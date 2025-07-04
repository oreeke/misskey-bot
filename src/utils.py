#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实用工具模块

这个模块提供了一些实用工具函数，如健康检查和系统信息获取功能。
"""

import os
import sys
import time
import asyncio
import platform
from typing import Dict, Any, Optional, Callable, Awaitable

import psutil
from loguru import logger


async def check_api_health(check_func: Callable[[], Awaitable[bool]], name: str) -> bool:
    """检查API健康状态
    
    Args:
        check_func: 检查函数，应返回布尔值表示健康状态
        name: API名称，用于日志记录
        
    Returns:
        布尔值，表示API是否健康
    """
    try:
        is_healthy = await check_func()
        if is_healthy:
            logger.info(f"{name} API 连接正常")
        else:
            logger.error(f"{name} API 连接失败")
        return is_healthy
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.error(f"{name} API 网络连接错误: {e}")
        return False
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"{name} API 数据处理错误: {e}")
        return False
    except Exception as e:
        logger.error(f"{name} API 健康检查出现未知错误: {e}")
        return False


def get_memory_usage() -> Dict[str, Any]:
    """获取当前进程的内存使用情况
    
    Returns:
        包含内存使用信息的字典
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # 转换为MB
    rss_mb = memory_info.rss / (1024 * 1024)
    vms_mb = memory_info.vms / (1024 * 1024)
    
    return {
        "rss_mb": round(rss_mb, 2),  # 物理内存使用
        "vms_mb": round(vms_mb, 2),  # 虚拟内存使用
        "percent": process.memory_percent(),  # 内存使用百分比
    }


async def monitor_memory_usage() -> None:
    """监控内存使用情况"""
    interval_seconds = 3600  # 每小时检查一次
    threshold_mb = 1024  # 1GB 的警告阈值
    
    while True:
        try:
            memory_usage = get_memory_usage()
            
            logger.debug(f"内存使用: {memory_usage['rss_mb']}MB (物理), {memory_usage['vms_mb']}MB (虚拟), {memory_usage['percent']}%")
            
            # 只在内存使用异常高时发出警告
            if memory_usage["rss_mb"] > threshold_mb:
                logger.warning(f"内存使用过高: {memory_usage['rss_mb']}MB")
            
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"内存监控出现错误: {e}")
            await asyncio.sleep(interval_seconds)


def get_system_info() -> Dict[str, Any]:
    """获取系统信息
    
    Returns:
        包含系统信息的字典
    """
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "process_id": os.getpid(),
    }


async def log_system_info() -> None:
    """记录系统信息"""
    system_info = get_system_info()
    logger.info(f"系统信息: {system_info}")
