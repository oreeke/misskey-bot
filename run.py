#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from src.main import main, shutdown

async def handle_shutdown(error_msg: str = None) -> None:
    if error_msg:
        print(f"\n{error_msg}")
    try:
        await shutdown()
    except Exception as e:
        print(f"关闭时出错: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if sys.platform == 'win32':
            asyncio.run(handle_shutdown())
        print("\n机器人已停止")
    except (OSError, IOError) as e:
        asyncio.run(handle_shutdown(f"文件或网络错误: {e}"))
    except (ValueError, TypeError, KeyError) as e:
        asyncio.run(handle_shutdown(f"配置或数据错误: {e}"))
    except Exception as e:
        asyncio.run(handle_shutdown(f"运行时错误: {e}"))