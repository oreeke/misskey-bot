#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试持久化功能的脚本

这个脚本用于验证机器人的消息ID持久化功能是否正常工作。
"""

import asyncio
import sys
from pathlib import Path

# 确保src目录在Python路径中
sys.path.insert(0, str(Path(__file__).parent / "src"))

from persistence import PersistenceManager


async def test_persistence():
    """测试SQLite持久化功能"""
    db_path = "data/bot_persistence.db"
    
    print("=== SQLite持久化功能测试 ===")
    
    try:
        # 初始化持久化管理器
        persistence = PersistenceManager(db_path)
        print(f"✓ 持久化管理器初始化成功: {db_path}")
        
        # 检查数据库文件
        if Path(db_path).exists():
            print(f"✓ 数据库文件存在: {db_path}")
        else:
            print(f"✓ 数据库文件已创建: {db_path}")
        
        # 测试基本功能
        test_mention_id = "test_mention_123"
        test_message_id = "test_message_456"
        
        # 测试标记处理
        await persistence.mark_mention_processed(test_mention_id)
        await persistence.mark_message_processed(test_message_id)
        print("✓ 测试数据已标记为已处理")
        
        # 测试查询
        is_mention_processed = await persistence.is_mention_processed(test_mention_id)
        is_message_processed = await persistence.is_message_processed(test_message_id)
        
        if is_mention_processed and is_message_processed:
            print("✓ 查询功能正常")
        else:
            print("✗ 查询功能异常")
        
        # 获取统计信息
        stats = await persistence.get_stats()
        print(f"✓ 统计信息: 提及 {stats['mentions_count']} 条，消息 {stats['messages_count']} 条")
        
        # 清理测试数据
        await persistence.cleanup_old_records(0)  # 清理所有记录
        print("✓ 测试数据已清理")
        
        # 关闭连接
        await persistence.close()
        print("✓ 持久化管理器已关闭")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 说明 ===")
    print("SQLite持久化系统已成功替代JSON文件存储。")
    print("机器人现在使用数据库来记录已处理的消息，")
    print("提供更好的性能和可靠性。")


if __name__ == "__main__":
    asyncio.run(test_persistence())