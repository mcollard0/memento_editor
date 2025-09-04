#!/usr/bin/env python3
"""
Autosave timer module for the Memento text editor.
Provides idle detection and automatic saving when user stops typing.
"""

import threading
from typing import Callable, Optional
from constants import IDLE_THRESHOLD_SECONDS


class IdleSaver:
    """Manages automatic saving based on user inactivity and character count."""
    
    def __init__(self, save_callback: Callable[[], None], idle_seconds: float = IDLE_THRESHOLD_SECONDS, char_threshold: int = 50):
        """
        Initialize the IdleSaver.
        
        Args:
            save_callback: Function to call when saving should occur
            idle_seconds: Number of seconds to wait after last activity before saving
            char_threshold: Number of characters typed since last save to trigger save
        """
        self.save_callback = save_callback
        self.idle_seconds = idle_seconds
        self.char_threshold = char_threshold
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._active = False
        self._char_count_since_save = 0
    
    def start(self):
        """Start the idle saver."""
        with self._lock:
            self._active = True
    
    def stop(self):
        """Stop the idle saver and cancel any pending save."""
        with self._lock:
            self._active = False
            if self._timer:
                self._timer.cancel()
                self._timer = None
    
    def update(self, char_added: bool = False):
        """Call this method whenever the user makes a change (types, etc.).
        
        Args:
            char_added: True if a character was added (for character counting)
        """
        with self._lock:
            if not self._active:
                return
            
            # Track character count
            if char_added:
                self._char_count_since_save += 1
                
                # Check if we should save due to character count
                if self._char_count_since_save >= self.char_threshold:
                    self._trigger_save("character count")
                    return
            
            # Cancel any existing timer
            if self._timer:
                self._timer.cancel()
            
            # Start a new timer
            self._timer = threading.Timer(self.idle_seconds, self._on_idle_timeout)
            self._timer.start()
    
    def _on_idle_timeout(self):
        """Called when the idle timeout expires."""
        self._trigger_save("idle timeout")
    
    def _trigger_save(self, reason: str):
        """Trigger a save operation and reset counters."""
        with self._lock:
            if self._active:
                try:
                    self.save_callback()
                    # Reset character count after successful save
                    self._char_count_since_save = 0
                except Exception as e:
                    # Don't let save errors crash the timer
                    print(f"Error during autosave ({reason}): {e}")
                finally:
                    self._timer = None
    
    def force_save(self):
        """Force an immediate save and cancel any pending timer."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            
            if self._active:
                try:
                    self.save_callback()
                    # Reset character count after successful save
                    self._char_count_since_save = 0
                except Exception as e:
                    print(f"Error during forced save: {e}")


class SaveStatus:
    """Tracks and formats save status for display."""
    
    def __init__(self):
        self.is_saving = False
        self.last_saved_time = None
        self.has_unsaved_changes = False
    
    def mark_saving(self):
        """Mark that a save operation is in progress."""
        self.is_saving = True
    
    def mark_saved(self):
        """Mark that save operation completed successfully."""
        import time
        self.is_saving = False
        self.last_saved_time = time.time()
        self.has_unsaved_changes = False
    
    def mark_changed(self):
        """Mark that there are unsaved changes."""
        self.has_unsaved_changes = True
    
    def get_status_text(self) -> str:
        """Get formatted status text for display."""
        if self.is_saving:
            return "Saving..."
        
        if not self.has_unsaved_changes and self.last_saved_time:
            import time
            from datetime import datetime
            last_saved = datetime.fromtimestamp(self.last_saved_time)
            return f"Saved at {last_saved.strftime('%H:%M:%S')}"
        
        if self.has_unsaved_changes:
            return "Unsaved changes"
        
        return "Ready"
