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
async def test_deepseek_api():
    """测试DeepSeek API"""
    logger.info("开始测试DeepSeek API连接")
    
    # 尝试从配置文件加载
    try:
        config = Config()
        await config.load()
        api_key = config.get('deepseek.api_key')
        model = config.get('deepseek.model', 'deepseek-chat')
        logger.info("从配置文件加载成功")
    except Exception as e:
        logger.warning(f"从配置文件加载失败: {e}，尝试从环境变量加载")
        # 加载环境变量
        load_dotenv()
        # 获取API配置
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    
    if not api_key:
        logger.error("错误: 未设置DeepSeek API密钥，请检查配置文件或环境变量")
        return False
    
    # 初始化DeepSeek API客户端
    deepseek = DeepSeekAPI(api_key=api_key, model=model)
    logger.info(f"使用模型: {model}")
    
    try:
        prompt = "你好，请用一句话介绍一下自己。"
        system_prompt = "你是一个友好的AI助手，名叫DeepSeek。"
        
        logger.info(f"发送提示: {prompt}")
        logger.info(f"系统提示: {system_prompt}")
        
        response = await deepseek.generate_text(prompt, system_prompt)
        logger.info(f"收到回复: {response}")
        
        user_message = "今天天气怎么样？"
        logger.info(f"测试聊天响应生成，用户消息: '{user_message}'")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        chat_response = await deepseek.generate_chat_response(
            messages=messages
        )
        logger.info(f"生成的聊天响应: {chat_response}")
        
        logger.info("DeepSeek API连接测试成功!")
        return True
    except Exception as e:
        logger.error(f"DeepSeek API连接测试失败: {e}")
        return False


async def main():
    """主函数"""
    success = await test_deepseek_api()
    if success:
        print("\n✅ DeepSeek API连接测试成功!")
        return 0
    else:
        print("\n❌ DeepSeek API连接测试失败!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)