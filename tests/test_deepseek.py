#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepSeek API 测试脚本

这个脚本用于测试DeepSeek API的连接和功能。
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import pytest

# 确保src目录在Python路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.deepseek_api import DeepSeekAPI
from src.config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_deepseek')


@pytest.mark.asyncio
@pytest.mark.integration
async def test_deepseek_api():
    """测试DeepSeek API"""
    # 尝试从配置文件加载
    try:
        config = Config()
        await config.load()
        api_key = config.get('deepseek.api_key')
        model = config.get('deepseek.model', 'deepseek-chat')
    except Exception as e:
        logger.warning(f"从配置文件加载失败: {e}，尝试从环境变量加载")
        # 加载环境变量
        load_dotenv()
        # 获取API配置
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    
    if not api_key:
        pytest.skip("DeepSeek API密钥未配置，跳过API测试")
    
    # 初始化DeepSeek API客户端
    deepseek = DeepSeekAPI(api_key=api_key, model=model)
    assert deepseek is not None
    
    # 测试文本生成
    prompt = "你好，请用一句话介绍一下自己。"
    system_prompt = "你是一个友好的AI助手，名叫DeepSeek。"
    
    response = await deepseek.generate_text(prompt, system_prompt)
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    
    # 测试聊天响应生成
    user_message = "今天天气怎么样？"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    chat_response = await deepseek.generate_chat_response(messages=messages)
    assert chat_response is not None
    assert isinstance(chat_response, str)
    assert len(chat_response) > 0


# 可以通过 pytest 命令运行这个测试:
# pytest tests/test_deepseek.py -v
# pytest tests/test_deepseek.py::test_deepseek_api -v
# pytest tests/test_deepseek.py -m "integration" -v  # 运行集成测试