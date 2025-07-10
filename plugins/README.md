# 插件开发指南

## 目录结构

```
plugins/
└── your_plugin/
    ├── __init__.py
    ├── your_plugin.py
    └── config.yaml
```

## 基础模板

```python
from typing import Dict, Any, Optional
from src.plugin_base import PluginBase

class YourPlugin(PluginBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    async def initialize(self) -> bool:
        return True
    
    async def cleanup(self) -> None:
        pass
    
    async def on_mention(self, mention_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text = mention_data.get("text", "")
        if "关键词" in text:
            return {
                "handled": True,
                "response": "回复内容"
            }
        return None
    
    async def on_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None
    
    async def on_auto_post(self) -> Optional[Dict[str, Any]]:
        return None
    
    async def on_startup(self) -> None:
        pass
    
    async def on_shutdown(self) -> None:
        pass
```

## 配置文件

```yaml
# config.yaml
enabled: false
priority: 0
your_setting: "value"
```

## hook 方法

- `on_mention(mention_data)` - 处理提及
- `on_message(message_data)` - 处理私信
- `on_auto_post()` - 自动发帖
- `on_startup()` - 启动时
- `on_shutdown()` - 关闭时