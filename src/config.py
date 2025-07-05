#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
            
            logger.info(f"已加载配置文件: {config_path}")
            
    
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
    
        if os.environ.get("MISSKEY_INSTANCE_URL"):
            self.config.setdefault("misskey", {})[
                "instance_url"
            ] = os.environ.get("MISSKEY_INSTANCE_URL")
        
        if os.environ.get("MISSKEY_ACCESS_TOKEN"):
            self.config.setdefault("misskey", {})[
                "access_token"
            ] = os.environ.get("MISSKEY_ACCESS_TOKEN")
        
    
        if os.environ.get("DEEPSEEK_API_KEY"):
            self.config.setdefault("deepseek", {})[
                "api_key"
            ] = os.environ.get("DEEPSEEK_API_KEY")
        
        if os.environ.get("DEEPSEEK_MODEL"):
            self.config.setdefault("deepseek", {})[
                "model"
            ] = os.environ.get("DEEPSEEK_MODEL")
        
    
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
        
    
        if os.environ.get("BOT_DEFAULT_VISIBILITY"):
            self.config.setdefault("bot", {}).setdefault("visibility", {})[
                "default"
            ] = os.environ.get("BOT_DEFAULT_VISIBILITY")
        
    
        if os.environ.get("DEEPSEEK_API_BASE"):
            self.config.setdefault("deepseek", {})[
                "api_base"
            ] = os.environ.get("DEEPSEEK_API_BASE")
            
        if os.environ.get("DEEPSEEK_MAX_TOKENS"):
            self.config.setdefault("deepseek", {})[
                "max_tokens"
            ] = int(os.environ.get("DEEPSEEK_MAX_TOKENS", "1000"))
            
        if os.environ.get("DEEPSEEK_TEMPERATURE"):
            self.config.setdefault("deepseek", {})[
                "temperature"
            ] = float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.8"))
        
    
        if os.environ.get("API_TIMEOUT"):
            self.config.setdefault("api", {})[
                "timeout"
            ] = int(os.environ.get("API_TIMEOUT", "30"))
            
        if os.environ.get("API_MAX_RETRIES"):
            self.config.setdefault("api", {})[
                "max_retries"
            ] = int(os.environ.get("API_MAX_RETRIES", "3"))
            
        if os.environ.get("API_RETRY_DELAY"):
            self.config.setdefault("api", {})[
                "retry_delay"
            ] = float(os.environ.get("API_RETRY_DELAY", "1.0"))
        
    
        if os.environ.get("PERSISTENCE_DB_PATH"):
            self.config.setdefault("persistence", {})[
                "db_path"
            ] = os.environ.get("PERSISTENCE_DB_PATH")
            
        if os.environ.get("PERSISTENCE_CLEANUP_DAYS"):
            self.config.setdefault("persistence", {})[
                "cleanup_days"
            ] = int(os.environ.get("PERSISTENCE_CLEANUP_DAYS", "7"))
        
    
        if os.environ.get("LOG_LEVEL"):
            self.config.setdefault("logging", {})[
                "level"
            ] = os.environ.get("LOG_LEVEL")
            
        if os.environ.get("LOG_PATH"):
            self.config.setdefault("logging", {})[
                "path"
            ] = os.environ.get("LOG_PATH")
        
    
        if os.environ.get("SYSTEM_PROMPT"):
            self.config["system_prompt"] = os.environ.get("SYSTEM_PROMPT")
    
    def _validate_config(self) -> None:
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
        

        
        logger.info("配置验证通过")
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
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
    
    def get_typed(self, key: str, default: T = None, expected_type: type = None) -> T:
        value = self.get(key, default)
        
        if expected_type and value is not None and not isinstance(value, expected_type):
            raise ValueError(f"配置项 {key} 期望类型 {expected_type.__name__}，实际类型 {type(value).__name__}")
        
        return value