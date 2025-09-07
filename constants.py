#!/usr/bin/env python3
"""
Constants and utility functions for the memento text editor application.
"""

import os
import pathlib

# Application constants
APP_NAME = "memento"
VERSION = "1.0.0"

# Directory paths
HOME = pathlib.Path.home()
MEMENTO_ROOT = HOME / ".memento"

# File names
CONTROL_FILE = "control.json"
LOG_FILE = "memento.log"

# Autosave settings
IDLE_THRESHOLD_SECONDS = 1.5  # Save after user stops typing for this long
CHAR_COUNT_THRESHOLDS = [2, 4, 8, 16, 32, 64]  # Dynamic character count thresholds
INITIAL_CHAR_THRESHOLD = 2    # Start with the smallest threshold

# Ring buffer settings
MIN_BUFFER_SIZE = 3
MAX_BUFFER_SIZE = 50
BASE_FILE_SIZE_KB = 1024  # 1MB base for buffer size calculation

def make_dirs_if_missing(path):
    """Create directory structure if it doesn't exist."""
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_memento_dir(memento_id):
    """Get the directory path for a specific memento."""
    return MEMENTO_ROOT / str(memento_id)

def get_next_memento_id():
    """Find the next available memento ID."""
    make_dirs_if_missing(MEMENTO_ROOT)
    existing_ids = []
    
    for item in MEMENTO_ROOT.iterdir():
        if item.is_dir() and item.name.isdigit():
            existing_ids.append(int(item.name))
    
    if not existing_ids:
        return 0
    
    return max(existing_ids) + 1

def calculate_buffer_size(text_size_bytes):
    """Calculate optimal ring buffer size based on text size."""
    size_kb = text_size_bytes / 1024
    # More savepoints for smaller files, fewer for larger files
    buffer_size = max(MIN_BUFFER_SIZE, min(MAX_BUFFER_SIZE, int(BASE_FILE_SIZE_KB / max(size_kb, 1))))
    return buffer_size
