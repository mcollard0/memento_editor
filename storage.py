#!/usr/bin/env python3
"""
Storage and ring buffer management for the Memento text editor application.
Handles file persistence, version control through ring buffers, and memento metadata.
"""

import json
import pathlib
import time
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from constants import (
    MEMENTO_ROOT, CONTROL_FILE, make_dirs_if_missing, 
    get_memento_dir, get_next_memento_id, calculate_buffer_size
)


class MementoInfo:
    """Information about a memento for display in the selector."""
    def __init__(self, memento_id: int, first_line: str, last_modified: datetime):
        self.memento_id = memento_id
        self.first_line = first_line
        self.last_modified = last_modified


class FileManager:
    """Manages file storage and ring buffer for a single memento."""
    
    def __init__(self, memento_id: int):
        self.memento_id = memento_id
        self.memento_dir = get_memento_dir(memento_id)
        self.control_file = self.memento_dir / CONTROL_FILE
        
        # Control file structure
        self.current_index = 0
        self.max_buffers = 10  # Default, will be adjusted
        self.created_timestamp = time.time()
        self.last_modified = time.time()
        
        # Load existing control file if it exists
        self._load_control_file()
    
    def _load_control_file(self):
        """Load control file data if it exists."""
        if self.control_file.exists():
            try:
                with open(self.control_file, 'r') as f:
                    data = json.load(f)
                    self.current_index = data.get('current_index', 0)
                    self.max_buffers = data.get('max_buffers', 10)
                    self.created_timestamp = data.get('created_timestamp', time.time())
                    self.last_modified = data.get('last_modified', time.time())
            except (json.JSONDecodeError, FileNotFoundError):
                # If control file is corrupted, start fresh
                pass
    
    def _save_control_file(self):
        """Save control file with current state."""
        make_dirs_if_missing(self.memento_dir)
        
        data = {
            'current_index': self.current_index,
            'max_buffers': self.max_buffers,
            'created_timestamp': self.created_timestamp,
            'last_modified': self.last_modified
        }
        
        with open(self.control_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_snapshot_path(self, index: int) -> pathlib.Path:
        """Get the file path for a snapshot at the given index."""
        return self.memento_dir / f"{index}.txt"
    
    def _adjust_buffer_size(self, text_size: int):
        """Adjust buffer size based on text size, protecting current position."""
        new_buffer_size = calculate_buffer_size(text_size)
        
        if new_buffer_size == self.max_buffers:
            return  # No change needed
        
        # Don't adjust if current index is near boundaries (to avoid data loss)
        if (self.current_index < 2 or 
            self.current_index >= self.max_buffers - 2):
            return
        
        if new_buffer_size > self.max_buffers:
            # Growing buffer - just update the count
            self.max_buffers = new_buffer_size
        else:
            # Shrinking buffer - remove excess files
            for i in range(new_buffer_size, self.max_buffers):
                snapshot_path = self._get_snapshot_path(i)
                if snapshot_path.exists():
                    snapshot_path.unlink()
            self.max_buffers = new_buffer_size
    
    def write_snapshot(self, text: str):
        """Write a new snapshot to the ring buffer."""
        make_dirs_if_missing(self.memento_dir)
        
        # Adjust buffer size based on text size
        text_bytes = len(text.encode('utf-8'))
        self._adjust_buffer_size(text_bytes)
        
        # Move to next position in ring buffer
        self.current_index = (self.current_index + 1) % self.max_buffers
        
        # Write the snapshot
        snapshot_path = self._get_snapshot_path(self.current_index)
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Update timestamps and save control file
        self.last_modified = time.time()
        self._save_control_file()
    
    def load_current_snapshot(self) -> str:
        """Load the current (most recent) snapshot."""
        snapshot_path = self._get_snapshot_path(self.current_index)
        
        if not snapshot_path.exists():
            return ""
        
        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (FileNotFoundError, UnicodeDecodeError):
            return ""
    
    def load_snapshot(self, version_offset: int = 0) -> Optional[str]:
        """Load a snapshot at a specific version offset from current.
        
        Args:
            version_offset: 0 for current, -1 for previous, etc.
        """
        index = (self.current_index + version_offset) % self.max_buffers
        snapshot_path = self._get_snapshot_path(index)
        
        if not snapshot_path.exists():
            return None
        
        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (FileNotFoundError, UnicodeDecodeError):
            return None
    
    def get_first_line(self) -> str:
        """Get the first line of the current snapshot for preview."""
        content = self.load_current_snapshot()
        if not content:
            return "[Empty memento]"
        
        lines = content.split('\n')
        first_line = lines[0].strip()
        return first_line if first_line else "[Untitled]"
    
    @staticmethod
    def create_new_memento() -> 'FileManager':
        """Create a new memento and return its FileManager."""
        memento_id = get_next_memento_id()
        manager = FileManager(memento_id)
        
        # Initialize with empty content
        manager.write_snapshot("")
        return manager
    
    @staticmethod
    def load_memento(memento_id: int) -> Optional['FileManager']:
        """Load an existing memento by ID."""
        memento_dir = get_memento_dir(memento_id)
        
        if not memento_dir.exists():
            return None
        
        return FileManager(memento_id)
    
    @staticmethod
    def list_mementos() -> List[MementoInfo]:
        """List all existing mementos with metadata."""
        make_dirs_if_missing(MEMENTO_ROOT)
        mementos = []
        
        for item in MEMENTO_ROOT.iterdir():
            if item.is_dir() and item.name.isdigit():
                memento_id = int(item.name)
                manager = FileManager.load_memento(memento_id)
                
                if manager:
                    first_line = manager.get_first_line()
                    last_modified = datetime.fromtimestamp(manager.last_modified)
                    
                    mementos.append(MementoInfo(
                        memento_id=memento_id,
                        first_line=first_line,
                        last_modified=last_modified
                    ))
        
        # Sort by last modified time, most recent first
        mementos.sort(key=lambda m: m.last_modified, reverse=True)
        return mementos
