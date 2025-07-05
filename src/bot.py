#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config
from .misskey_api import MisskeyAPI
from .deepseek_api import DeepSeekAPI
from .persistence import PersistenceManager
from .exceptions import (
    MisskeyBotError,
    ConfigurationError,
    APIConnectionError,
    APIRateLimitError,
    AuthenticationError
)
from .constants import (
    DEFAULT_MAX_RETRIES,
    MAX_PROCESSED_ITEMS_CACHE,
    DEFAULT_POLLING_INTERVAL
)


DEFAULT_ERROR_REPLY_MAX_LENGTH = 500
ERROR_MSG_RATE_LIMIT = "抱歉，请求过于频繁，请稍后再试。"
ERROR_MSG_AUTH_FAILED = "抱歉，服务配置有误，请联系管理员。"
ERROR_MSG_CONNECTION_FAILED = "抱歉，AI服务暂时不可用，请稍后再试。"
ERROR_MSG_VALIDATION_FAILED = "抱歉，请求参数无效，请检查输入。"
ERROR_MSG_RESOURCE_EXHAUSTED = "抱歉，系统资源不足，请稍后再试。"
ERROR_MSG_UNKNOWN_ERROR = "抱歉，处理您的消息时出现了错误。"


class MisskeyBot:
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_cleanup_needed') and self._cleanup_needed:
            await self.stop()
        return False
    
    def __init__(self, config: Config):
        if not isinstance(config, Config):
            raise ValueError("配置参数必须是Config类型")
        
        self.config = config
        

        try:
            self.misskey = MisskeyAPI(
                instance_url=config.get("misskey.instance_url"),
                access_token=config.get("misskey.access_token"),
                config=config,
            )
            
            self.deepseek = DeepSeekAPI(
                api_key=config.get("deepseek.api_key"),
                model=config.get("deepseek.model"),
            )
            
    
            self._cleanup_needed = True
            
            logger.info("API客户端初始化成功")
            
        except (ValueError, AuthenticationError) as e:
            logger.error(f"API客户端配置错误: {e}")
            raise ConfigurationError(f"API客户端配置错误: {e}")
        except (ImportError, AttributeError) as e:
            logger.error(f"API客户端依赖错误: {e}")
            raise ConfigurationError(f"API客户端依赖错误: {e}")
        except Exception as e:
            logger.error(f"API客户端初始化未知错误: {e}")
            raise ConfigurationError(f"API客户端初始化未知错误: {e}")
        

        try:
            self.scheduler = AsyncIOScheduler()
            logger.info("调度器初始化成功")
        except ImportError as e:
            logger.error(f"调度器依赖缺失: {e}")
            raise ConfigurationError(f"调度器依赖缺失: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"调度器配置错误: {e}")
            raise ConfigurationError(f"调度器配置错误: {e}")
        except Exception as e:
            logger.error(f"调度器初始化未知错误: {e}")
            raise ConfigurationError(f"调度器初始化未知错误: {e}")
        

        db_path = config.get("persistence.db_path", "data/bot_persistence.db")
        self.persistence = PersistenceManager(db_path)
        

        self.processed_mentions: deque = deque(maxlen=MAX_PROCESSED_ITEMS_CACHE)
        self.processed_messages: deque = deque(maxlen=MAX_PROCESSED_ITEMS_CACHE)
        

        self.last_auto_post_time = datetime.now() - timedelta(hours=24)
        

        self.posts_today = 0
        self.today = datetime.now().date()
        

        self.system_prompt = config.get("system_prompt", "")
        

        self.running = False
        

        self.tasks = []
        

        self.error_counts = {
            'api_errors': 0,
            'rate_limit_errors': 0,
            'auth_errors': 0,
            'connection_errors': 0
        }
        
        logger.info("Misskey机器人初始化完成")
    
    async def _load_recent_processed_items(self) -> None:
        """加载最近的已处理消息ID到内存缓存"""
        try:
    
            recent_mentions = await self.persistence.get_recent_mentions(MAX_PROCESSED_ITEMS_CACHE)
            for mention in recent_mentions:
                self.processed_mentions.append(mention['note_id'])
            
    
            recent_messages = await self.persistence.get_recent_messages(MAX_PROCESSED_ITEMS_CACHE)
            for message in recent_messages:
                self.processed_messages.append(message['message_id'])
                
            logger.info(f"已加载 {len(recent_mentions)} 个提及和 {len(recent_messages)} 个消息到内存缓存")
            
        except Exception as e:
            logger.warning(f"加载已处理消息ID到缓存时出错: {e}，将从空状态开始")
    
    async def _cleanup_old_processed_items(self) -> None:
        try:
            cleanup_days = self.config.get("persistence.cleanup_days", 7)
            deleted_count = await self.persistence.cleanup_old_records(cleanup_days)
            
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 条过期记录")
                
        except Exception as e:
            logger.error(f"清理旧记录时出错: {e}")
     
    def _handle_error(self, error: Exception, context: str = "") -> str:
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        
        logger.error(f"错误类型: {error_type}, 上下文: {context}, 详情: {str(error)}")
        
        
        if isinstance(error, APIRateLimitError):
            return ERROR_MSG_RATE_LIMIT
        elif isinstance(error, AuthenticationError):
            return ERROR_MSG_AUTH_FAILED
        elif isinstance(error, APIConnectionError):
            return ERROR_MSG_CONNECTION_FAILED
        elif isinstance(error, ValueError):
            return ERROR_MSG_VALIDATION_FAILED
        elif isinstance(error, RuntimeError):
            return ERROR_MSG_RESOURCE_EXHAUSTED
        else:
            return ERROR_MSG_UNKNOWN_ERROR
    
    def get_error_stats(self) -> Dict[str, int]:
        return self.error_counts.copy()
     
    async def start(self) -> None:
        if self.running:
            logger.warning("机器人已经在运行中")
            return
            
        logger.info("正在启动机器人...")
        self.running = True
        

        try:
            current_user = await self.misskey.get_current_user()
            self.bot_user_id = current_user.get("id")
            logger.info(f"机器人用户ID: {self.bot_user_id}")
        except Exception as e:
            logger.error(f"获取当前用户信息失败: {e}")
            self.bot_user_id = None
        

        await self._load_recent_processed_items()
        

        self.scheduler.add_job(
            self._reset_daily_post_count,
            "cron",
            hour=0,
            minute=0,
            second=0,
        )
        

        self.scheduler.add_job(
            lambda: asyncio.create_task(self._cleanup_old_processed_items()),
            "cron",
            hour=1,
            minute=0,
            second=0,
        )
        

        self.scheduler.add_job(
            lambda: asyncio.create_task(self.persistence.vacuum()),
            "cron",
            hour=2,
            minute=0,
            second=0,
        )
        

        if self.config.get("bot.auto_post.enabled", False):
            interval_minutes = self.config.get("bot.auto_post.interval_minutes", 60)
            logger.info(f"已启用自动发帖，间隔: {interval_minutes}分钟")
            
            self.scheduler.add_job(
                self._auto_post,
                "interval",
                minutes=interval_minutes,
                next_run_time=datetime.now() + timedelta(minutes=1),
            )
        

        self.scheduler.start()
        

        websocket_task = asyncio.create_task(self._start_websocket())
        self.tasks.append(websocket_task)
        

        polling_task = asyncio.create_task(self._poll_mentions())
        self.tasks.append(polling_task)
        
        logger.info("机器人已启动")
    
    async def stop(self) -> None:
        if not self.running:
            logger.warning("机器人已经停止")
            return
            
        logger.info("正在停止机器人...")
        self.running = False
        
        try:
    
            self.scheduler.shutdown()
            
    
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
    
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks = []
            
    
            await self.misskey.close()
            
    
            await self.persistence.close()
            
        except Exception as e:
            logger.error(f"停止机器人时出错: {e}")
        finally:
    
            self._cleanup_needed = False
            logger.info("机器人已停止")
    
    async def _start_websocket(self) -> None:
        retry_count = 0
        max_retries = 10
        base_delay = 5
        
        while self.running:
            try:
                await self.misskey.connect_websocket(self._handle_websocket_message)
    
                retry_count = 0
            except asyncio.CancelledError:
    
                break
            except (ConnectionError, OSError, TimeoutError) as e:
                if not self.running:
                    break
                    
                retry_count += 1
    
                delay = min(base_delay * (2 ** (retry_count - 1)), 300)
                
                logger.error(f"WebSocket网络连接错误: {e}")
                logger.info(f"将在{delay}秒后重新连接WebSocket... (尝试 {retry_count}/{max_retries})")
                
    
                if retry_count >= max_retries:
                    logger.error(f"WebSocket连接失败次数过多，将重置重试计数")
                    retry_count = 0
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"WebSocket数据格式错误: {e}")
    
                continue
            except Exception as e:
                if not self.running:
                    break
                    
                retry_count += 1
                delay = min(base_delay * (2 ** (retry_count - 1)), 300)
                
                logger.error(f"WebSocket未知错误: {e}")
                logger.info(f"将在{delay}秒后重新连接WebSocket... (尝试 {retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    logger.error(f"WebSocket连接失败次数过多，将重置重试计数")
                    retry_count = 0
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
    
    async def _handle_websocket_message(self, data: Dict[str, Any]) -> None:

        try:
            logger.debug(f"收到WebSocket消息: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("type") != "channel":
                logger.debug(f"忽略非频道消息，类型: {data.get('type')}")
                return
            
            body = data.get("body", {})
            if not body:
                logger.debug("消息体为空，忽略")
                return
            
            message_type = body.get("type")
            logger.debug(f"消息类型: {message_type}")
            

            if message_type == "mention" and self.config.get("bot.response.mention_enabled", True):
                note = body.get("body", {})
                if note and note.get("id") not in self.processed_mentions:
                    logger.info(f"处理提及消息: {note.get('id')}")
                    await self._handle_mention(note)
                else:
                    logger.debug(f"提及消息已处理或无效: {note.get('id') if note else 'None'}")
            

            elif message_type in ["messaging_message", "messagingMessage", "message", "chat"] and self.config.get("bot.response.chat_enabled", True):
                message = body.get("body", {})
                if message and message.get("id") not in self.processed_messages:
                    logger.info(f"处理聊天消息: {message.get('id')}")
                    await self._handle_message(message)
                else:
                    logger.debug(f"聊天消息已处理或无效: {message.get('id') if message else 'None'}")
            
            else:
                logger.debug(f"未处理的消息类型: {message_type}")
                    
        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {e}")
    
    async def _poll_mentions(self) -> None:
        retry_count = 0
        max_retries = 5
        base_delay = DEFAULT_POLLING_INTERVAL
        
        while self.running:
            try:
    
                if self.config.get("bot.response.mention_enabled", True):
                    mentions = await self.misskey.get_mentions(limit=10)
                    for mention in mentions:
                        if mention["id"] not in self.processed_mentions:
                            await self._handle_mention(mention)
                
    
                if self.config.get("bot.response.chat_enabled", True):
                    await self._poll_chat_messages()
                
    
                retry_count = 0
                
    
                try:
                    await asyncio.sleep(base_delay)
                except asyncio.CancelledError:
                    break
                    
            except asyncio.CancelledError:
                break
            except (APIRateLimitError, APIConnectionError) as e:
                if not self.running:
                    break
                    
                retry_count += 1

                delay = min(base_delay * (3 ** (retry_count - 1)), 1800)
                
                logger.error(f"轮询API错误: {e}")
                logger.info(f"将在{delay}秒后重试... (尝试 {retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    logger.error(f"轮询API失败次数过多，将重置重试计数")
                    retry_count = 0
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
            except (ConnectionError, TimeoutError) as e:
                if not self.running:
                    break
                    
                retry_count += 1
                delay = min(base_delay * (2 ** (retry_count - 1)), 900)
                
                logger.error(f"轮询网络错误: {e}")
                logger.info(f"将在{delay}秒后重试... (尝试 {retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    logger.error(f"轮询网络失败次数过多，将重置重试计数")
                    retry_count = 0
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
            except Exception as e:
                if not self.running:
                    break
                    
                retry_count += 1
                delay = min(base_delay * (2 ** (retry_count - 1)), 900)
                
                logger.error(f"轮询未知错误: {e}")
                logger.info(f"将在{delay}秒后重试... (尝试 {retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    logger.error(f"轮询失败次数过多，将重置重试计数")
                    retry_count = 0
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
    
    async def _poll_chat_messages(self) -> None:
        try:
            logger.debug("开始轮询聊天消息")
            
    
            messages = await self.misskey.get_all_chat_messages(limit=20)
            
            logger.debug(f"获取到 {len(messages)} 条聊天消息")
            
            for message in messages:
                message_id = message.get("id")
                if message_id and message_id not in self.processed_messages:
            
                    if not await self.persistence.is_message_processed(message_id):
                        logger.info(f"通过轮询发现新聊天消息: {message_id}")
                        await self._handle_message(message)
                    else:
                        logger.debug(f"聊天消息已在数据库中标记为已处理: {message_id}")
                else:
                    logger.debug(f"聊天消息已在内存缓存中: {message_id}")
                        
        except Exception as e:
            logger.error(f"轮询聊天消息时出错: {e}")
            logger.debug(f"轮询聊天消息详细错误: {e}", exc_info=True)
    
    async def _get_chat_notifications(self) -> List[Dict[str, Any]]:
        logger.warning("_get_chat_notifications方法已弃用，请使用get_all_chat_messages方法")
        try:
    
            return await self.misskey.get_all_chat_messages(limit=20)
            
        except Exception as e:
            logger.debug(f"获取聊天消息失败: {e}")
            return []
    
    async def _handle_mention(self, note: Dict[str, Any]) -> None:
        note_id = note.get("id")
        if not note_id:
            return
            

        if note_id in self.processed_mentions or await self.persistence.is_mention_processed(note_id):
            return
        
        try:
    
            if not isinstance(note, dict):
                raise ValueError("提及数据必须是字典格式")
            
            required_fields = ["user", "id", "text"]
            for field in required_fields:
                if field not in note:
                    raise ValueError(f"提及数据缺少必要字段: {field}")
            
    
            text = note.get("text", "")
            user = note.get("user", {})
            username = user.get("username", "用户")
            user_id = user.get("id")
            
    
            await self.persistence.mark_mention_processed(note_id, user_id, username)
            self.processed_mentions.append(note_id)
            
            logger.info(f"收到来自 {username} 的提及: {text}")
            
            try:
    
                reply = await self.deepseek.generate_reply(text, self.system_prompt, username)
            except (APIRateLimitError, APIConnectionError, AuthenticationError) as e:
                self._handle_error(e, "生成回复时")
    
                error_message = "抱歉，AI服务暂时不可用，请稍后再试。"
                if isinstance(e, APIRateLimitError):
                    error_message = "抱歉，请求过于频繁，请稍后再试。"
                elif isinstance(e, AuthenticationError):
                    error_message = "抱歉，服务配置有误，请联系管理员。"
                
                await self._send_error_reply(username, note_id, error_message)
                return
            

            max_length = self.config.get("bot.response.max_response_length", 500)
            if len(reply) > max_length:
                reply = reply[:max_length-3] + "..."
            
            try:
    
                await self.misskey.create_note(reply, reply_id=note_id)
                logger.info(f"已回复提及: {reply[:50]}...")
            except (APIRateLimitError, APIConnectionError, AuthenticationError) as e:
                self._handle_error(e, "发送回复时")
                await self._send_error_reply(username, note_id, "抱歉，回复发送失败，请稍后再试。")
            
        except ValueError as e:
            logger.error(f"输入验证错误: {e}")
            self._handle_error(e, "处理提及时")
        except Exception as e:
            logger.error(f"处理提及时出错: {e}")
            self._handle_error(e, "处理提及时")

            try:
                username = note.get("user", {}).get("username", "用户")
                if username and note_id:
                    await self._send_error_reply(username, note_id, "抱歉，处理您的消息时出现了错误。")
            except Exception as reply_error:
                logger.error(f"发送错误回复失败: {reply_error}")
    
    async def _send_error_reply(self, username: str, note_id: str, message: str) -> None:
        try:

            if len(message) > DEFAULT_ERROR_REPLY_MAX_LENGTH:
                message = message[:DEFAULT_ERROR_REPLY_MAX_LENGTH-3] + "..."
            
            await self.misskey.create_note(
                text=f"@{username} {message}",
                reply_id=note_id
            )
        except Exception as e:
            logger.error(f"发送错误回复失败: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        logger.debug(f"处理聊天消息: {json.dumps(message, ensure_ascii=False, indent=2)}")
        
        message_id = message.get("id")
        if not message_id:
            logger.debug("消息缺少ID，跳过处理")
            return
            

        if message_id in self.processed_messages or await self.persistence.is_message_processed(message_id):
            logger.debug(f"消息已处理: {message_id}")
            return
        
        try:
    
            text = message.get("text") or message.get("content") or message.get("body", "")
            user_id = message.get("userId") or message.get("user_id") or message.get("fromUserId") or message.get("from_user_id")
            
    
            if not user_id and "user" in message:
                user_obj = message.get("user", {})
                user_id = user_obj.get("id") if isinstance(user_obj, dict) else None
            
    
            if not user_id and "sender" in message:
                sender_obj = message.get("sender", {})
                user_id = sender_obj.get("id") if isinstance(sender_obj, dict) else None
            
            logger.debug(f"解析消息 - ID: {message_id}, 用户ID: {user_id}, 文本: {text[:50] if text else 'None'}...")
            
    
            if self.bot_user_id and user_id == self.bot_user_id:
                logger.debug(f"跳过自己发送的消息: {message_id}")
        
                await self.persistence.mark_message_processed(message_id, user_id, "private")
                self.processed_messages.append(message_id)
                return
            
    
            await self.persistence.mark_message_processed(message_id, user_id, "private")
            self.processed_messages.append(message_id)
            
            if not user_id or not text:
                logger.debug(f"消息缺少必要信息 - 用户ID: {user_id}, 文本: {bool(text)}")
                return
            
            logger.info(f"收到来自用户 {user_id} 的消息: {text}")
            
    
            chat_history = await self._get_chat_history(user_id)
            
    
            chat_history.append({"role": "user", "content": text})
            
    
            if not chat_history or chat_history[0].get("role") != "system":
                chat_history.insert(0, {"role": "system", "content": self.system_prompt})
            
    
            max_tokens = self.config.get("deepseek.max_tokens", 1000)
            temperature = self.config.get("deepseek.temperature", 0.8)
            reply = await self.deepseek.generate_chat_response(chat_history, max_tokens=max_tokens, temperature=temperature)
            
    
            max_length = self.config.get("bot.response.max_response_length", 500)
            if len(reply) > max_length:
                reply = reply[:max_length-3] + "..."
            
    
            await self.misskey.send_message(user_id, reply)
            logger.info(f"已回复消息: {reply[:50]}...")
            
    
            chat_history.append({"role": "assistant", "content": reply})
            
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            logger.debug(f"处理消息详细错误: {e}", exc_info=True)
    
    async def _get_chat_history(self, user_id: str, limit: int = 5) -> List[Dict[str, str]]:
        try:
    
            messages = await self.misskey.get_messages(user_id, limit=limit)
            
    
            chat_history = []
            for msg in reversed(messages):
                if msg.get("userId") == user_id:
                    chat_history.append({"role": "user", "content": msg.get("text", "")})
                else:
                    chat_history.append({"role": "assistant", "content": msg.get("text", "")})
            
            return chat_history
            
        except Exception as e:
            logger.error(f"获取聊天历史时出错: {e}")
            return []
    
    async def _auto_post(self) -> None:
        if not self.running:
            return
            
        try:
    
            current_date = datetime.now().date()
            if current_date != self.today:
                self._reset_daily_post_count()
            
            max_posts = self.config.get("bot.auto_post.max_posts_per_day", 10)
            if self.posts_today >= max_posts:
                logger.info(f"今日发帖数量已达上限 ({max_posts})，跳过自动发帖")
                return
            
    
            post_prompt = self.config.get("bot.auto_post.prompt", "请生成一篇有趣、有见解的社交媒体帖子。")
            
    
            post_content = await self.deepseek.generate_post(self.system_prompt, prompt=post_prompt)
            
    
            max_length = self.config.get("bot.auto_post.max_post_length", 500)
            if len(post_content) > max_length:
                post_content = post_content[:max_length-3] + "..."
                logger.info(f"帖子内容已截断至{max_length}字符")
            
    
            await self.misskey.create_note(post_content)
            
    
            self.posts_today += 1
            self.last_auto_post_time = datetime.now()
            
            logger.info(f"已自动发帖: {post_content[:50]}...")
            
        except Exception as e:
            logger.error(f"自动发帖时出错: {e}")
    
    def _reset_daily_post_count(self) -> None:
        self.posts_today = 0
        self.today = datetime.now().date()
        logger.info("已重置每日发帖计数")