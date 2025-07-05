#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import tempfile
import os
from pathlib import Path
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.persistence import PersistenceManager


@pytest.mark.asyncio
async def test_persistence_manager():
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        
        persistence = PersistenceManager(db_path)
        assert persistence is not None
        
        
        assert Path(db_path).exists()
        
        test_mention_id = "test_mention_123"
        test_message_id = "test_message_456"
        
        
        await persistence.mark_mention_processed(test_mention_id)
        await persistence.mark_message_processed(test_message_id)
        
        
        is_mention_processed = await persistence.is_mention_processed(test_mention_id)
        is_message_processed = await persistence.is_message_processed(test_message_id)
        
        assert is_mention_processed is True
        assert is_message_processed is True
        
        
        is_new_mention_processed = await persistence.is_mention_processed("new_mention")
        is_new_message_processed = await persistence.is_message_processed("new_message")
        
        assert is_new_mention_processed is False
        assert is_new_message_processed is False
        
        
        stats = await persistence.get_stats()
        assert isinstance(stats, dict)
        assert 'mentions_count' in stats
        assert 'messages_count' in stats
        assert stats['mentions_count'] >= 1
        assert stats['messages_count'] >= 1
        
        
        await persistence.cleanup_old_records(0)
        
        
        await persistence.close()
        
    finally:
        
        if os.path.exists(db_path):
            os.unlink(db_path)