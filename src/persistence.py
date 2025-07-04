#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
持久化管理模块

使用SQLite数据库替代JSON文件，提供更高效的消息ID存储和查询功能。
"""

import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from contextlib import asynccontextmanager

from loguru import logger


class PersistenceManager:
    """持久化管理器，使用SQLite存储已处理的消息ID"""
    
    def __init__(self, db_path: str = "data/bot_persistence.db"):
        """初始化持久化管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._connection = None
        self._lock = asyncio.Lock()
        
        # 同步初始化数据库连接
        self._init_sync_connection()
        
    def _init_sync_connection(self) -> None:
        """同步初始化数据库连接"""
        self._connection = sqlite3.connect(
            self.db_path, 
            check_same_thread=False,
            timeout=30.0
        )
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._connection.execute("PRAGMA cache_size=10000")
        
        # 创建表结构
        self._create_tables_sync()
        logger.info(f"持久化管理器已初始化，数据库: {self.db_path}")
        
    def _create_tables_sync(self) -> None:
        """同步创建数据库表结构"""
        cursor = self._connection.cursor()
        
        # 已处理的提及表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT UNIQUE NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                username TEXT
            )
        """)
        
        # 已处理的消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                chat_type TEXT
            )
        """)
        
        # 创建索引以提高查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_note_id 
            ON processed_mentions(note_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_processed_at 
            ON processed_mentions(processed_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_message_id 
            ON processed_messages(message_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_processed_at 
            ON processed_messages(processed_at)
        """)
        
        self._connection.commit()
        
    async def initialize(self) -> None:
        """初始化数据库连接和表结构"""
        async with self._lock:
            self._connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute("PRAGMA cache_size=10000")
            
            # 创建表结构
            await self._create_tables()
            logger.info(f"持久化管理器已初始化，数据库: {self.db_path}")
    
    async def _create_tables(self) -> None:
        """创建数据库表结构"""
        cursor = self._connection.cursor()
        
        # 已处理的提及表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT UNIQUE NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                username TEXT
            )
        """)
        
        # 已处理的消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                chat_type TEXT
            )
        """)
        
        # 创建索引以提高查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_note_id 
            ON processed_mentions(note_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_processed_at 
            ON processed_mentions(processed_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_message_id 
            ON processed_messages(message_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_processed_at 
            ON processed_messages(processed_at)
        """)
        
        self._connection.commit()
    
    async def is_mention_processed(self, note_id: str) -> bool:
        """检查提及是否已处理
        
        Args:
            note_id: 提及的帖子ID
            
        Returns:
            bool: 是否已处理
        """
        async with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_mentions WHERE note_id = ? LIMIT 1",
                (note_id,)
            )
            return cursor.fetchone() is not None
    
    async def is_message_processed(self, message_id: str) -> bool:
        """检查消息是否已处理
        
        Args:
            message_id: 消息ID
            
        Returns:
            bool: 是否已处理
        """
        async with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ? LIMIT 1",
                (message_id,)
            )
            return cursor.fetchone() is not None
    
    async def mark_mention_processed(
        self, 
        note_id: str, 
        user_id: Optional[str] = None, 
        username: Optional[str] = None
    ) -> None:
        """标记提及为已处理
        
        Args:
            note_id: 提及的帖子ID
            user_id: 用户ID
            username: 用户名
        """
        async with self._lock:
            cursor = self._connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO processed_mentions 
                    (note_id, user_id, username) VALUES (?, ?, ?)
                    """,
                    (note_id, user_id, username)
                )
                self._connection.commit()
            except sqlite3.Error as e:
                logger.error(f"标记提及已处理时出错: {e}")
                self._connection.rollback()
    
    async def mark_message_processed(
        self, 
        message_id: str, 
        user_id: Optional[str] = None, 
        chat_type: Optional[str] = None
    ) -> None:
        """标记消息为已处理
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            chat_type: 聊天类型
        """
        async with self._lock:
            cursor = self._connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO processed_messages 
                    (message_id, user_id, chat_type) VALUES (?, ?, ?)
                    """,
                    (message_id, user_id, chat_type)
                )
                self._connection.commit()
            except sqlite3.Error as e:
                logger.error(f"标记消息已处理时出错: {e}")
                self._connection.rollback()
    
    async def get_processed_mentions_count(self) -> int:
        """获取已处理提及数量"""
        async with self._lock:
            cursor = self._connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM processed_mentions")
            return cursor.fetchone()[0]
    
    async def get_processed_messages_count(self) -> int:
        """获取已处理消息数量"""
        async with self._lock:
            cursor = self._connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM processed_messages")
            return cursor.fetchone()[0]
    
    async def cleanup_old_records(self, days: int = 7) -> int:
        """清理过期记录
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的记录数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with self._lock:
            cursor = self._connection.cursor()
            
            # 清理过期的提及记录
            cursor.execute(
                "DELETE FROM processed_mentions WHERE processed_at < ?",
                (cutoff_date,)
            )
            mentions_deleted = cursor.rowcount
            
            # 清理过期的消息记录
            cursor.execute(
                "DELETE FROM processed_messages WHERE processed_at < ?",
                (cutoff_date,)
            )
            messages_deleted = cursor.rowcount
            
            self._connection.commit()
            
            total_deleted = mentions_deleted + messages_deleted
            if total_deleted > 0:
                logger.info(f"已清理 {total_deleted} 条过期记录 (提及: {mentions_deleted}, 消息: {messages_deleted})")
            
            return total_deleted
    
    async def get_recent_mentions(self, limit: int = 100) -> List[dict]:
        """获取最近的已处理提及
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[dict]: 最近的提及记录
        """
        async with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT note_id, processed_at, user_id, username 
                FROM processed_mentions 
                ORDER BY processed_at DESC 
                LIMIT ?
                """,
                (limit,)
            )
            
            return [
                {
                    'note_id': row[0],
                    'processed_at': row[1],
                    'user_id': row[2],
                    'username': row[3]
                }
                for row in cursor.fetchall()
            ]
    
    async def get_recent_messages(self, limit: int = 100) -> List[dict]:
        """获取最近的已处理消息
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[dict]: 最近的消息记录
        """
        async with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT message_id, processed_at, user_id, chat_type 
                FROM processed_messages 
                ORDER BY processed_at DESC 
                LIMIT ?
                """,
                (limit,)
            )
            
            return [
                {
                    'message_id': row[0],
                    'processed_at': row[1],
                    'user_id': row[2],
                    'chat_type': row[3]
                }
                for row in cursor.fetchall()
            ]
    
    async def get_statistics(self) -> dict:
        """获取统计信息
        
        Returns:
            dict: 统计信息
        """
        async with self._lock:
            cursor = self._connection.cursor()
            
            # 总数统计
            cursor.execute("SELECT COUNT(*) FROM processed_mentions")
            total_mentions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM processed_messages")
            total_messages = cursor.fetchone()[0]
            
            # 今日统计
            today = datetime.now().date()
            cursor.execute(
                "SELECT COUNT(*) FROM processed_mentions WHERE DATE(processed_at) = ?",
                (today,)
            )
            today_mentions = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM processed_messages WHERE DATE(processed_at) = ?",
                (today,)
            )
            today_messages = cursor.fetchone()[0]
            
            # 数据库大小
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return {
                'total_mentions': total_mentions,
                'total_messages': total_messages,
                'today_mentions': today_mentions,
                'today_messages': today_messages,
                'db_size_bytes': db_size,
                'db_size_mb': round(db_size / 1024 / 1024, 2)
            }
    
    async def get_stats(self) -> dict:
        """获取统计信息（get_statistics的别名）
        
        Returns:
            dict: 统计信息，包含mentions_count和messages_count字段
        """
        stats = await self.get_statistics()
        return {
            'mentions_count': stats['total_mentions'],
            'messages_count': stats['total_messages'],
            **stats
        }
    
    async def vacuum_database(self) -> None:
        """优化数据库，回收空间"""
        async with self._lock:
            try:
                self._connection.execute("VACUUM")
                logger.info("数据库优化完成")
            except sqlite3.Error as e:
                logger.error(f"数据库优化失败: {e}")
    
    async def vacuum(self) -> None:
        """优化数据库（vacuum_database的别名）"""
        await self.vacuum_database()
    
    async def close(self) -> None:
        """关闭数据库连接"""
        async with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info("持久化管理器已关闭")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        return False