#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import importlib
import importlib.util
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from .plugin_base import PluginBase
from .config import Config

class PluginManager:
    
    def __init__(self, config: Config, plugins_dir: str = "plugins", persistence=None):
        self.config = config
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.persistence = persistence
        
    async def load_plugins(self) -> None:
        if not self.plugins_dir.exists():
            logger.info(f"插件目录不存在: {self.plugins_dir}")
            return
        for plugin_dir in self.plugins_dir.iterdir():
            if (plugin_dir.is_dir() and
                not plugin_dir.name.startswith('.') and
                plugin_dir.name not in {'__pycache__', 'example'}):
                plugin_config = self._load_plugin_config(plugin_dir)
                await self._load_plugin(plugin_dir, plugin_config)
        await self._initialize_plugins()
        enabled_count = sum(1 for plugin in self.plugins.values() if plugin.enabled)
        logger.info(f"已发现 {len(self.plugins)} 个插件，{enabled_count} 个已启用")
    
    def _load_plugin_config(self, plugin_dir: Path) -> Dict[str, Any]:
        config_file = plugin_dir / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                return config
            except Exception as e:
                logger.error(f"加载插件 {plugin_dir.name} 配置文件时出错: {e}")
                return {}
        else:
            return {"enabled": False}
    
    async def _load_plugin(self, plugin_dir: Path, plugin_config: Dict[str, Any]) -> None:
        try:
            plugin_file = plugin_dir / f"{plugin_dir.name}.py"
            if not plugin_file.exists():
                logger.warning(f"插件目录 {plugin_dir.name} 中未找到 {plugin_dir.name}.py 文件")
                return
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_dir.name}.plugin",
                plugin_file
            )
            if spec is None or spec.loader is None:
                logger.warning(f"无法加载插件规范: {plugin_dir.name}")
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginBase) and
                    attr is not PluginBase):
                    plugin_class = attr
                    break
            if plugin_class is None:
                logger.warning(f"插件 {plugin_dir.name} 中未找到有效的插件类")
                return
            import inspect
            sig = inspect.signature(plugin_class.__init__)
            params = list(sig.parameters.keys())[1:]
            if 'name' in params and 'persistence_manager' in params:
                plugin_instance = plugin_class(plugin_dir.name, plugin_config, self.persistence)
            elif 'name' in params:
                plugin_instance = plugin_class(plugin_dir.name, plugin_config)
            else:
                plugin_instance = plugin_class(plugin_config)
                if hasattr(plugin_instance, 'set_persistence') and self.persistence:
                    plugin_instance.set_persistence(self.persistence)
            self.plugins[plugin_dir.name] = plugin_instance
            self.plugin_configs[plugin_dir.name] = plugin_config
            status = "启用" if plugin_instance.enabled else "禁用"
            logger.debug(f"已发现插件: {plugin_dir.name} (状态: {status})")
        except Exception as e:
            logger.warning(f"加载插件 {plugin_dir.name} 时出错: {e}")
    
    async def _initialize_plugins(self) -> None:
        sorted_plugins = sorted(
            self.plugins.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        for plugin_name, plugin in sorted_plugins:
            try:
                if plugin.enabled:
                    success = await plugin.initialize()
                    if not success:
                        logger.warning(f"插件 {plugin_name} 初始化失败")
                        plugin.set_enabled(False)
                    else:
                        logger.debug(f"插件 {plugin_name} 初始化成功")
            except Exception as e:
                logger.error(f"初始化插件 {plugin_name} 时出错: {e}")
                plugin.set_enabled(False)
    
    async def call_plugin_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        results = []
        sorted_plugins = sorted(
            [(name, plugin) for name, plugin in self.plugins.items() if plugin.enabled],
            key=lambda x: x[1].priority,
            reverse=True
        )
        for plugin_name, plugin in sorted_plugins:
            try:
                if hasattr(plugin, hook_name):
                    method = getattr(plugin, hook_name)
                    result = await method(*args, **kwargs)
                    if result is not None:
                        results.append(result)
            except Exception as e:
                logger.error(f"调用插件 {plugin_name} 的 {hook_name} hook 时出错: {e}")
        return results
    
    async def on_mention(self, mention_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.call_plugin_hook("on_mention", mention_data)
    
    async def on_message(self, message_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.call_plugin_hook("on_message", message_data)
    
    async def on_auto_post(self) -> List[Dict[str, Any]]:
        return await self.call_plugin_hook("on_auto_post")
    
    async def on_startup(self) -> None:
        await self.call_plugin_hook("on_startup")
    
    async def on_shutdown(self) -> None:
        await self.call_plugin_hook("on_shutdown")
    
    async def cleanup_plugins(self) -> None:
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    await plugin.cleanup()
                    logger.debug(f"插件 {plugin_name} 清理完成")
                except Exception as e:
                    logger.error(f"清理插件 {plugin_name} 时出错: {e}")
    
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        return [plugin.get_info() for plugin in self.plugins.values()]
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        return self.plugins.get(name)
    
    def enable_plugin(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        if plugin:
            plugin.set_enabled(True)
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        if plugin:
            plugin.set_enabled(False)
            return True
        return False