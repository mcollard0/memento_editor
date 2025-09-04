#!/usr/bin/env python3
"""
Fixed version of autosave timer module for the Memento text editor.
Provides idle detection and automatic saving when user stops typing.
Fixes the deadlock issue in the original implementation.
"""

import threading
import time
from typing import Callable, Optional
from constants import IDLE_THRESHOLD_SECONDS


class IdleSaver:
    """Manages automatic saving based on user inactivity and character count."""
    
    def __init__(self, save_callback: Callable[[], None], idle_seconds: float = IDLE_THRESHOLD_SECONDS):
        """
        Initialize the IdleSaver with progressive character thresholds.
        
        Args:
            save_callback: Function to call when saving should occur
            idle_seconds: Number of seconds to wait after last activity before saving
        """
        self.save_callback = save_callback
        self.idle_seconds = idle_seconds
        
        # Progressive threshold system: starts at 2, increases by 2 each save up to 20
        self.char_threshold = 2  # Start at 2 characters
        self.max_threshold = 20  # Maximum threshold
        self.threshold_increment = 2  # Increase by 2 each time
        
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._active = False
        self._char_count_since_save = 0
        
        # Session tracking for display purposes
        self._session_start_time = None
        self._session_char_count = 0
    
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
        should_save_now = False
        
        with self._lock:
            if not self._active:
                return
            
            # Track typing session start
            if char_added and self._session_start_time is None:
                self._session_start_time = time.time()
                self._session_char_count = 0
            
            # Track character count
            if char_added:
                self._char_count_since_save += 1
                self._session_char_count += 1
                
                # Check if we should save due to character count
                if self._char_count_since_save >= self.char_threshold:
                    should_save_now = True
            
            # Cancel any existing timer
            if self._timer:
                self._timer.cancel()
            
            # Only start a new timer if we're not saving immediately
            if not should_save_now:
                self._timer = threading.Timer(self.idle_seconds, self._on_idle_timeout)
                self._timer.start()
        
        # IMPORTANT: Trigger save OUTSIDE the lock to avoid deadlock
        if should_save_now:
            self._trigger_save("character count")
    
    def _on_idle_timeout(self):
        """Called when the idle timeout expires."""
        # Reset session tracking
        with self._lock:
            if self._session_start_time is not None:
                self._session_start_time = None
                self._session_char_count = 0
        
        self._trigger_save("idle timeout")
    
    def _increase_threshold(self):
        """Progressively increase the character threshold after each save."""
        with self._lock:
            if self.char_threshold < self.max_threshold:
                old_threshold = self.char_threshold
                self.char_threshold = min(self.char_threshold + self.threshold_increment, self.max_threshold)
                print(f"Auto-save threshold increased: {old_threshold} → {self.char_threshold} chars")
    
    def _trigger_save(self, reason: str):
        """Trigger a save operation and reset counters.
        
        IMPORTANT: This method is called WITHOUT holding the lock to avoid deadlocks.
        It only acquires the lock for minimal critical sections.
        """
        # First, check if we're still active
        with self._lock:
            if not self._active:
                return
            active_check = True
        
        if not active_check:
            return
        
        try:
            # Call the save callback (this may take time and call GUI methods)
            self.save_callback()
            
            # Reset counters after successful save
            with self._lock:
                self._char_count_since_save = 0
                
                # Reset session tracking
                if self._session_start_time is not None:
                    self._session_start_time = None
                    self._session_char_count = 0
            
            # Increase threshold progressively after successful save
            self._increase_threshold()
                    
        except Exception as e:
            # Don't let save errors crash the timer
            print(f"Error during autosave ({reason}): {e}")
        finally:
            # Clean up timer reference
            with self._lock:
                if self._timer and not self._timer.is_alive():
                    self._timer = None
    
    def force_save(self):
        """Force an immediate save and cancel any pending timer."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            
            active_check = self._active
        
        if active_check:
            try:
                self.save_callback()
                # Reset character count after successful save
                with self._lock:
                    self._char_count_since_save = 0
                # Increase threshold progressively after successful save
                self._increase_threshold()
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
