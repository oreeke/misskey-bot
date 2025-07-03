#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Misskey Bot 运行脚本

这个脚本是一个简单的入口点，用于在本地运行Misskey机器人。
"""

import asyncio
import os
import sys
from pathlib import Path

# 确保src目录在Python路径中
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main, shutdown


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 在Windows上，KeyboardInterrupt可能会绕过信号处理器
        if sys.platform == 'win32':
            try:
                asyncio.run(shutdown())
            except (OSError, IOError) as e:
                print(f"关闭时文件或网络错误: {e}")
            except Exception as e:
                print(f"关闭时出现未知错误: {e}")
        print("\n机器人已停止")
    except (OSError, IOError) as e:
        print(f"\n文件或网络错误: {e}")
        # 尝试优雅关闭
        try:
            asyncio.run(shutdown())
        except Exception as shutdown_error:
            print(f"关闭时出现未知错误: {shutdown_error}")
    except (ValueError, TypeError, KeyError) as e:
        print(f"\n配置或数据错误: {e}")
        # 尝试优雅关闭
        try:
            asyncio.run(shutdown())
        except Exception as shutdown_error:
            print(f"关闭时出现未知错误: {shutdown_error}")
    except Exception as e:
        print(f"\n运行时出现未知错误: {e}")
        # 尝试优雅关闭
        try:
            asyncio.run(shutdown())
        except Exception as shutdown_error:
            print(f"关闭时出现未知错误: {shutdown_error}")