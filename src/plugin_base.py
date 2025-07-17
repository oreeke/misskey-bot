#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger

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
    
    async def on_shutdown(self) -> None:
        pass
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "description": getattr(self, "description", "No description available")
        }
    
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        logger.info(f"插件 {self.name} {'启用' if enabled else '禁用'}")