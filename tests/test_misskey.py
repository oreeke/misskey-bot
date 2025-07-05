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
from src.misskey_api import MisskeyAPI
from src.config import Config
from src.utils import check_api_health


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_misskey')


@pytest.mark.asyncio
@pytest.mark.integration
async def test_misskey_api():
    
    try:
        config = Config()
        await config.load()
        instance_url = config.get('misskey.instance_url')
        access_token = config.get('misskey.access_token')
    except Exception as e:
        logger.warning(f"从配置文件加载失败: {e}，尝试从环境变量加载")
        
        load_dotenv()
        
        instance_url = os.environ.get("MISSKEY_INSTANCE_URL")
        access_token = os.environ.get("MISSKEY_ACCESS_TOKEN")
    
    if not instance_url or not access_token:
        pytest.skip("Misskey实例URL或访问令牌未配置，跳过API测试")
    
    
    misskey = MisskeyAPI(instance_url=instance_url, access_token=access_token)
    assert misskey is not None
    
    try:
        
        me = await misskey.request("i")
        assert me is not None
        assert isinstance(me, dict)
        assert "id" in me
        assert "username" in me
        
        
        instance = await misskey.request('meta')
        assert instance is not None
        assert isinstance(instance, dict)
        assert "name" in instance
        assert "version" in instance
        
        
        async def check_misskey_health():
            try:
                me = await misskey.request("i")
                return me is not None and "id" in me
            except Exception:
                return False
        
        health_status = await check_api_health(check_misskey_health, "Misskey")
        assert health_status is True
        
    finally:
        
        await misskey.close()