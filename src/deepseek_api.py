#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepSeek API 客户端

这个模块提供了与DeepSeek API交互的功能，用于生成文本内容。
"""

import asyncio
import json
import random
from typing import Any, Dict, List, Optional, Union

from loguru import logger

import openai  # 使用OpenAI客户端，因为DeepSeek API兼容OpenAI API格式

from .exceptions import (
    APIConnectionError,
    APIRateLimitError,
    AuthenticationError as CustomAuthError
)
from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_API_TIMEOUT,
    DEEPSEEK_API_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE
)

# 导入OpenAI异常类（新版本库 v1.0.0+）
try:
    from openai import (
        RateLimitError,
        APIError,
        AuthenticationError,
        BadRequestError,
        APITimeoutError,
        NotFoundError,
        Timeout
    )
except ImportError as e:
    logger.error(f"无法导入OpenAI异常类: {e}")
    # 使用BaseException子类作为备用
    class RateLimitError(Exception):
        pass
    class APIError(Exception):
        pass
    class AuthenticationError(Exception):
        pass
    class BadRequestError(Exception):
        pass
    class APITimeoutError(Exception):
        pass
    class NotFoundError(Exception):
        pass
    class Timeout(Exception):
        pass


class DeepSeekAPI:
    """DeepSeek API 客户端类"""
    
    def __init__(self, api_key: str, model: str = DEFAULT_DEEPSEEK_MODEL, api_base: Optional[str] = None, max_retries: int = DEFAULT_MAX_RETRIES):
        """初始化DeepSeek API客户端
        
        Args:
            api_key: DeepSeek API密钥
            model: 使用的模型名称
            api_base: API基础URL，默认使用DeepSeek的官方API
            max_retries: 最大重试次数
            
        Raises:
            ValueError: 当输入参数无效时
            CustomAuthError: 当API密钥无效时
        """
        # 输入验证
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API密钥不能为空且必须是字符串")
        
        if len(api_key.strip()) < 10:
            raise ValueError("API密钥长度过短，请检查密钥是否正确")
        
        if not model or not isinstance(model, str):
            raise ValueError("模型名称不能为空且必须是字符串")
        
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("最大重试次数必须是非负整数")
        
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.max_retries = max_retries
        self.base_retry_delay = DEFAULT_RETRY_DELAY
        self.max_retry_delay = 60.0
        self.backoff_factor = 2.0
        
        # 设置API基础URL
        self.api_base = api_base if api_base else DEEPSEEK_API_BASE_URL
        
        # 创建OpenAI客户端（新版本库 v1.0.0+）
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=DEFAULT_API_TIMEOUT  # 添加超时配置
            )
            logger.info(f"成功创建OpenAI客户端，base_url={self.api_base}，超时时间={DEFAULT_API_TIMEOUT}秒")
        except Exception as e:
            logger.error(f"创建OpenAI客户端失败: {e}")
            raise APIConnectionError("DeepSeek", f"客户端初始化失败: {e}")
     
    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟时间（指数退避 + 随机抖动）"""
        delay = self.base_retry_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_retry_delay)
        # 添加随机抖动
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return max(0.1, delay + jitter)
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        retryable_errors = (
            RateLimitError,
            APITimeoutError,
            Timeout,
            APIError
        )
        return isinstance(error, retryable_errors)
     
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, 
                            max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE) -> str:
        """生成文本
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            max_tokens: 最大生成token数
            temperature: 生成温度
            
        Returns:
            生成的文本内容
            
        Raises:
            ValueError: 当输入参数无效时
            APIConnectionError: 当API连接失败时
            APIRateLimitError: 当API速率限制时
            CustomAuthError: 当API认证失败时
        """
        # 输入验证
        if not prompt or not isinstance(prompt, str):
            raise ValueError("提示内容不能为空且必须是字符串")
        
        if len(prompt.strip()) == 0:
            raise ValueError("提示内容不能为空白字符")
        
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ValueError("最大token数必须是正整数")
        
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("温度值必须在0到2之间")
        
        messages = []
        
        # 添加系统提示（如果提供）
        if system_prompt:
            if not isinstance(system_prompt, str):
                raise ValueError("系统提示必须是字符串")
            messages.append({"role": "system", "content": system_prompt.strip()})
        
        # 添加用户提示
        messages.append({"role": "user", "content": prompt.strip()})
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"正在调用DeepSeek API生成文本，尝试次数: {attempt + 1}/{self.max_retries}")
                
                # 使用新版本OpenAI库的API调用方式，添加asyncio超时保护
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    ),
                    timeout=DEFAULT_API_TIMEOUT
                )
                
                # 提取生成的文本
                generated_text = response.choices[0].message.content
                if not generated_text:
                    raise APIConnectionError("DeepSeek", "API返回空内容")
                
                logger.info(f"成功生成文本，长度: {len(generated_text)}")
                return generated_text
                
            except RateLimitError as e:
                last_error = e
                logger.warning(f"API速率限制，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
                    
            except BadRequestError as e:
                logger.error(f"API请求错误: {e}")
                raise ValueError(f"API请求参数错误: {e}")
                
            except AuthenticationError as e:
                logger.error(f"API认证错误: {e}")
                raise CustomAuthError(f"DeepSeek API认证失败: {e}")
                
            except (APITimeoutError, Timeout, asyncio.TimeoutError, APIError) as e:
                last_error = e
                logger.warning(f"API超时或临时错误，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1 and self._is_retryable_error(e):
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
                    
            except (ConnectionError, OSError) as e:
                last_error = e
                logger.error(f"DeepSeek API网络连接失败，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"DeepSeek API数据处理错误: {e}")
                raise ValueError(f"API响应数据格式错误: {e}")
            except Exception as e:
                last_error = e
                logger.error(f"DeepSeek API未知错误，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
        
        # 所有重试都失败了
        if isinstance(last_error, RateLimitError):
            raise APIRateLimitError(f"DeepSeek API速率限制，已达到最大重试次数: {last_error}")
        else:
            raise APIConnectionError("DeepSeek", f"API调用失败，已达到最大重试次数: {last_error}")
    
    async def generate_post(self, system_prompt: str, context: Optional[str] = None, prompt: Optional[str] = None) -> str:
        """生成社交媒体帖子
        
        Args:
            system_prompt: 系统提示词
            context: 上下文信息
            prompt: 用户提示词
            
        Returns:
            生成的帖子内容
        """
        # 构建完整的提示词
        full_prompt = ""
        if context:
            full_prompt += f"上下文信息：{context}\n\n"
        if prompt:
            full_prompt += f"用户要求：{prompt}\n\n"
        full_prompt += "请生成一条有趣、有价值的社交媒体帖子。"
        
        return await self.generate_text(full_prompt, system_prompt, max_tokens=500, temperature=0.8)
    
    async def generate_reply(self, original_text: str, system_prompt: str, username: Optional[str] = None) -> str:
        """生成回复内容
        
        Args:
            original_text: 原始帖子内容
            system_prompt: 系统提示词
            username: 用户名（可选）
            
        Returns:
            生成的回复内容
        """
        # 构建回复提示词
        reply_prompt = f"请对以下内容生成一个有见解、友善的回复：\n\n{original_text}"
        
        if username:
            reply_prompt += f"\n\n（回复给用户：@{username}）"
        
        return await self.generate_text(reply_prompt, system_prompt, max_tokens=300, temperature=0.7)
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], 
                                      max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE) -> str:
        """生成聊天响应
        
        Args:
            chat_history: 聊天历史，格式为 [{"role": "user", "content": "..."}, ...]
            system_prompt: 系统提示词
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的聊天响应
            
        Raises:
            ValueError: 当输入参数无效时
            APIConnectionError: 当API连接失败时
            APIRateLimitError: 当API速率限制时
            CustomAuthError: 当API认证失败时
        """
        # 输入验证
        if not messages or not isinstance(messages, list):
            raise ValueError("消息列表不能为空且必须是列表")
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"消息 {i} 必须是字典格式")
            if 'role' not in msg or 'content' not in msg:
                raise ValueError(f"消息 {i} 必须包含 'role' 和 'content' 字段")
            if not isinstance(msg['content'], str) or len(msg['content'].strip()) == 0:
                raise ValueError(f"消息 {i} 的内容不能为空")
        
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ValueError("最大token数必须是正整数")
        
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("温度值必须在0到2之间")
        
        # 使用传入的消息列表
        api_messages = messages.copy()
        
        last_error = None
        
        # 调用API生成响应
        for attempt in range(self.max_retries):
            try:
                logger.info(f"正在调用DeepSeek API生成聊天响应，尝试次数: {attempt + 1}/{self.max_retries}")
                
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    ),
                    timeout=DEFAULT_API_TIMEOUT
                )
                
                generated_text = response.choices[0].message.content
                if not generated_text:
                    raise APIConnectionError("DeepSeek", "API返回空内容")
                
                logger.info(f"成功生成聊天响应，长度: {len(generated_text)}")
                return generated_text.strip()
                
            except RateLimitError as e:
                last_error = e
                logger.warning(f"API速率限制，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
                    
            except BadRequestError as e:
                logger.error(f"API请求错误: {e}")
                raise ValueError(f"API请求参数错误: {e}")
                
            except AuthenticationError as e:
                logger.error(f"API认证错误: {e}")
                raise CustomAuthError(f"DeepSeek API认证失败: {e}")
                
            except (APITimeoutError, Timeout, asyncio.TimeoutError, APIError) as e:
                last_error = e
                logger.warning(f"API超时或临时错误，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1 and self._is_retryable_error(e):
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
                    
            except (ConnectionError, OSError) as e:
                last_error = e
                logger.error(f"DeepSeek API网络连接失败，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"DeepSeek API数据处理错误: {e}")
                raise ValueError(f"API响应数据格式错误: {e}")
            except Exception as e:
                last_error = e
                logger.error(f"DeepSeek API未知错误，尝试 {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试")
                    await asyncio.sleep(delay)
        
        # 所有重试都失败了
        if isinstance(last_error, RateLimitError):
            raise APIRateLimitError(f"DeepSeek API速率限制，已达到最大重试次数: {last_error}")
        else:
            raise APIConnectionError("DeepSeek", f"API调用失败，已达到最大重试次数: {last_error}")