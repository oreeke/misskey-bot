#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional, List

from loguru import logger
from dotenv import load_dotenv

from .config import Config
from .bot import MisskeyBot
from .utils import log_system_info, monitor_memory_usage
from .constants import DEFAULT_LOG_LEVEL, DEFAULT_LOG_PATH

bot: Optional[MisskeyBot] = None
tasks: List[asyncio.Task] = []
_shutdown_called: bool = False

async def shutdown(signal_type=None) -> None:
    global bot, tasks, _shutdown_called
    if _shutdown_called:
        return
    _shutdown_called = True
    
    shutdown_msg = f"收到信号 {signal_type.name}，关闭机器人..." if signal_type else "关闭机器人..."
    logger.info(shutdown_msg)
    await _cleanup_tasks()
    await _stop_bot()
    logger.info("机器人已关闭")

async def _cleanup_tasks() -> None:
    global tasks
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    tasks = []

async def _stop_bot() -> None:
    global bot
    if bot:
        await bot.stop()

async def main() -> None:
    global bot, tasks
    load_dotenv()
    config = Config()
    await config.load()
    log_path = Path(config.get("logging.path", DEFAULT_LOG_PATH))
    log_path.mkdir(exist_ok=True)
    log_level = config.get("logging.level", DEFAULT_LOG_LEVEL)
    logger.add(
        log_path / "misskey_ai.log",
        rotation="1 day",
        level=log_level,
    )
    await log_system_info()
    logger.info("启动机器人...")
    try:
        bot = MisskeyBot(config)
        await bot.start()
        await _setup_monitoring_and_signals()
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("收到用户关闭请求，正在安全退出...")
    except Exception as e:
        logger.error(f"启动过程中发生错误: {e}")
        raise
    finally:
        await shutdown()
        logger.info("再见~")

async def _setup_monitoring_and_signals() -> None:
    global tasks
    memory_task = asyncio.create_task(monitor_memory_usage())
    tasks.append(memory_task)
    if sys.platform != 'win32':
        loop = asyncio.get_running_loop()
        signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
        for sig in signals:
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(shutdown(s))
            )

if __name__ == "__main__":
    asyncio.run(main())