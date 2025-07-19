#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
from typing import Any, Dict, List, Optional, Callable

import aiohttp
from loguru import logger

from .exceptions import (
    APIConnectionError,
    APIRateLimitError,
    AuthenticationError,
    WebSocketConnectionError
)
from .constants import (
    RETRYABLE_HTTP_CODES,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
    HTTP_FORBIDDEN,
    HTTP_TOO_MANY_REQUESTS,
    WS_HEARTBEAT_INTERVAL,
    WS_RECONNECT_DELAY,
    WS_MAX_RECONNECT_ATTEMPTS
)
from .utils import retry_async

class MisskeyAPI:
    def __init__(self, instance_url: str, access_token: str, max_retries: int = 3, timeout: int = 30, config=None):
        from .api_validation import validate_url_param, validate_token_param, log_validation_error
        try:
            self.instance_url = validate_url_param(instance_url, "实例 URL").rstrip("/")
            self.access_token = validate_token_param(access_token, "访问令牌")
        except ValueError as e:
            log_validation_error(e, "Misskey API 初始化")
            raise
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("最大重试次数必须是非负整数")
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("超时时间必须是正整数")
        self.config = config
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "MisskeyBot/1.0"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[aiohttp.ClientWebSocketResponse] = None
        self.ws_heartbeat_task: Optional[asyncio.Task] = None
        self.max_retries = max_retries
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    def _is_retryable_error(self, status_code: int) -> bool:
        return status_code in RETRYABLE_HTTP_CODES
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self) -> None:
        if self.ws_heartbeat_task is not None:
            self.ws_heartbeat_task.cancel()
            try:
                await self.ws_heartbeat_task
            except asyncio.CancelledError:
                pass
            self.ws_heartbeat_task = None
        if self.ws_connection is not None and not self.ws_connection.closed:
            await self.ws_connection.close()
            self.ws_connection = None
        if self.session is not None and not self.session.closed:
            connector = self.session.connector
            await self.session.close()
            if connector is not None and not connector.closed:
                await connector.close()
            await asyncio.sleep(0.1)
            self.session = None
        logger.debug("Misskey API 客户端连接已关闭")
    
    @retry_async(max_retries=3, retryable_exceptions=(aiohttp.ClientError, APIConnectionError))
    async def _make_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not endpoint or not isinstance(endpoint, str):
            raise ValueError("API 端点不能为空且必须是字符串")
        if data is not None and not isinstance(data, dict):
            raise ValueError("请求数据必须是字典格式")
        session = await self._ensure_session()
        url = f"{self.instance_url}/api/{endpoint}"
        request_data = {"i": self.access_token}
        if data:
            request_data.update(data)
        try:
            logger.debug(f"请求 Misskey API: {endpoint}")
            async with session.post(url, json=request_data, headers=self.headers) as response:
                if response.status == HTTP_OK:
                    try:
                        result = await response.json()
                        logger.debug(f"Misskey API 请求成功: {endpoint}")
                        return result
                    except json.JSONDecodeError as e:
                        raise APIConnectionError("Misskey", f"API 返回无效 JSON: {e}")
                
                elif response.status == HTTP_UNAUTHORIZED:
                    logger.error("API 认证失败")
                    raise AuthenticationError("Misskey API 认证失败，请检查访问令牌")
                elif response.status == HTTP_FORBIDDEN:
                    logger.error("API 权限不足")
                    raise AuthenticationError("Misskey API 权限不足，请求被拒绝")
                elif response.status == HTTP_TOO_MANY_REQUESTS:
                    raise APIRateLimitError("Misskey API 速率限制")
                elif self._is_retryable_error(response.status):
                    error_text = await response.text()
                    raise APIConnectionError("Misskey", f"HTTP {response.status}: {error_text}")
                else:
                    error_text = await response.text()
                    logger.error(f"API 请求失败: {response.status} - {error_text}")
                    raise APIConnectionError("Misskey", f"HTTP {response.status}: {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.warning(f"网络错误: {e}")
            raise APIConnectionError("Misskey", f"网络连接失败: {e}")
        except (AuthenticationError, ValueError):
            raise
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"网络连接错误: {e}")
            raise APIConnectionError("Misskey", f"网络连接错误: {e}")
        except (TypeError, KeyError) as e:
            logger.error(f"Misskey API 数据处理错误: {e}")
            raise ValueError(f"API 响应数据格式错误: {e}")
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise APIConnectionError("Misskey", f"未知错误: {e}")
    
    async def request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._make_request(endpoint, data)
    
    async def create_note(self, text: str, visibility: Optional[str] = None, reply_id: Optional[str] = None) -> Dict[str, Any]:
        if visibility is None:
            if self.config:
                visibility = self.config.get("bot.auto_post.visibility", "public")
            else:
                visibility = "public"
        data = {
            "text": text,
            "visibility": visibility,
        }
        if reply_id:
            data["replyId"] = reply_id
        result = await self._make_request("notes/create", data)
        logger.debug(f"Misskey 发帖成功，note_id: {result.get('createdNote', {}).get('id', 'unknown')}")
        return result
    
    async def get_mentions(self, limit: int = 10, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = {
            "limit": limit,
        }
        if since_id:
            data["sinceId"] = since_id
        return await self._make_request("notes/mentions", data)
    
    async def get_note(self, note_id: str) -> Dict[str, Any]:
        data = {
            "noteId": note_id,
        }
        return await self._make_request("notes/show", data)
    
    async def get_user(self, user_id: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
        if not (user_id or username):
            raise ValueError("必须提供 user_id 或 username")
        data = {}
        if user_id:
            data["userId"] = user_id
        elif username:
            data["username"] = username
        return await self._make_request("users/show", data)
    
    async def get_current_user(self) -> Dict[str, Any]:
        return await self._make_request("i", {})
    
    async def get_messages(self, user_id: str, limit: int = 10, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = {
            "userId": user_id,
            "limit": limit,
        }
        if since_id:
            data["sinceId"] = since_id
        return await self._make_request("chat/messages/user-timeline", data)
    
    async def send_message(self, user_id: str, text: str) -> Dict[str, Any]:
        data = {
            "toUserId": user_id,
            "text": text,
        }
        result = await self._make_request("chat/messages/create-to-user", data)
        logger.debug(f"Misskey 私信发送成功，message_id: {result.get('id', 'unknown')}")
        return result
    
    async def get_all_chat_messages(self, limit: int = 10, room: bool = False) -> List[Dict[str, Any]]:
        data = {
            "limit": limit,
            "room": room,
        }
        try:
            chat_messages = await self._make_request("chat/history", data)
            logger.debug(f"通过 chat/history API 获取到 {len(chat_messages)} 条聊天消息")
            return chat_messages
        except Exception as e:
            logger.debug(f"获取聊天消息失败: {e}")
            return []
    
    async def _ws_heartbeat(self) -> None:
        while True:
            try:
                if self.ws_connection and not self.ws_connection.closed:
                    await self.ws_connection.ping()
                    logger.debug("已发送 WebSocket 心跳")
                await asyncio.sleep(WS_HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                logger.debug("WebSocket 心跳任务已取消")
                break
            except (ConnectionError, OSError, TimeoutError) as e:
                logger.warning(f"WebSocket 心跳网络错误: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket 心跳未知错误: {e}")
                await asyncio.sleep(5)
    
    async def connect_websocket(self, callback: Callable[[Dict[str, Any]], Any], 
                                max_reconnect_attempts: int = WS_MAX_RECONNECT_ATTEMPTS) -> None:
        reconnect_attempts = 0
        reconnect_delay = WS_RECONNECT_DELAY
        
        while reconnect_attempts < max_reconnect_attempts:
            try:
                ws_url = f"{self.instance_url.replace('http', 'ws')}/streaming"
                
                session = await self._ensure_session()
                self.ws_connection = await session.ws_connect(ws_url)
                
                if self.ws_heartbeat_task is None or self.ws_heartbeat_task.done():
                    self.ws_heartbeat_task = asyncio.create_task(self._ws_heartbeat())
                
                connect_data = {
                    "type": "connect",
                    "body": {
                        "channel": "main",
                        "id": "main",
                    }
                }
                await self.ws_connection.send_str(json.dumps(connect_data))
                
                if self.access_token:
                    user_connect_data = {
                        "type": "connect",
                        "body": {
                            "channel": "user",
                            "id": "user",
                            "params": {
                                "i": self.access_token
                            }
                        }
                    }
                    await self.ws_connection.send_str(json.dumps(user_connect_data))
                
                logger.info("WebSocket 连接已建立")
                reconnect_attempts = 0
                reconnect_delay = 1.0
                
                async for msg in self.ws_connection:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            await callback(data)
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析 WebSocket 消息: {msg.data}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.warning(f"WebSocket 连接错误: {self.ws_connection.exception()}")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logger.warning("WebSocket 连接已关闭")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSING:
                        logger.warning("WebSocket 连接正在关闭...")
                        break
                
                logger.warning("WebSocket 连接已断开，准备重连")
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"WebSocket 连接失败: {e}")
                if reconnect_attempts >= max_reconnect_attempts - 1:
                    logger.error(f"WebSocket 连接失败，已达到最大重试次数: {e}")
                    raise WebSocketConnectionError(f"WebSocket 连接失败，已达到最大重试次数: {e}")
            
            reconnect_attempts += 1
            if reconnect_attempts < max_reconnect_attempts:
                logger.info(f"WebSocket 将在 {reconnect_delay} 秒后尝试重连 ({reconnect_attempts}/{max_reconnect_attempts})")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, WS_HEARTBEAT_INTERVAL * 2)
            else:
                break