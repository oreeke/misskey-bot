#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置模块

这个模块负责加载和管理机器人的配置。
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, TypeVar, Generic
from urllib.parse import urlparse

import yaml
from loguru import logger

from .exceptions import ConfigurationError
from .constants import (
    DEFAULT_MAX_DAILY_POSTS,
    DEFAULT_MAX_POST_LENGTH,
    MAX_POST_LENGTH
)

# 泛型类型变量
T = TypeVar('T')


class Config:
    """配置类，负责加载和管理配置"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置类
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的config.yaml
        """
        self.config_path = config_path or os.environ.get("CONFIG_PATH", "config.yaml")
        self.config: Dict[str, Any] = {}
    
    async def load(self) -> None:
        """加载配置文件"""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            raise ConfigurationError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"已加载配置文件: {config_path}")
            
            # 使用环境变量覆盖配置（如果存在）
            self._override_from_env()
            
            # 验证配置
            self._validate_config()
            
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise ConfigurationError(f"配置文件格式错误: {e}")
        except FileNotFoundError as e:
            logger.error(f"配置文件不存在: {e}")
            raise ConfigurationError(f"配置文件不存在: {e}")
        except PermissionError as e:
            logger.error(f"配置文件权限不足: {e}")
            raise ConfigurationError(f"配置文件权限不足: {e}")
        except (OSError, IOError) as e:
            logger.error(f"配置文件读取错误: {e}")
            raise ConfigurationError(f"配置文件读取错误: {e}")
        except Exception as e:
            logger.error(f"加载配置文件未知错误: {e}")
            raise ConfigurationError(f"加载配置文件未知错误: {e}")
    
    def _override_from_env(self) -> None:
        """从环境变量覆盖配置"""
        # Misskey配置
        if os.environ.get("MISSKEY_INSTANCE_URL"):
            self.config.setdefault("misskey", {})[
                "instance_url"
            ] = os.environ.get("MISSKEY_INSTANCE_URL")
        
        if os.environ.get("MISSKEY_ACCESS_TOKEN"):
            self.config.setdefault("misskey", {})[
                "access_token"
            ] = os.environ.get("MISSKEY_ACCESS_TOKEN")
        
        # DeepSeek配置
        if os.environ.get("DEEPSEEK_API_KEY"):
            self.config.setdefault("deepseek", {})[
                "api_key"
            ] = os.environ.get("DEEPSEEK_API_KEY")
        
        if os.environ.get("DEEPSEEK_MODEL"):
            self.config.setdefault("deepseek", {})[
                "model"
            ] = os.environ.get("DEEPSEEK_MODEL")
        
        # 自动发帖配置
        if os.environ.get("BOT_AUTO_POST_ENABLED"):
            self.config.setdefault("bot", {}).setdefault("auto_post", {})[
                "enabled"
            ] = os.environ.get("BOT_AUTO_POST_ENABLED").lower() in ("true", "1", "yes")
        
        if os.environ.get("BOT_AUTO_POST_INTERVAL"):
            self.config.setdefault("bot", {}).setdefault("auto_post", {})[
                "interval_minutes"
            ] = int(os.environ.get("BOT_AUTO_POST_INTERVAL", "60"))
            
        if os.environ.get("BOT_AUTO_POST_MAX_PER_DAY"):
            self.config.setdefault("bot", {}).setdefault("auto_post", {})[
                "max_posts_per_day"
            ] = int(os.environ.get("BOT_AUTO_POST_MAX_PER_DAY", "10"))
            
        if os.environ.get("BOT_AUTO_POST_MAX_LENGTH"):
            self.config.setdefault("bot", {}).setdefault("auto_post", {})[
                "max_post_length"
            ] = int(os.environ.get("BOT_AUTO_POST_MAX_LENGTH", "500"))
            
        if os.environ.get("BOT_AUTO_POST_PROMPT"):
            self.config.setdefault("bot", {}).setdefault("auto_post", {})[
                "prompt"
            ] = os.environ.get("BOT_AUTO_POST_PROMPT")
        
        # 响应配置
        if os.environ.get("BOT_RESPONSE_MENTION_ENABLED"):
            self.config.setdefault("bot", {}).setdefault("response", {})[
                "mention_enabled"
            ] = os.environ.get("BOT_RESPONSE_MENTION_ENABLED").lower() in ("true", "1", "yes")
            
        if os.environ.get("BOT_RESPONSE_CHAT_ENABLED"):
            self.config.setdefault("bot", {}).setdefault("response", {})[
                "chat_enabled"
            ] = os.environ.get("BOT_RESPONSE_CHAT_ENABLED").lower() in ("true", "1", "yes")
            
        if os.environ.get("BOT_RESPONSE_MAX_LENGTH"):
            self.config.setdefault("bot", {}).setdefault("response", {})[
                "max_response_length"
            ] = int(os.environ.get("BOT_RESPONSE_MAX_LENGTH", "500"))
        
        # 笔记可见性配置
        if os.environ.get("BOT_DEFAULT_VISIBILITY"):
            self.config.setdefault("bot", {}).setdefault("visibility", {})[
                "default"
            ] = os.environ.get("BOT_DEFAULT_VISIBILITY")
        
        # 系统提示词
        if os.environ.get("SYSTEM_PROMPT"):
            self.config["system_prompt"] = os.environ.get("SYSTEM_PROMPT")
    
    def _validate_config(self) -> None:
        """验证配置的完整性和有效性"""
        required_configs: List[Tuple[str, str]] = [
            ("misskey.instance_url", "Misskey实例URL"),
            ("misskey.access_token", "Misskey访问令牌"),
            ("deepseek.api_key", "DeepSeek API密钥"),
        ]
        
        missing_configs = []
        for config_path, config_name in required_configs:
            if not self.get(config_path):
                missing_configs.append(config_name)
        
        if missing_configs:
            error_msg = f"缺少必要的配置项: {', '.join(missing_configs)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        # 验证URL格式
        instance_url = self.get("misskey.instance_url")
        if instance_url and not self._is_valid_url(instance_url):
            error_msg = f"Misskey实例URL格式无效: {instance_url}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 验证API密钥格式
        deepseek_key = self.get("deepseek.api_key")
        if deepseek_key and not self._is_valid_api_key(deepseek_key):
            error_msg = "DeepSeek API密钥格式无效"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 自动发帖配置不进行验证，允许用户自由设置
        
        logger.info("配置验证通过")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值，如果配置不存在则返回此值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL格式是否有效
        
        Args:
            url: 要验证的URL
            
        Returns:
            布尔值，表示URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except (ValueError, TypeError):
            return False
        except Exception:
            return False
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        """验证API密钥格式是否有效
        
        Args:
            api_key: 要验证的API密钥
            
        Returns:
            布尔值，表示API密钥是否有效
        """
        if not api_key or not isinstance(api_key, str):
            return False
        
        # 基本长度检查（API密钥通常较长）
        if len(api_key.strip()) < 10:
            return False
        
        # 检查是否包含明显的占位符文本
        placeholder_patterns = [
            r'your.*key.*here',
            r'replace.*with.*key',
            r'api.*key.*placeholder',
            r'sk-[a-zA-Z0-9]{20,}',  # OpenAI风格的密钥格式
        ]
        
        api_key_lower = api_key.lower()
        for pattern in placeholder_patterns[:-1]:  # 排除最后一个正常格式
            if re.search(pattern, api_key_lower):
                return False
        
        return True
    
    def get_typed(self, key: str, default: T = None, expected_type: type = None) -> T:
        """获取指定类型的配置值
        
        Args:
            key: 配置键
            default: 默认值
            expected_type: 期望的类型
            
        Returns:
            指定类型的配置值
            
        Raises:
            ValueError: 当配置值类型不匹配时
        """
        value = self.get(key, default)
        
        if expected_type and value is not None and not isinstance(value, expected_type):
            raise ValueError(f"配置项 {key} 期望类型 {expected_type.__name__}，实际类型 {type(value).__name__}")
        
        return value