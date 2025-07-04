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
@pytest.mark.integration
async def test_misskey_api():
    """测试Misskey API"""
    # 尝试从配置文件加载
    try:
        config = Config()
        await config.load()
        instance_url = config.get('misskey.instance_url')
        access_token = config.get('misskey.access_token')
    except Exception as e:
        logger.warning(f"从配置文件加载失败: {e}，尝试从环境变量加载")
        # 加载环境变量
        load_dotenv()
        # 获取API配置
        instance_url = os.environ.get("MISSKEY_INSTANCE_URL")
        access_token = os.environ.get("MISSKEY_ACCESS_TOKEN")
    
    if not instance_url or not access_token:
        pytest.skip("Misskey实例URL或访问令牌未配置，跳过API测试")
    
    # 初始化Misskey API客户端
    misskey = MisskeyAPI(instance_url=instance_url, access_token=access_token)
    assert misskey is not None
    
    try:
        # 测试获取当前用户信息
        me = await misskey.request("i")
        assert me is not None
        assert isinstance(me, dict)
        assert "id" in me
        assert "username" in me
        
        # 获取实例信息
        instance = await misskey.request('meta')
        assert instance is not None
        assert isinstance(instance, dict)
        assert "name" in instance
        assert "version" in instance
        
        # 测试健康检查函数
        async def check_misskey_health():
            try:
                me = await misskey.request("i")
                return me is not None and "id" in me
            except Exception:
                return False
        
        health_status = await check_api_health(check_misskey_health, "Misskey")
        assert health_status is True
        
    finally:
        # 关闭API客户端
        await misskey.close()


# 可以通过 pytest 命令运行这个测试:
# pytest tests/test_misskey.py -v
# pytest tests/test_misskey.py::test_misskey_api -v
# pytest tests/test_misskey.py -m "integration" -v  # 运行集成测试