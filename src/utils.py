#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import platform
import random
from functools import wraps
from typing import Dict, Any, Callable, Awaitable, TypeVar

import psutil
from loguru import logger

T = TypeVar('T')

def retry_async(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, 
                backoff_factor: float = 2.0, retryable_exceptions: tuple = None):
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if retryable_exceptions and not isinstance(e, retryable_exceptions):
                        raise
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        jitter = delay * 0.25 * (2 * random.random() - 1)
                        await asyncio.sleep(max(0.1, delay + jitter))
            raise last_error
        return wrapper
    return decorator

def calculate_retry_delay(attempt: int, base_delay: float = 1.0, 
                         backoff_factor: float = 2.0, max_delay: float = 60.0) -> float:
    delay = base_delay * (backoff_factor ** attempt)
    delay = min(delay, max_delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0.1, delay + jitter)

async def check_api_health(check_func: Callable[[], Awaitable[bool]], name: str) -> bool:
    try:
        is_healthy = await check_func()
        if is_healthy:
            logger.debug(f"{name} API 连接正常")
        else:
            logger.warning(f"{name} API 连接失败")
        return is_healthy
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.warning(f"{name} API 网络连接错误: {e}")
        return False
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"{name} API 数据处理错误: {e}")
        return False
    except Exception as e:
        logger.error(f"{name} API 健康检查出现未知错误: {e}")
        return False

def get_memory_usage() -> Dict[str, Any]:
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    rss_mb = memory_info.rss / (1024 * 1024)
    vms_mb = memory_info.vms / (1024 * 1024)
    return {
        "rss_mb": round(rss_mb, 2),
        "vms_mb": round(vms_mb, 2),
        "percent": process.memory_percent(),
    }

async def monitor_memory_usage() -> None:
    interval_seconds = 3600
    threshold_mb = 1024
    while True:
        try:
            memory_usage = get_memory_usage()
            logger.debug(f"内存使用: {memory_usage['rss_mb']} MB (物理), {memory_usage['vms_mb']} MB (虚拟), {memory_usage['percent']}%")
            if memory_usage["rss_mb"] > threshold_mb:
                logger.warning(f"内存使用过高: {memory_usage['rss_mb']} MB")
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"内存监控出现错误: {e}")
            await asyncio.sleep(interval_seconds)

def get_system_info() -> Dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "process_id": os.getpid(),
    }

async def log_system_info() -> None:
    system_info = get_system_info()
    logger.info(f"运行环境: Python {system_info['python_version']}, {system_info['platform']}, CPU 核心: {system_info['cpu_count']}, 内存: {system_info['memory_total_gb']} GB")

def health_check() -> bool:
    try:
        memory_usage = get_memory_usage()
        if memory_usage["percent"] > 90:
            logger.warning(f"内存使用过高: {memory_usage['percent']}%")
            return False
        current_process = psutil.Process(os.getpid())
        if not current_process.is_running():
            return False
        return True
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return False
