#!/usr/bin/env python3
"""
Automatic Multi-Window Text Capture System for Memento
Continuously monitors active windows and captures text content to separate mementos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import hashlib
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from text_capture import TextCapture
from storage import FileManager

logger = logging.getLogger(__name__)

@dataclass
class WindowInfo:
    """Information about a tracked window."""
    window_id: str
    window_name: str
    window_class: str
    memento_id: Optional[int] = None
    last_content_hash: Optional[str] = None
    last_activity: Optional[datetime] = None
    content_length: int = 0

class AutoCaptureSystem:
    """Automatic text capture system that monitors windows and creates mementos."""
    
    def __init__(self, gui_callback=None):
        self.text_capture = TextCapture()
        self.is_running = False
        self.capture_thread = None
        self.current_window_id = None
        self.gui_callback = gui_callback  # Callback to update GUI
        
        # Window tracking
        self.tracked_windows: Dict[str, WindowInfo] = {}
        
        # Configuration
        self.capture_interval = 5.0  # seconds
        self.idle_threshold = 10.0   # seconds of no activity before capture
        self.min_content_length = 5  # minimum chars to consider valid content
        
        # Ignore list - windows we don't want to capture from
        self.default_ignore_patterns = {
            'memento', 'terminal', 'konsole', 'gnome-terminal', 'xterm',
            'desktop', 'panel', 'taskbar', 'dock', 'launcher',
            'notification', 'popup', 'dialog', 'alert'
        }
        
        logger.info("Auto-capture system initialized")
    
    def should_ignore_window(self, window_info: dict) -> bool:
        """Check if a window should be ignored based on name/class."""
        window_name = window_info.get('window_name', '').lower()
        window_class = window_info.get('window_class', '').lower()
        
        for pattern in self.default_ignore_patterns:
            if pattern in window_name or pattern in window_class:
                return True
        
        return False
    
    def get_content_hash(self, content: str) -> str:
        """Generate a hash of content to detect changes."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def capture_window_content(self, window_id: str = None) -> Optional[str]:
        """Capture text content from the active window using comprehensive methods."""
        try:
            # Try to capture all visible text using comprehensive methods
            content = self.text_capture.capture_all_window_text(window_id)
            
            if content and len(content.strip()) >= self.min_content_length:
                return content.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error capturing window content: {e}")
            return None
    
    def get_or_create_memento_for_window(self, window_id: str, window_info: dict) -> Optional[int]:
        """Get existing memento for window or create new one."""
        
        # Check if we already have a memento for this window
        if window_id in self.tracked_windows:
            tracked_window = self.tracked_windows[window_id]
            if tracked_window.memento_id:
                return tracked_window.memento_id
        
        # Create new memento for this window
        try:
            file_manager = FileManager.create_new_memento()
            memento_id = file_manager.memento_id
            
            # Store window info
            self.tracked_windows[window_id] = WindowInfo(
                window_id=window_id,
                window_name=window_info.get('window_name', 'Unknown'),
                window_class=window_info.get('window_class', 'Unknown'),
                memento_id=memento_id,
                last_activity=datetime.now()
            )
            
            # Write initial content with window information
            initial_content = f"Auto-captured from: {window_info.get('window_name', 'Unknown Window')}\\n"
            initial_content += f"Application: {window_info.get('window_class', 'Unknown')}\\n"
            initial_content += f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
            initial_content += "=" * 50 + "\\n\\n"
            
            file_manager.write_snapshot(initial_content)
            
            logger.info(f"Created memento {memento_id} for window '{window_info.get('window_name', 'Unknown')}'")
            return memento_id
            
        except Exception as e:
            logger.error(f"Failed to create memento for window {window_id}: {e}")
            return None
    
    def update_memento_content(self, memento_id: int, content: str, window_info: WindowInfo):
        """Update memento content, replacing all text."""
        try:
            file_manager = FileManager.load_memento(memento_id)
            if not file_manager:
                logger.error(f"Could not load memento {memento_id}")
                return False
            
            # Create timestamp header
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            header = f"Auto-captured from: {window_info.window_name}\\n"
            header += f"Application: {window_info.window_class}\\n"
            header += f"Last updated: {timestamp}\\n"
            header += f"Content length: {len(content)} characters\\n"
            header += "=" * 50 + "\\n\\n"
            
            # Combine header with content
            full_content = header + content
            
            # Replace all content in memento
            file_manager.write_snapshot(full_content)
            
            # Update tracking info
            window_info.last_content_hash = self.get_content_hash(content)
            window_info.last_activity = datetime.now()
            window_info.content_length = len(content)
            
            logger.info(f"Updated memento {memento_id} with {len(content)} chars from {window_info.window_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update memento {memento_id}: {e}")
            return False
    
    def capture_loop(self):
        """Main capture loop that runs in a separate thread."""
        logger.info("Auto-capture loop started")
        last_capture_time = time.time()
        loop_count = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                loop_count += 1
                
                # Debug: Log every 10 loops to show we're active
                if loop_count % 20 == 0:
                    logger.info(f"Capture loop active - iteration {loop_count}")
                
                # Get current window info
                window_info = self.text_capture.get_active_window_info()
                logger.debug(f"Window info: {window_info}")
                
                if 'window_id' not in window_info:
                    logger.debug("No window_id in window_info")
                    time.sleep(1)
                    continue
                    
                if self.should_ignore_window(window_info):
                    logger.debug(f"Ignoring window: {window_info.get('window_name', 'Unknown')}")
                    time.sleep(1)
                    continue
                
                window_id = window_info['window_id']
                window_name = window_info.get('window_name', 'Unknown')
                
                # Check if window changed or enough time passed
                should_capture = False
                
                if window_id != self.current_window_id:
                    # Window changed - always capture
                    should_capture = True
                    self.current_window_id = window_id
                    logger.info(f"Window changed to: {window_name} (ID: {window_id})")
                elif current_time - last_capture_time >= self.capture_interval:
                    # Regular interval capture
                    should_capture = True
                    logger.info(f"Regular capture interval reached for {window_name}")
                
                # Check for idle detection
                if window_id in self.tracked_windows:
                    last_activity = self.tracked_windows[window_id].last_activity
                    if last_activity and (datetime.now() - last_activity).total_seconds() >= self.idle_threshold:
                        should_capture = True
                        logger.info(f"Idle threshold reached for {window_name}")
                
                if should_capture:
                    logger.info(f"Attempting to capture content from {window_name}")
                    
                    # Capture content
                    content = self.capture_window_content(window_id)
                    logger.info(f"Captured content length: {len(content) if content else 0}")
                    
                    if content:
                        # Get or create memento for this window
                        memento_id = self.get_or_create_memento_for_window(window_id, window_info)
                        
                        if memento_id:
                            # Check if content changed
                            content_hash = self.get_content_hash(content)
                            
                            if (window_id not in self.tracked_windows or 
                                self.tracked_windows[window_id].last_content_hash != content_hash):
                                
                                logger.info(f"Content changed - updating memento {memento_id}")
                                # Content changed - update memento
                                self.update_memento_content(
                                    memento_id, 
                                    content, 
                                    self.tracked_windows[window_id]
                                )
                                
                                # Update GUI with captured text
                                if self.gui_callback:
                                    self.gui_callback(window_name, content)
                            else:
                                logger.info(f"Content unchanged for {window_name}")
                    else:
                        logger.warning(f"No content captured from {window_name}")
                    
                    last_capture_time = current_time
                
                # Sleep for a short interval
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)
        
        logger.info("Auto-capture loop stopped")
    
    def start_capture(self):
        """Start the automatic capture system."""
        if self.is_running:
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info("Auto-capture system started")
    
    def stop_capture(self):
        """Stop the automatic capture system."""
        self.is_running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5)
        logger.info("Auto-capture system stopped")
    
    def get_status(self) -> Dict:
        """Get current status of the capture system."""
        return {
            'running': self.is_running,
            'tracked_windows': len(self.tracked_windows),
            'current_window_id': self.current_window_id,
            'capture_interval': self.capture_interval,
            'idle_threshold': self.idle_threshold,
            'capabilities': self.text_capture.get_capabilities()
        }


