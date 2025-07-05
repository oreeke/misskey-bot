#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import random
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta

import aiohttp
from loguru import logger

from .exceptions import (
    APIConnectionError,
    APIRateLimitError,
    AuthenticationError,
    WebSocketConnectionError
)
from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_VISIBILITY,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
    HTTP_FORBIDDEN,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIMEOUT
)


class MisskeyAPI:
    
    def __init__(self, instance_url: str, access_token: str, max_retries: int = DEFAULT_MAX_RETRIES, config=None):

        if not instance_url or not isinstance(instance_url, str):
            raise ValueError("实例URL不能为空且必须是字符串")
        
        if not instance_url.strip().startswith(('http://', 'https://')):
            raise ValueError("实例URL必须以http://或https://开头")
        
        if not access_token or not isinstance(access_token, str):
            raise ValueError("访问令牌不能为空且必须是字符串")
        
        if len(access_token.strip()) < 10:
            raise ValueError("访问令牌长度过短，请检查令牌是否正确")
        
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("最大重试次数必须是非负整数")
        
        self.instance_url = instance_url.rstrip("/")
        self.access_token = access_token.strip()
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[aiohttp.ClientWebSocketResponse] = None
        self.ws_heartbeat_task: Optional[asyncio.Task] = None
        self.max_retries = max_retries
        self.base_retry_delay = DEFAULT_RETRY_DELAY
        self.max_retry_delay = 60.0
        self.backoff_factor = 2.0
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        delay = self.base_retry_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_retry_delay)
        
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return max(0.1, delay + jitter)
    
    def _is_retryable_error(self, status_code: int) -> bool:
        retryable_codes = {
            HTTP_TOO_MANY_REQUESTS,
            HTTP_INTERNAL_SERVER_ERROR,
            HTTP_BAD_GATEWAY,
            HTTP_SERVICE_UNAVAILABLE,
            HTTP_GATEWAY_TIMEOUT
        }
        return status_code in retryable_codes
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
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
    
    async def _make_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

        if not endpoint or not isinstance(endpoint, str):
            raise ValueError("API端点不能为空且必须是字符串")
        
        if data is not None and not isinstance(data, dict):
            raise ValueError("请求数据必须是字典格式")
        
        session = await self._ensure_session()
        url = f"{self.instance_url}/api/{endpoint}"
        

        request_data = {"i": self.access_token}
        if data:
            request_data.update(data)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"正在请求Misskey API: {endpoint} (尝试 {attempt + 1}/{self.max_retries})")
                
                async with session.post(url, json=request_data, headers=self.headers) as response:
                    if response.status == HTTP_OK:
                        try:
                            result = await response.json()
                            logger.debug(f"Misskey API请求成功: {endpoint}")
                            return result
                        except json.JSONDecodeError as e:
                            raise APIConnectionError("Misskey", f"API返回无效JSON: {e}")
                    
                    elif response.status == HTTP_UNAUTHORIZED:
                        logger.error("API认证失败")
                        raise AuthenticationError("Misskey API认证失败，请检查访问令牌")
                    
                    elif response.status == HTTP_TOO_MANY_REQUESTS:
                        last_error = APIRateLimitError("Misskey API速率限制")
                        logger.warning(f"API速率限制 (尝试 {attempt + 1}/{self.max_retries})")
                        if attempt < self.max_retries - 1:
                            delay = self._calculate_retry_delay(attempt)
                            logger.info(f"等待 {delay:.2f} 秒后重试")
                            await asyncio.sleep(delay)
                    
                    elif self._is_retryable_error(response.status):
                        error_text = await response.text()
                        last_error = APIConnectionError("Misskey", f"HTTP {response.status}: {error_text}")
                        logger.warning(f"API临时错误 (尝试 {attempt + 1}/{self.max_retries}): {response.status}")
                        if attempt < self.max_retries - 1:
                            delay = self._calculate_retry_delay(attempt)
                            logger.info(f"等待 {delay:.2f} 秒后重试")
                            await asyncio.sleep(delay)
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"API请求失败: {response.status} - {error_text}")
                        raise APIConnectionError("Misskey", f"HTTP {response.status}: {error_text}")
                            
            except aiohttp.ClientError as e:
                last_error = APIConnectionError("Misskey", f"网络连接失败: {e}")
                logger.warning(f"网络错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
            
            except (AuthenticationError, ValueError):

                raise
            
            except (ConnectionError, OSError, TimeoutError) as e:
                last_error = APIConnectionError("Misskey", f"网络连接错误: {e}")
                logger.error(f"网络连接错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
            except (TypeError, KeyError) as e:
                logger.error(f"Misskey API数据处理错误: {e}")
                raise ValueError(f"API响应数据格式错误: {e}")
            except Exception as e:
                last_error = APIConnectionError("Misskey", f"未知错误: {e}")
                logger.error(f"未知错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
        

        if last_error:
            raise last_error
        else:
            raise APIConnectionError("Misskey", "API请求失败，已达到最大重试次数")
    
    async def request(self, endpoint: str, data: Optional[Dict[str, Any]] = None, method: str = "POST", 
                     retry_count: int = 0) -> Dict[str, Any]:
        """发送请求到Misskey API（保持向后兼容）
        
        Args:
            endpoint: API端点
            data: 请求数据
            method: 请求方法（暂时忽略，始终使用POST）
            retry_count: 当前重试次数（已弃用）
            
        Returns:
            API响应
        """
        return await self._make_request(endpoint, data)
    
    async def create_note(self, text: str, visibility: Optional[str] = None, reply_id: Optional[str] = None) -> Dict[str, Any]:
        """创建帖子（发帖）"""

        if visibility is None:
            if self.config:
                visibility = self.config.get("bot.visibility.default", DEFAULT_VISIBILITY)
            else:
                visibility = DEFAULT_VISIBILITY
        data = {
            "text": text,
            "visibility": visibility,
        }
        
        if reply_id:
            data["replyId"] = reply_id
        
        return await self._make_request("notes/create", data)
    
    async def get_mentions(self, limit: int = 10, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取提及（@）"""
        data = {
            "limit": limit,
        }
        
        if since_id:
            data["sinceId"] = since_id
        
        return await self._make_request("notes/mentions", data)
    
    async def get_note(self, note_id: str) -> Dict[str, Any]:
        """获取帖子信息"""
        data = {
            "noteId": note_id,
        }
        
        return await self._make_request("notes/show", data)
    
    async def get_user(self, user_id: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
        """获取用户信息"""
        if not user_id and not username:
            raise ValueError("必须提供user_id或username")
        
        data = {}
        if user_id:
            data["userId"] = user_id
        elif username:
            data["username"] = username
        
        return await self._make_request("users/show", data)
    
    async def get_current_user(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        return await self._make_request("i", {})
    
    async def get_messages(self, user_id: str, limit: int = 10, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取与指定用户的聊天消息"""
        data = {
            "userId": user_id,
            "limit": limit,
        }
        
        if since_id:
            data["sinceId"] = since_id
        
        return await self._make_request("chat/messages/user-timeline", data)
    
    async def send_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """发送聊天消息"""
        data = {
            "toUserId": user_id,
            "text": text,
        }
        
        return await self._make_request("chat/messages/create-to-user", data)
    
    async def get_all_chat_messages(self, limit: int = 20, room: bool = False) -> List[Dict[str, Any]]:
        """获取聊天历史记录"""
        data = {
            "limit": min(max(limit, 1), 100),
            "room": room,
        }
        
        try:
    
            chat_messages = await self._make_request("chat/history", data)
            logger.debug(f"通过chat/history API获取到 {len(chat_messages)} 条聊天消息")
            return chat_messages
            
        except Exception as e:
            logger.debug(f"获取聊天消息失败: {e}")
            return []
    
    async def _ws_heartbeat(self) -> None:
        """WebSocket心跳，保持连接活跃"""
        while True:
            try:
                if self.ws_connection and not self.ws_connection.closed:
                    await self.ws_connection.ping()
                    logger.debug("已发送WebSocket心跳")
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.debug("WebSocket心跳任务已取消")
                break
            except (ConnectionError, OSError, TimeoutError) as e:
                logger.error(f"WebSocket心跳网络错误: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket心跳未知错误: {e}")
                await asyncio.sleep(5)
    
    async def connect_websocket(self, callback: Callable[[Dict[str, Any]], Any], 
                               max_reconnect_attempts: int = 10) -> None:
        """连接到Misskey WebSocket API"""
        reconnect_attempts = 0
        reconnect_delay = 1.0
        
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
                
                logger.info("已连接到Misskey WebSocket API")
                reconnect_attempts = 0
                reconnect_delay = 1.0
                

                async for msg in self.ws_connection:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            await callback(data)
                        except json.JSONDecodeError:
                            logger.error(f"无法解析WebSocket消息: {msg.data}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket连接错误: {self.ws_connection.exception()}")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logger.warning("WebSocket连接已关闭")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSING:
                        logger.warning("WebSocket连接正在关闭")
                        break
                
                logger.warning("WebSocket连接已断开，准备重连")
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"WebSocket连接失败: {e}")
            
            
            reconnect_attempts += 1
            if reconnect_attempts < max_reconnect_attempts:
                logger.info(f"将在{reconnect_delay}秒后尝试重连 ({reconnect_attempts}/{max_reconnect_attempts})")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)
            else:
                logger.error(f"已达到最大重连尝试次数({max_reconnect_attempts})，停止重连")
                break