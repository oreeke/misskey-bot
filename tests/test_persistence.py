#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试持久化功能

这个脚本用于验证机器人的消息ID持久化功能是否正常工作。"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path
import pytest

# 确保src目录在Python路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.persistence import PersistenceManager


@pytest.mark.asyncio
async def test_persistence_manager():
    """测试SQLite持久化功能"""
    # 使用临时文件避免污染项目目录
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 初始化持久化管理器
        persistence = PersistenceManager(db_path)
        assert persistence is not None
        
        # 检查数据库文件是否创建
        assert Path(db_path).exists()
        
        test_mention_id = "test_mention_123"
        test_message_id = "test_message_456"
        
        # 测试标记功能
        await persistence.mark_mention_processed(test_mention_id)
        await persistence.mark_message_processed(test_message_id)
        
        # 测试查询功能
        is_mention_processed = await persistence.is_mention_processed(test_mention_id)
        is_message_processed = await persistence.is_message_processed(test_message_id)
        
        assert is_mention_processed is True
        assert is_message_processed is True
        
        # 测试未处理的ID
        is_new_mention_processed = await persistence.is_mention_processed("new_mention")
        is_new_message_processed = await persistence.is_message_processed("new_message")
        
        assert is_new_mention_processed is False
        assert is_new_message_processed is False
        
        # 测试统计功能
        stats = await persistence.get_stats()
        assert isinstance(stats, dict)
        assert 'mentions_count' in stats
        assert 'messages_count' in stats
        assert stats['mentions_count'] >= 1
        assert stats['messages_count'] >= 1
        
        # 测试清理功能
        await persistence.cleanup_old_records(0)
        
        # 关闭连接
        await persistence.close()
        
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)


# 可以通过 pytest 命令运行这个测试:
# pytest tests/test_persistence.py -v
# pytest tests/test_persistence.py::test_persistence_manager -v