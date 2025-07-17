#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, TypeVar
from urllib.parse import urlparse

import yaml
from loguru import logger

from .exceptions import ConfigurationError

T = TypeVar('T')

class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.environ.get("CONFIG_PATH", "config.yaml")
        self.config: Dict[str, Any] = {}
    
    async def load(self) -> None:
        config_path = Path(self.config_path)
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            raise ConfigurationError(f"配置文件不存在: {config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            logger.debug(f"已加载配置文件: {config_path}")
            self._override_from_env()
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
        env_mappings = {
            "MISSKEY_INSTANCE_URL": ("misskey.instance_url", str),
            "MISSKEY_ACCESS_TOKEN": ("misskey.access_token", str),
            "DEEPSEEK_API_KEY": ("deepseek.api_key", str),
            "DEEPSEEK_MODEL": ("deepseek.model", str),
            "DEEPSEEK_API_BASE": ("deepseek.api_base", str),
            "DEEPSEEK_MAX_TOKENS": ("deepseek.max_tokens", int),
            "DEEPSEEK_TEMPERATURE": ("deepseek.temperature", float),
            "BOT_SYSTEM_PROMPT": ("bot.system_prompt", str),
            "BOT_AUTO_POST_ENABLED": ("bot.auto_post.enabled", bool),
            "BOT_AUTO_POST_INTERVAL": ("bot.auto_post.interval_minutes", int),
            "BOT_AUTO_POST_MAX_PER_DAY": ("bot.auto_post.max_posts_per_day", int),
            "BOT_AUTO_POST_VISIBILITY": ("bot.auto_post.visibility", str),
            "BOT_AUTO_POST_PROMPT": ("bot.auto_post.prompt", str),
            "BOT_RESPONSE_MENTION_ENABLED": ("bot.response.mention_enabled", bool),
            "BOT_RESPONSE_CHAT_ENABLED": ("bot.response.chat_enabled", bool),
            "BOT_RESPONSE_CHAT_MEMORY": ("bot.response.chat_memory", int),
            "BOT_RESPONSE_POLLING_INTERVAL": ("bot.response.polling_interval", int),
            "API_TIMEOUT": ("api.timeout", int),
            "API_MAX_RETRIES": ("api.max_retries", int),
            "DB_CLEANUP_DAYS": ("db.cleanup_days", int),
            "LOG_LEVEL": ("logging.level", str)
        }
        for env_key, (config_path, value_type) in env_mappings.items():
            env_value = os.environ.get(env_key)
            if env_value:
                self._set_config_value(config_path, env_value, value_type)
    
    def _set_config_value(self, path: str, value: str, value_type: type) -> None:
        keys = path.split(".")
        config = self.config
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        if value_type == bool:
            config[keys[-1]] = value.lower() in ("true", "1", "yes")
        elif value_type == int:
            config[keys[-1]] = int(value)
        elif value_type == float:
            config[keys[-1]] = float(value)
        else:
            config[keys[-1]] = self._process_string_value(value, path)
    
    def _process_string_value(self, value: Any, config_path: str) -> str:
        if not isinstance(value, str):
            return value
        if value.startswith("file://"):
            return self._load_from_file(value[7:])
        if self._is_prompt_config(config_path) and self._looks_like_file_path(value):
            return self._load_from_file(value)
        return value
    
    def _load_from_file(self, file_path: str) -> str:
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = Path(self.config_path).parent / path
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.debug(f"从文件加载配置: {file_path}")
                return content
        except Exception as e:
            logger.debug(f"无法从文件加载配置 {file_path}: {e}，使用原始值")
            return file_path
    
    def _looks_like_file_path(self, value: str) -> bool:
        if len(value) > 200:
            return False
        file_indicators = ['.txt']
        if any(value.endswith(ext) for ext in file_indicators):
            return True
        path_indicators = ['prompts']
        return any(indicator in value for indicator in path_indicators)
    
    def _is_prompt_config(self, config_path: str) -> bool:
        prompt_configs = [
            'bot.system_prompt',
            'bot.auto_post.prompt'
        ]
        return config_path in prompt_configs
    
    def _validate_config(self) -> None:
        required_configs: List[Tuple[str, str]] = [
            ("misskey.instance_url", "Misskey 实例URL"),
            ("misskey.access_token", "Misskey 访问令牌"),
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
        instance_url = self.get("misskey.instance_url")
        if instance_url and not self._is_valid_url(instance_url):
            error_msg = f"Misskey实例URL格式无效: {instance_url}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        deepseek_key = self.get("deepseek.api_key")
        if deepseek_key and not self._is_valid_api_key(deepseek_key):
            error_msg = "DeepSeek API密钥格式无效"
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.debug("配置验证通过")
    
    def get(self, key: str, default: Any = None) -> Any:
        if key == "persistence.db_path":
            return "data/misskey_ai.db"
        if key == "logging.path":
            return "logs"
            
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                if default is None:
                    default = self._get_builtin_default(key)
                return default
        return value
    
    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except (ValueError, TypeError):
            return False
        except Exception:
            return False
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        if not api_key or not isinstance(api_key, str):
            return False
        if len(api_key.strip()) < 10:
            return False
        placeholder_patterns = [
            r'your.*key.*here',
            r'replace.*with.*key',
            r'api.*key.*placeholder',
            r'sk-[a-zA-Z0-9]{20,}',
        ]
        api_key_lower = api_key.lower()
        for pattern in placeholder_patterns[:-1]:
            if re.search(pattern, api_key_lower):
                return False
        return True
    
    def _get_builtin_default(self, key: str) -> Any:
        builtin_defaults = {
            "deepseek.model": "deepseek-chat",
            "deepseek.api_base": "https://api.deepseek.com/v1",
            "deepseek.max_tokens": 1000,
            "deepseek.temperature": 0.8,
            
            "bot.auto_post.enabled": True,
            "bot.auto_post.interval_minutes": 180,
            "bot.auto_post.max_posts_per_day": 8,
            "bot.auto_post.visibility": "public",
            "bot.response.mention_enabled": True,
            "bot.response.chat_enabled": True,
            "bot.response.chat_memory": 10,
            "bot.response.polling_interval": 60,
            
            "api.timeout": 30,
            "api.max_retries": 3,
            
            "db.cleanup_days": 30,
            
            "logging.level": "INFO",
        }
        return builtin_defaults.get(key)
    
    def get_typed(self, key: str, default: T = None, expected_type: type = None) -> T:
        value = self.get(key, default)
        if expected_type and value is not None and not isinstance(value, expected_type):
            raise ValueError(f"配置项 {key} 期望类型 {expected_type.__name__}，实际类型 {type(value).__name__}")
        return value