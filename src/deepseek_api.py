#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from typing import Dict, List, Optional

from loguru import logger
import openai

from .exceptions import (
    APIConnectionError,
    APIRateLimitError,
    AuthenticationError as CustomAuthError
)
from .utils import retry_async

try:
    from openai import (
        RateLimitError,
        APIError,
        AuthenticationError,
        BadRequestError,
        APITimeoutError,
        Timeout
    )
except ImportError as e:
    logger.error(f"无法导入 DeepSeek API 异常类: {e}")

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
    class Timeout(Exception):
        pass

class DeepSeekAPI:
    def __init__(self, api_key: str, model: str = "deepseek-chat", api_base: Optional[str] = None, max_retries: int = 3, timeout: int = 30):
        from .api_validation import validate_token_param, validate_url_param, log_validation_error
        try:
            self.api_key = validate_token_param(api_key, "API 密钥")
            self.model = validate_token_param(model, "模型名称")
            if not isinstance(max_retries, int) or max_retries < 0:
                raise ValueError("最大重试次数必须是非负整数")
            self.max_retries = max_retries
            self.timeout = timeout
            api_base_url = api_base if api_base else "https://api.deepseek.com/v1"
            self.api_base = validate_url_param(api_base_url, "API base URL")
        except ValueError as e:
            log_validation_error(e, "DeepSeek API 初始化")
            raise
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout
            )
            logger.debug(f"DeepSeek API 客户端初始化完成，base_url={self.api_base}")
        except Exception as e:
            logger.error(f"创建 DeepSeek API 客户端失败: {e}")
            raise APIConnectionError("DeepSeek", f"客户端初始化失败: {e}")

    def _validate_params(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> None:
        from .api_validation import validate_token_param, validate_numeric_param, log_validation_error
        try:
            validate_token_param(prompt, "提示内容")
            if system_prompt:
                validate_token_param(system_prompt, "系统提示")
            validate_numeric_param(max_tokens, "max_tokens", min_value=1, max_value=4096)
            validate_numeric_param(temperature, "temperature", min_value=0, max_value=2)
        except ValueError as e:
            log_validation_error(e, "DeepSeek API 参数验证")
            raise
    
    @retry_async(max_retries=3, retryable_exceptions=(RateLimitError, APITimeoutError, Timeout, APIError, ConnectionError, OSError))
    async def _call_api(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ),
                timeout=self.timeout
            )
            generated_text = response.choices[0].message.content
            if not generated_text:
                raise APIConnectionError("DeepSeek", "API 返回空内容")
            logger.debug(f"DeepSeek API 单轮文本调用成功，生成内容长度: {len(generated_text)}")
            return generated_text
        except BadRequestError as e:
            raise ValueError(f"API 请求参数错误: {e}")
        except AuthenticationError as e:
            raise CustomAuthError(f"DeepSeek API 认证失败: {e}")
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"API 响应数据格式错误: {e}")
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, 
                            max_tokens: int = 1000, temperature: float = 0.8) -> str:
        self._validate_params(prompt, system_prompt, max_tokens, temperature)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})
        try:
            return await self._call_api(messages, max_tokens, temperature)
        except (RateLimitError, APITimeoutError, Timeout, APIError, ConnectionError, OSError) as e:
            if isinstance(e, RateLimitError):
                raise APIRateLimitError(f"DeepSeek API 速率限制: {e}")
            else:
                raise APIConnectionError("DeepSeek", f"API 调用失败: {e}")
    
    def close(self):
        if hasattr(self, 'client') and self.client:
            self.client.close()
            logger.debug("DeepSeek API 客户端连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def generate_post(self, system_prompt: str, prompt: Optional[str] = None, max_tokens: int = 1000, temperature: float = 0.8) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("缺少提示词")
        return await self.generate_text(prompt, system_prompt, max_tokens=max_tokens, temperature=temperature)
    
    async def generate_reply(self, original_text: str, system_prompt: str, username: Optional[str] = None, max_tokens: int = 300, temperature: float = 0.8) -> str:
        reply_prompt = original_text
        if username:
            reply_prompt += f"\n\n（回复用户：@{username}）"
        return await self.generate_text(reply_prompt, system_prompt, max_tokens=max_tokens, temperature=temperature)
    
    def _validate_chat_messages(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> None:
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
            raise ValueError("最大 token 数必须是正整数")
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("温度值必须在 0 到 2 之间")
    
    @retry_async(max_retries=3, retryable_exceptions=(RateLimitError, APITimeoutError, Timeout, APIError, ConnectionError, OSError))
    async def _call_chat_api(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ),
                timeout=self.timeout
            )
            generated_text = response.choices[0].message.content
            if not generated_text:
                raise APIConnectionError("DeepSeek", "API 返回空内容")
            logger.debug(f"DeepSeek API 多轮对话调用成功，生成内容长度: {len(generated_text)}")
            return generated_text.strip()
        except BadRequestError as e:
            raise ValueError(f"API 请求参数错误: {e}")
        except AuthenticationError as e:
            raise CustomAuthError(f"DeepSeek API 认证失败: {e}")
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"API 响应数据格式错误: {e}")
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], 
                                      max_tokens: int = 1000, temperature: float = 0.8) -> str:
        self._validate_chat_messages(messages, max_tokens, temperature)
        try:
            return await self._call_chat_api(messages, max_tokens, temperature)
        except (RateLimitError, APITimeoutError, Timeout, APIError, ConnectionError, OSError) as e:
            if isinstance(e, RateLimitError):
                raise APIRateLimitError(f"DeepSeek API 速率限制: {e}")
            else:
                raise APIConnectionError("DeepSeek", f"API 调用失败: {e}")