#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, Any, Optional
from loguru import logger

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.plugin_base import PluginBase

class ExamplePlugin(PluginBase):
    
    description = "示例插件，展示插件系统的基本用法"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.greeting_enabled = config.get("greeting_enabled", True)
        self.auto_post_enabled = config.get("auto_post_enabled", False)
    
    async def initialize(self) -> bool:
        logger.info(f"示例插件初始化完成，问候功能: {'启用' if self.greeting_enabled else '禁用'}")
        return True
    
    async def cleanup(self) -> None:
        logger.info("示例插件清理完成")
    
    async def on_mention(self, mention_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.greeting_enabled:
            return None
        
        text = mention_data.get("text", "").lower()
        user = mention_data.get("user", {})
        username = user.get("username", "用户")
        
        if "你好" in text or "hello" in text or "hi" in text:
            logger.info(f"示例插件处理问候消息: @{username}")
            return {
                "handled": True,
                "plugin_name": "ExamplePlugin",
                "response": f"@{username} 你好！我是示例插件，很高兴见到你！"
            }
        
        return None
    
    async def on_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.greeting_enabled:
            return None
        
        text = message_data.get("text", "").lower()
        
        if "插件" in text and "测试" in text:
            logger.info("示例插件处理测试消息")
            return {
                "handled": True,
                "plugin_name": "ExamplePlugin",
                "response": "插件系统工作正常！这是来自示例插件的回复。"
            }
        
        return None
    
    async def on_auto_post(self) -> Optional[Dict[str, Any]]:
        if not self.auto_post_enabled:
            return None
        
        import random
        
        posts = [
            "🤖 插件系统正在运行中...",
            "💡 今天又是充满可能性的一天！",
            "🌟 示例插件向大家问好！",
            "🔧 插件化架构让扩展变得简单！"
        ]
        
        content = random.choice(posts)
        
        logger.info("示例插件生成自动发帖内容")
        return {
            "content": content,
            "visibility": "public",
            "plugin_name": "ExamplePlugin"
        }
    
    async def on_startup(self) -> None:
        logger.info("示例插件启动 hook 被调用")
    
    async def on_shutdown(self) -> None:
        logger.info("示例插件关闭 hook 被调用")