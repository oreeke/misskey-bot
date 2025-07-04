#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Misskey Bot 主程序

这个模块是Misskey机器人的入口点，负责初始化和启动机器人。
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from .config import Config
from .bot import MisskeyBot
from .utils import log_system_info, monitor_memory_usage


# 全局变量，用于存储机器人实例
bot = None
# 全局变量，用于存储任务列表
tasks = []


async def shutdown(signal_type=None):
    """优雅关闭机器人
    
    Args:
        signal_type: 触发关闭的信号类型
    """
    global bot, tasks
    
    if signal_type:
        logger.info(f"收到信号 {signal_type.name}，正在关闭机器人...")
    else:
        logger.info("正在关闭机器人...")
    
    # 取消所有任务
    for task in tasks:
        if not task.done():
            task.cancel()
    
    # 等待任务完成
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    tasks = []
    
    # 停止机器人
    if bot:
        await bot.stop()
    
    logger.info("机器人已完全关闭")


async def main():
    """主函数，初始化并启动机器人"""
    global bot, tasks
    
    # 加载环境变量
    load_dotenv()
    
    # 加载配置以获取日志设置
    config = Config()
    await config.load()
    
    # 设置日志
    log_path = Path(config.get("logging.path", "logs"))
    log_path.mkdir(exist_ok=True)
    log_level = config.get("logging.level", "INFO")
    logger.add(
        log_path / "misskey_bot_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=log_level,
    )
    
    # 记录系统信息
    await log_system_info()
    
    logger.info("正在启动Misskey机器人...")
    
    try:
        # 创建并启动机器人
        bot = MisskeyBot(config)
        await bot.start()
        
        # 启动内存监控
        memory_task = asyncio.create_task(monitor_memory_usage())
        tasks.append(memory_task)
        
        # 设置信号处理
        loop = asyncio.get_running_loop()
        
        # 在Windows上，信号处理方式不同
        if sys.platform != 'win32':
            signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
            for sig in signals:
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(shutdown(s))
                )
        # Windows上的信号处理在外层的KeyboardInterrupt中处理
        
        # 保持运行直到收到信号
        while True:
            await asyncio.sleep(3600)  # 每小时检查一次
            
    except asyncio.CancelledError:
        # 任务被取消，正常退出
        pass
    except (OSError, IOError) as e:
        logger.error(f"文件或网络错误导致机器人启动失败: {e}")
        if bot:
            await bot.stop()
        raise
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"配置或数据错误导致机器人启动失败: {e}")
        if bot:
            await bot.stop()
        raise
    except Exception as e:
        import traceback
        logger.error(f"未知错误导致机器人启动失败: {e}")
        logger.error(f"完整错误信息: {traceback.format_exc()}")
        if bot:
            try:
                await bot.stop()
            except Exception as stop_error:
                logger.error(f"停止机器人时出错: {stop_error}")
        raise
    finally:
        # 确保资源清理
        if bot and hasattr(bot, '_cleanup_needed') and bot._cleanup_needed:
            try:
                await bot.stop()
            except Exception as cleanup_error:
                logger.error(f"最终清理时出错: {cleanup_error}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 在Windows上，KeyboardInterrupt可能会绕过信号处理器
        logger.info("收到键盘中断信号")
        try:
            asyncio.run(shutdown())
        except Exception as e:
            logger.error(f"关闭时出错: {e}")
        logger.info("机器人已停止")
    except (OSError, IOError) as e:
        logger.exception(f"文件或网络错误: {e}")
        try:
            asyncio.run(shutdown())
        except Exception as shutdown_error:
            logger.error(f"关闭时出错: {shutdown_error}")
    except (ValueError, TypeError, KeyError) as e:
        logger.exception(f"配置或数据错误: {e}")
        try:
            asyncio.run(shutdown())
        except Exception as shutdown_error:
            logger.error(f"关闭时出错: {shutdown_error}")
    except Exception as e:
        logger.exception(f"机器人运行时出现未知错误: {e}")
        try:
            asyncio.run(shutdown())
        except Exception as shutdown_error:
            logger.error(f"关闭时出错: {shutdown_error}")
    finally:
        # 确保在所有情况下都尝试清理资源
        if bot is not None:
            try:
                asyncio.run(bot.stop())
            except Exception as e:
                logger.error(f"最终清理时出错: {e}")