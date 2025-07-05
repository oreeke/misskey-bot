#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import logging
from pathlib import Path
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.deepseek_api import DeepSeekAPI
from src.config import Config


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_deepseek')


@pytest.mark.asyncio
@pytest.mark.integration
async def test_deepseek_api():
    
    try:
        config = Config()
        await config.load()
        api_key = config.get('deepseek.api_key')
        model = config.get('deepseek.model', 'deepseek-chat')
    except Exception as e:
        logger.warning(f"从配置文件加载失败: {e}，尝试从环境变量加载")
        
        load_dotenv()
        
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    
    if not api_key:
        pytest.skip("DeepSeek API密钥未配置，跳过API测试")
    
    
    deepseek = DeepSeekAPI(api_key=api_key, model=model)
    assert deepseek is not None
    
    
    prompt = "你好，请用一句话介绍一下自己。"
    system_prompt = "你是一个友好的AI助手，名叫DeepSeek。"
    
    response = await deepseek.generate_text(prompt, system_prompt)
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    
    
    user_message = "今天天气怎么样？"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    chat_response = await deepseek.generate_chat_response(messages=messages)
    assert chat_response is not None
    assert isinstance(chat_response, str)
    assert len(chat_response) > 0



# pytest tests/test_deepseek.py -v
# pytest tests/test_deepseek.py::test_deepseek_api -v