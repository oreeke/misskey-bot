#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
from pathlib import Path
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

def test_all_imports():
    
    from src.exceptions import (
        MisskeyBotError, ConfigurationError, APIConnectionError,
        APIRateLimitError, AuthenticationError, WebSocketConnectionError,
        MisskeyAPIError, DeepSeekAPIError
    )
    
    from src.constants import (
        DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_VISIBILITY,
        HTTP_OK, HTTP_UNAUTHORIZED, HTTP_TOO_MANY_REQUESTS
    )
    
    from src.config import Config
    from src.utils import health_check, get_memory_usage, get_system_info
    from src.persistence import PersistenceManager
    from src.misskey_api import MisskeyAPI
    from src.deepseek_api import DeepSeekAPI
    from src.bot import MisskeyBot
    from src.main import main, shutdown
    
    
    assert MisskeyBotError is not None
    assert Config is not None
    assert health_check is not None
    assert PersistenceManager is not None
    assert MisskeyAPI is not None
    assert DeepSeekAPI is not None
    assert MisskeyBot is not None
    assert main is not None
    assert shutdown is not None

def test_health_check():
    from src.utils import health_check
    result = health_check()
    assert result is not None
    assert isinstance(result, (bool, str, dict))

def test_config_loading():
    from src.config import Config
    config = Config()
    assert config is not None
    
    
    default_visibility = config.get('bot.visibility.default', 'public')
    assert default_visibility in ['public', 'unlisted', 'followers', 'specified']
    
    
    assert hasattr(config, 'get')
    assert callable(config.get)

def test_exception_classes():
    from src.exceptions import MisskeyAPIError, DeepSeekAPIError
    
    
    error1 = MisskeyAPIError("测试错误", 404)
    assert isinstance(error1, Exception)
    assert "测试错误" in str(error1)
    assert error1.status_code == 404
    
    
    error2 = DeepSeekAPIError("测试错误", "invalid_request")
    assert isinstance(error2, Exception)
    assert "测试错误" in str(error2)
    assert error2.error_code == "invalid_request"

@pytest.mark.slow
def test_docker_build():
    
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )
    except FileNotFoundError:
        pytest.skip("Docker命令未找到，请确保Docker已安装")
    
    if result.returncode != 0:
        pytest.skip("Docker不可用，跳过构建测试")
    
    
    build_result = subprocess.run(
        ["docker", "build", "-t", "misskey-ai-test", "."],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        timeout=300
    )
    
    try:
        assert build_result.returncode == 0, f"Docker构建失败: {build_result.stderr}"
    finally:
        
        subprocess.run(
            ["docker", "rmi", "misskey-ai-test"],
            capture_output=True,
            encoding='utf-8',
            errors='ignore'
        )

def test_docker_compose_syntax():
    try:
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=30
        )
    except FileNotFoundError:
        pytest.skip("docker-compose命令未找到")
    
    assert result.returncode == 0, f"docker-compose.yaml语法错误: {result.stderr}"


# pytest tests/test_build.py -v
# pytest tests/test_build.py::test_all_imports -v