class AutoCaptureGUI:
    """GUI for controlling the automatic capture system."""
    
    def __init__(self):
        self.capture_system = AutoCaptureSystem(gui_callback=self._show_captured_text)
        self.root = tk.Tk()
        self.root.title("Memento Auto-Capture System")
        self.root.geometry("1200x900")
        
        self.status_text = tk.StringVar(value="Stopped")
        self.tracked_count = tk.StringVar(value="0")
        
        self._create_widgets()
        self._update_status()
        
        # Start status update timer
        self._schedule_status_update()
    
    def _create_widgets(self):
        """Create the GUI widgets."""
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Memento Auto-Capture System", 
                              font=('TkDefaultFont', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Status section
        status_frame = tk.LabelFrame(main_frame, text="System Status", padx=15, pady=15)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(status_frame, text="Status:", font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        status_label = tk.Label(status_frame, textvariable=self.status_text, font=('TkDefaultFont', 10))
        status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        tk.Label(status_frame, text="Tracked Windows:", font=('TkDefaultFont', 10, 'bold')).grid(row=1, column=0, sticky=tk.W)
        tk.Label(status_frame, textvariable=self.tracked_count, font=('TkDefaultFont', 10)).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Configuration section
        config_frame = tk.LabelFrame(main_frame, text="Configuration", padx=15, pady=15)
        config_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(config_frame, text="Capture Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.DoubleVar(value=self.capture_system.capture_interval)
        tk.Spinbox(config_frame, from_=1.0, to=60.0, increment=1.0, textvariable=self.interval_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        tk.Label(config_frame, text="Idle Threshold (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.idle_var = tk.DoubleVar(value=self.capture_system.idle_threshold)
        tk.Spinbox(config_frame, from_=5.0, to=300.0, increment=5.0, textvariable=self.idle_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Control buttons
        control_frame = tk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.start_button = tk.Button(control_frame, text="🚀 Start Auto-Capture", 
                                     command=self._start_capture, width=25, height=2, 
                                     font=('TkDefaultFont', 12, 'bold'), bg='lightgreen')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = tk.Button(control_frame, text="⏹ Stop Auto-Capture", 
                                    command=self._stop_capture, width=25, height=2, 
                                    font=('TkDefaultFont', 12, 'bold'), bg='lightcoral')
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        tk.Button(control_frame, text="⚙ Apply Settings", 
                 command=self._apply_settings, width=20, height=2, 
                 font=('TkDefaultFont', 12, 'bold'), bg='lightblue').pack(side=tk.RIGHT)
        
        # Window tracking display
        tracking_frame = tk.LabelFrame(main_frame, text="📋 Tracked Windows", padx=15, pady=15)
        tracking_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.tracking_tree = ttk.Treeview(tracking_frame, columns=('name', 'class', 'memento_id', 'last_update'), show='headings', height=12)
        self.tracking_tree.heading('name', text='Window Name')
        self.tracking_tree.heading('class', text='Application')
        self.tracking_tree.heading('memento_id', text='Memento ID')
        self.tracking_tree.heading('last_update', text='Last Update')
        
        self.tracking_tree.column('name', width=300)
        self.tracking_tree.column('class', width=200)
        self.tracking_tree.column('memento_id', width=100)
        self.tracking_tree.column('last_update', width=150)
        
        self.tracking_tree.pack(fill=tk.X)
        
        # Split bottom section into two columns
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        # Activity log (left side)
        log_frame = tk.LabelFrame(bottom_frame, text="📊 Activity Log", padx=10, pady=10)
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, font=('Courier', 9), height=15)
        log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Captured text display (right side)
        capture_frame = tk.LabelFrame(bottom_frame, text="📝 Latest Captured Text", padx=10, pady=10)
        capture_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.captured_text = tk.Text(capture_frame, wrap=tk.WORD, font=('Courier', 9), height=15)
        capture_scrollbar = tk.Scrollbar(capture_frame, orient=tk.VERTICAL, command=self.captured_text.yview)
        self.captured_text.configure(yscrollcommand=capture_scrollbar.set)
        
        self.captured_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        capture_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Instructions
        instructions = """🔍 AUTOMATIC TEXT CAPTURE SYSTEM
        
• Monitors all active windows automatically
• Creates separate mementos for each application
• Captures text content when windows change or at regular intervals
• Replaces memento content with latest captured text
• Ignores system windows (terminals, panels, etc.)

USAGE: Click 'Start Auto-Capture' and switch between applications. 
Each app will get its own memento document that updates automatically!"""
        
        self.log_text.insert(tk.END, instructions + "\\n\\n")
    
    def _start_capture(self):
        """Start the capture system."""
        self._apply_settings()
        self.capture_system.start_capture()
        self._log("🚀 Auto-capture system started")
    
    def _stop_capture(self):
        """Stop the capture system."""
        self.capture_system.stop_capture()
        self._log("⏹ Auto-capture system stopped")
    
    def _apply_settings(self):
        """Apply configuration settings."""
        self.capture_system.capture_interval = self.interval_var.get()
        self.capture_system.idle_threshold = self.idle_var.get()
        self._log(f"⚙ Settings applied: interval={self.capture_system.capture_interval}s, idle={self.capture_system.idle_threshold}s")
    
    def _log(self, message: str):
        """Add message to activity log."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\\n")
        self.log_text.see(tk.END)
    
    def _show_captured_text(self, window_name: str, content: str):
        """Display captured text in the captured text panel."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        header = f"=== CAPTURED FROM: {window_name} at {timestamp} ===\n"
        footer = f"\n=== END CAPTURE ({len(content)} chars) ===\n\n"
        
        self.captured_text.insert(tk.END, header + content + footer)
        self.captured_text.see(tk.END)
        
        # Keep only last 10000 characters to prevent memory issues
        content_length = len(self.captured_text.get('1.0', tk.END))
        if content_length > 10000:
            self.captured_text.delete('1.0', '500.0')  # Remove first 500 lines
    
    def _update_status(self):
        """Update the status display."""
        status = self.capture_system.get_status()
        
        if status['running']:
            self.status_text.set("🟢 Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.status_text.set("🔴 Stopped")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        
        self.tracked_count.set(str(status['tracked_windows']))
        
        # Update tracking tree
        for item in self.tracking_tree.get_children():
            self.tracking_tree.delete(item)
        
        for window_id, window_info in self.capture_system.tracked_windows.items():
            last_update = window_info.last_activity.strftime('%H:%M:%S') if window_info.last_activity else 'Never'
            self.tracking_tree.insert('', tk.END, values=(
                window_info.window_name[:40] + ('...' if len(window_info.window_name) > 40 else ''),
                window_info.window_class,
                window_info.memento_id or 'None',
                last_update
            ))
    
    def _schedule_status_update(self):
        """Schedule regular status updates."""
        self._update_status()
        self.root.after(2000, self._schedule_status_update)  # Update every 2 seconds
    
    def run(self):
        """Run the GUI."""
        try:
            self.root.mainloop()
        finally:
            self.capture_system.stop_capture()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('auto_capture.log')
        ]
    )
    
    # Run the auto-capture GUI
    app = AutoCaptureGUI()
    app.run()
