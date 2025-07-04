#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
构建验证测试

用于验证项目的所有模块导入和Docker构建是否正常。"""

import sys
import subprocess
from pathlib import Path
import pytest

# 确保src目录在Python路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_all_imports():
    """测试所有模块的导入"""
    # 测试基础模块
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
    
    # 验证关键类和函数存在
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
    """测试健康检查函数"""
    from src.utils import health_check
    result = health_check()
    assert result is not None
    assert isinstance(result, (bool, str, dict))  # 健康检查应返回有意义的结果

def test_config_loading():
    """测试配置加载"""
    from src.config import Config
    config = Config()
    assert config is not None
    
    # 测试默认配置
    default_visibility = config.get('bot.visibility.default', 'public')
    assert default_visibility in ['public', 'unlisted', 'followers', 'specified']
    
    # 测试配置方法存在
    assert hasattr(config, 'get')
    assert callable(config.get)

def test_exception_classes():
    """测试异常类"""
    from src.exceptions import MisskeyAPIError, DeepSeekAPIError
    
    # 测试MisskeyAPIError
    error1 = MisskeyAPIError("测试错误", 404)
    assert isinstance(error1, Exception)
    assert "测试错误" in str(error1)
    assert error1.status_code == 404
    
    # 测试DeepSeekAPIError
    error2 = DeepSeekAPIError("测试错误", "invalid_request")
    assert isinstance(error2, Exception)
    assert "测试错误" in str(error2)
    assert error2.error_code == "invalid_request"

@pytest.mark.slow
def test_docker_build():
    """测试Docker构建"""
    # 检查Docker是否可用
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
    
    # 测试Docker构建
    build_result = subprocess.run(
        ["docker", "build", "-t", "misskey-bot-test", "."],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        timeout=300  # 5分钟超时
    )
    
    try:
        assert build_result.returncode == 0, f"Docker构建失败: {build_result.stderr}"
    finally:
        # 清理测试镜像
        subprocess.run(
            ["docker", "rmi", "misskey-bot-test"],
            capture_output=True,
            encoding='utf-8',
            errors='ignore'
        )

def test_docker_compose_syntax():
    """测试docker-compose文件语法"""
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

# 可以通过 pytest 命令运行这些测试:
# pytest tests/test_build.py -v
# pytest tests/test_build.py::test_all_imports -v
# pytest tests/test_build.py -m "not slow" -v  # 跳过慢速测试