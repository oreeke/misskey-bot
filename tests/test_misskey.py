#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Misskey API 测试脚本

这个脚本用于测试Misskey API的连接和功能。
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
from src.misskey_api import MisskeyAPI
from src.config import Config
from src.utils import check_api_health

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_misskey')


@pytest.mark.asyncio
async def test_misskey_api():
    """测试Misskey API"""
    logger.info("开始测试Misskey API连接")
    
    # 尝试从配置文件加载
    try:
        config = Config()
        await config.load()
        instance_url = config.get('misskey.instance_url')
        access_token = config.get('misskey.access_token')
        logger.info("从配置文件加载成功")
    except Exception as e:
        logger.warning(f"从配置文件加载失败: {e}，尝试从环境变量加载")
        # 加载环境变量
        load_dotenv()
        # 获取API配置
        instance_url = os.environ.get("MISSKEY_INSTANCE_URL")
        access_token = os.environ.get("MISSKEY_ACCESS_TOKEN")
    
    if not instance_url or not access_token:
        logger.error("错误: 未设置Misskey实例URL或访问令牌，请检查配置文件或环境变量")
        return False
    
    # 初始化Misskey API客户端
    misskey = MisskeyAPI(instance_url=instance_url, access_token=access_token)
    
    # 测试获取当前用户信息
    try:
        logger.info("获取当前用户信息...")
        me = await misskey.request("i")
        logger.info(f"用户名: {me.get('username')}")
        logger.info(f"显示名称: {me.get('name')}")
        logger.info(f"描述: {me.get('description')}")
        
        # 获取实例信息
        logger.info("获取实例信息...")
        instance = await misskey.request('meta')
        logger.info(f"实例名称: {instance.get('name')}")
        logger.info(f"实例版本: {instance.get('version')}")
        
        # 测试健康检查函数
        logger.info("执行API健康检查...")
        # 创建一个健康检查函数
        async def check_misskey_health():
            try:
                me = await misskey.request("i")
                return me is not None and "id" in me
            except Exception:
                return False
        
        health_status = await check_api_health(check_misskey_health, "Misskey")
        logger.info(f"API健康状态: {health_status}")
        
        logger.info("API连接成功!")
        
        # 测试发送一条测试笔记
        post = input("\n是否发送测试笔记? (y/n): ")
        if post.lower() == "y":
            note_text = "这是一条测试笔记，来自Misskey Bot测试脚本。"
            logger.info(f"发送笔记: {note_text}")
            result = await misskey.create_note(note_text)
            logger.info("笔记已发送!")
        
        return True
    except Exception as e:
        logger.error(f"API连接测试失败: {e}")
        return False
    finally:
        # 关闭API客户端
        await misskey.close()


async def main():
    """主函数"""
    success = await test_misskey_api()
    if success:
        print("\n✅ Misskey API连接测试成功!")
        return 0
    else:
        print("\n❌ Misskey API连接测试失败!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)