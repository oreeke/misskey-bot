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

bot: Optional[MisskeyBot] = None
tasks: List[asyncio.Task] = []
_shutdown_called: bool = False
shutdown_event: Optional[asyncio.Event] = None

async def shutdown(signal_type=None) -> None:
    global bot, tasks, _shutdown_called, shutdown_event
    if _shutdown_called:
        return
    _shutdown_called = True
    
    logger.info("关闭机器人...")
    await _cleanup_tasks()
    await _stop_bot()
    if shutdown_event and not shutdown_event.is_set():
        shutdown_event.set()
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
    global bot, tasks, shutdown_event
    shutdown_event = asyncio.Event()
    
    load_dotenv()
    config = Config()
    await config.load()
    log_path = Path(config.get("logging.path"))
    log_path.mkdir(exist_ok=True)
    log_level = config.get("logging.level")
    logger.add(
        log_path / "misskey_ai.log",
        level=log_level,
    )
    await log_system_info()
    logger.info("启动机器人...")
    try:
        bot = MisskeyBot(config)
        await bot.start()
        await _setup_monitoring_and_signals()
        await shutdown_event.wait()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"启动过程中发生错误: {e}")
        raise
    finally:
        await shutdown()
        logger.info("再见~")

def _signal_handler(sig):
    global shutdown_event
    logger.info(f"收到信号 {sig.name}，准备关闭...")
    if shutdown_event and not shutdown_event.is_set():
        shutdown_event.set()

async def _setup_monitoring_and_signals() -> None:
    global tasks
    memory_task = asyncio.create_task(monitor_memory_usage())
    tasks.append(memory_task)
    
    loop = asyncio.get_running_loop()
    if sys.platform != 'win32':
        signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
        for sig in signals:
            loop.add_signal_handler(sig, _signal_handler, sig)
    else:
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda s, f: _signal_handler(signal.Signals(s)))

if __name__ == "__main__":
    asyncio.run(main())