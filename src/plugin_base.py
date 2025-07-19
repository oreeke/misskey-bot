#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        self.enabled = config.get("enabled", False)
        self.priority = config.get("priority", 0)

    @abstractmethod
    async def initialize(self) -> bool:
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        pass

    async def on_mention(self, _mention_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None

    async def on_message(self, _message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None

    async def on_auto_post(self) -> Optional[Dict[str, Any]]:
        return None

    async def on_startup(self) -> None:
        pass

    async def on_auto_post(self) -> Optional[Dict[str, Any]]:
        return None

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "description": getattr(self, "description", "No description available")
        }

    def _extract_username(self, data: Dict[str, Any]) -> str:
        user_info = data.get("fromUser") or data.get("user", {})
        return user_info.get("username", "unknown") if isinstance(user_info, dict) else "unknown"

    def _log_plugin_action(self, action: str, details: str = "") -> None:
        if details:
            logger.info(f"{self.name} 插件{action}: {details}")
        else:
            logger.info(f"{self.name} 插件{action}")

    def _validate_plugin_response(self, response: Dict[str, Any]) -> bool:
        if not isinstance(response, dict):
            return False
        if "handled" in response and not isinstance(response["handled"], bool):
            return False
        if "plugin_name" in response and not isinstance(response["plugin_name"], str):
            return False
        if "response" in response and not isinstance(response["response"], str):
            return False
        return True

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        logger.info(f"插件 {self.name} {'启用' if enabled else '禁用'}")
