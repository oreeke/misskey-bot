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


async def shutdown(signal_type=None) -> None:
    global bot, tasks
    
    if signal_type:
        logger.info(f"收到信号 {signal_type.name}，正在关闭机器人...")
    else:
        logger.info("正在关闭机器人...")
    
    for task in tasks:
        if not task.done():
            task.cancel()
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    tasks = []
    
    if bot:
        await bot.stop()
    
    logger.info("机器人已完全关闭")


async def main() -> None:
    global bot, tasks
    
    load_dotenv()
    
    config = Config()
    await config.load()
    
    log_path = Path(config.get("logging.path", "logs"))
    log_path.mkdir(exist_ok=True)
    log_level = config.get("logging.level", "INFO")
    logger.add(
        log_path / "misskey_bot_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=log_level,
    )
    
    await log_system_info()
    
    logger.info("正在启动Misskey机器人...")
    
    try:
        bot = MisskeyBot(config)
        await bot.start()
        
        memory_task = asyncio.create_task(monitor_memory_usage())
        tasks.append(memory_task)
        
        loop = asyncio.get_running_loop()
        
        if sys.platform != 'win32':
            signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
            for sig in signals:
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(shutdown(s))
                )
        
        while True:
            await asyncio.sleep(3600)
            
    except (asyncio.CancelledError, KeyboardInterrupt) as e:
        logger.info("收到用户关闭请求，正在安全关闭...")
        await shutdown()
    except Exception as e:
        logger.error(f"未知错误: {e}")
        await shutdown()
        raise
    finally:
        logger.info("主函数执行完毕")


if __name__ == "__main__":
    asyncio.run(main())