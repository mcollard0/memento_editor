#!/usr/bin/env python3
"""
Fixed version of autosave timer module for the Memento text editor.
Provides idle detection and automatic saving when user stops typing.
Fixes the deadlock issue in the original implementation.
"""

import threading
import time
from typing import Callable, Optional
from constants import IDLE_THRESHOLD_SECONDS, CHAR_COUNT_THRESHOLDS, INITIAL_CHAR_THRESHOLD


class IdleSaver:
    """Manages automatic saving based on user inactivity and character count."""
    
    def __init__(self, save_callback: Callable[[], None], idle_seconds: float = IDLE_THRESHOLD_SECONDS):
        """
        Initialize the IdleSaver with dynamic character thresholds.
        
        Args:
            save_callback: Function to call when saving should occur
            idle_seconds: Number of seconds to wait after last activity before saving
        """
        self.save_callback = save_callback
        self.idle_seconds = idle_seconds
        self.char_thresholds = CHAR_COUNT_THRESHOLDS.copy()
        self.current_threshold_index = 0
        self.char_threshold = INITIAL_CHAR_THRESHOLD
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._active = False
        self._char_count_since_save = 0
        
        # Typing pattern analysis
        self._typing_sessions = []  # List of (char_count, duration) tuples
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
        # Record typing session data
        session_data = None
        
        with self._lock:
            # Record typing session if we have data
            if self._session_start_time is not None and self._session_char_count > 0:
                session_duration = time.time() - self._session_start_time
                session_data = (self._session_char_count, session_duration)
                
                # Reset session tracking
                self._session_start_time = None
                self._session_char_count = 0
        
        # Process session data and trigger save OUTSIDE the lock
        if session_data:
            self._process_session_data(session_data)
        
        self._trigger_save("idle timeout")
    
    def _process_session_data(self, session_data):
        """Process typing session data and adjust thresholds."""
        chars, duration = session_data
        
        with self._lock:
            self._typing_sessions.append((chars, duration))
            
            # Keep only recent sessions (last 20)
            if len(self._typing_sessions) > 20:
                self._typing_sessions = self._typing_sessions[-20:]
            
            # Analyze and adjust threshold
            self._adjust_threshold()
    
    def _adjust_threshold(self):
        """Adjust character threshold based on typing patterns.
        NOTE: This method assumes the lock is already held."""
        if len(self._typing_sessions) < 3:  # Need at least 3 sessions to analyze
            return
        
        # Calculate average characters per session
        total_chars = sum(chars for chars, duration in self._typing_sessions)
        avg_chars_per_session = total_chars / len(self._typing_sessions)
        
        # Find the appropriate threshold based on average typing pattern
        new_threshold_index = 0
        for i, threshold in enumerate(self.char_thresholds):
            if avg_chars_per_session >= threshold:
                new_threshold_index = i
            else:
                break
        
        # Update threshold if it changed
        if new_threshold_index != self.current_threshold_index:
            self.current_threshold_index = new_threshold_index
            old_threshold = self.char_threshold
            self.char_threshold = self.char_thresholds[new_threshold_index]
            print(f"Auto-save threshold adjusted: {old_threshold} → {self.char_threshold} chars (avg: {avg_chars_per_session:.1f})")
    
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
                
                # If this was a character count save, record the session
                if reason == "character count" and self._session_start_time is not None:
                    session_duration = time.time() - self._session_start_time
                    if session_duration > 0:  # Valid session
                        session_data = (self._session_char_count, session_duration)
                        
                        # Process session data while holding lock
                        self._typing_sessions.append(session_data)
                        
                        # Keep only recent sessions (last 20)
                        if len(self._typing_sessions) > 20:
                            self._typing_sessions = self._typing_sessions[-20:]
                        
                        # Analyze and adjust threshold
                        self._adjust_threshold()
                    
                    # Reset session tracking
                    self._session_start_time = None
                    self._session_char_count = 0
                    
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
