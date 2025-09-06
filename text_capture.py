#!/usr/bin/env python3
"""
Text Capture Module for Memento
Captures text from active windows and focused text controls across platforms.
"""

import subprocess
import sys
import time
import platform
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class TextCapture:
    """Cross-platform text capture utility."""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.available_methods = self._detect_available_methods()
        logger.info(f"Text capture initialized for {self.platform}")
        logger.info(f"Available methods: {list(self.available_methods.keys())}")
    
    def _detect_available_methods(self) -> Dict[str, bool]:
        """Detect which text capture methods are available on this system."""
        methods = {}
        
        if self.platform == "linux":
            # Check for X11 tools
            methods['xwininfo'] = self._command_available('xwininfo')
            methods['xdotool'] = self._command_available('xdotool')
            methods['xclip'] = self._command_available('xclip')
            methods['xsel'] = self._command_available('xsel')
            methods['wmctrl'] = self._command_available('wmctrl')
            
        elif self.platform == "windows":
            # Windows-specific tools would go here
            methods['powershell'] = self._command_available('powershell')
            methods['win32'] = self._python_module_available('win32gui')
            
        # Universal clipboard access
        methods['tkinter_clipboard'] = True  # tkinter is usually available
        
        return methods
    
    def _command_available(self, command: str) -> bool:
        """Check if a command-line tool is available."""
        try:
            subprocess.run([command], capture_output=True, timeout=2)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _python_module_available(self, module: str) -> bool:
        """Check if a Python module is available."""
        try:
            __import__(module)
            return True
        except ImportError:
            return False
    
    def get_active_window_info(self) -> Dict[str, str]:
        """Get information about the currently active window."""
        if self.platform == "linux":
            return self._get_active_window_info_linux()
        elif self.platform == "windows":
            return self._get_active_window_info_windows()
        else:
            return {"error": f"Unsupported platform: {self.platform}"}
    
    def _get_active_window_info_linux(self) -> Dict[str, str]:
        """Get active window info on Linux using X11 tools."""
        info = {}
        
        try:
            # Get active window ID
            if self.available_methods.get('xdotool'):
                result = subprocess.run(['xdotool', 'getactivewindow'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    window_id = result.stdout.strip()
                    info['window_id'] = window_id
                    
                    # Get window name
                    result = subprocess.run(['xdotool', 'getwindowname', window_id],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        info['window_name'] = result.stdout.strip()
                    
                    # Get window class
                    result = subprocess.run(['xdotool', 'getwindowclassname', window_id],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        info['window_class'] = result.stdout.strip()
            
            elif self.available_methods.get('xwininfo'):
                # Fallback to xwininfo
                result = subprocess.run(['xwininfo', '-name', 'Memento'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['method'] = 'xwininfo'
                    info['available'] = 'basic window info only'
            
        except subprocess.TimeoutExpired:
            info['error'] = 'Timeout getting window info'
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    def _get_active_window_info_windows(self) -> Dict[str, str]:
        """Get active window info on Windows."""
        info = {'platform': 'windows', 'method': 'not_implemented'}
        
        # Windows implementation would use win32gui or PowerShell
        if self.available_methods.get('win32'):
            info['note'] = 'win32gui available but not implemented yet'
        elif self.available_methods.get('powershell'):
            info['note'] = 'PowerShell available but not implemented yet'
        
        return info
    
    def capture_selected_text(self) -> Optional[str]:
        """Capture currently selected text using clipboard."""
        try:
            if self.platform == "linux":
                return self._capture_selected_text_linux()
            elif self.platform == "windows":
                return self._capture_selected_text_windows()
            else:
                return self._capture_selected_text_tkinter()
        except Exception as e:
            logger.error(f"Error capturing selected text: {e}")
            return None
    
    def _capture_selected_text_linux(self) -> Optional[str]:
        """Capture selected text on Linux."""
        # Method 1: Try xclip
        if self.available_methods.get('xclip'):
            try:
                result = subprocess.run(['xclip', '-o', '-selection', 'primary'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
        
        # Method 2: Try xsel
        if self.available_methods.get('xsel'):
            try:
                result = subprocess.run(['xsel', '--primary'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
        
        # Method 3: Fallback to tkinter clipboard
        return self._capture_selected_text_tkinter()
    
    def _capture_selected_text_windows(self) -> Optional[str]:
        """Capture selected text on Windows."""
        # Windows implementation would go here
        return self._capture_selected_text_tkinter()
    
    def _capture_selected_text_tkinter(self) -> Optional[str]:
        """Capture text from tkinter clipboard (cross-platform fallback)."""
        try:
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return text if text else None
        except tk.TclError:
            return None
    
    def auto_select_and_capture(self) -> Optional[str]:
        """Automatically select all text in the active control and capture it."""
        if self.platform == "linux" and self.available_methods.get('xdotool'):
            try:
                # Send Ctrl+A to select all
                subprocess.run(['xdotool', 'key', 'ctrl+a'], timeout=2)
                time.sleep(0.1)  # Small delay
                
                # Send Ctrl+C to copy
                subprocess.run(['xdotool', 'key', 'ctrl+c'], timeout=2)
                time.sleep(0.1)  # Small delay
                
                # Capture from clipboard
                return self.capture_selected_text()
                
            except Exception as e:
                logger.error(f"Auto select and capture failed: {e}")
                return None
        else:
            return None
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Return what capabilities are available on this system."""
        caps = {
            'window_info': False,
            'selected_text': False,
            'auto_select': False,
            'clipboard_access': False
        }
        
        # Window info capabilities
        if self.platform == "linux":
            caps['window_info'] = (self.available_methods.get('xdotool', False) or 
                                 self.available_methods.get('xwininfo', False))
            caps['auto_select'] = self.available_methods.get('xdotool', False)
        
        # Text capture capabilities
        caps['selected_text'] = (self.available_methods.get('xclip', False) or
                                self.available_methods.get('xsel', False) or
                                self.available_methods.get('tkinter_clipboard', False))
        
        caps['clipboard_access'] = self.available_methods.get('tkinter_clipboard', False)
        
        return caps


def create_test_gui():
    """Create a test GUI to demonstrate text capture functionality."""
    
    def test_capture():
        """Test the text capture functionality."""
        results.delete('1.0', tk.END)
        results.insert(tk.END, "Testing text capture...\n\n")
        
        capture = TextCapture()
        
        # Test window info
        results.insert(tk.END, "=== WINDOW INFO ===\n")
        window_info = capture.get_active_window_info()
        for key, value in window_info.items():
            results.insert(tk.END, f"{key}: {value}\n")
        
        results.insert(tk.END, "\n=== CAPABILITIES ===\n")
        caps = capture.get_capabilities()
        for key, value in caps.items():
            status = "✓" if value else "✗"
            results.insert(tk.END, f"{status} {key}: {value}\n")
        
        results.insert(tk.END, "\n=== AVAILABLE METHODS ===\n")
        for method, available in capture.available_methods.items():
            status = "✓" if available else "✗"
            results.insert(tk.END, f"{status} {method}: {available}\n")
    
    def test_selected_text():
        """Test capturing selected text."""
        results.delete('1.0', tk.END)
        results.insert(tk.END, "Capturing selected text...\n\n")
        
        capture = TextCapture()
        text = capture.capture_selected_text()
        
        if text:
            results.insert(tk.END, f"Captured text ({len(text)} chars):\n")
            results.insert(tk.END, f"'{text}'\n")
        else:
            results.insert(tk.END, "No text captured.\n")
            results.insert(tk.END, "Try selecting some text first.\n")
    
    def test_auto_capture():
        """Test auto-select and capture."""
        results.delete('1.0', tk.END)
        results.insert(tk.END, "Auto-selecting and capturing text...\n")
        results.insert(tk.END, "This will attempt to select all text in the active window.\n\n")
        
        # Give user time to switch windows
        root.after(3000, lambda: perform_auto_capture())
    
    def perform_auto_capture():
        capture = TextCapture()
        text = capture.auto_select_and_capture()
        
        if text:
            results.insert(tk.END, f"Auto-captured text ({len(text)} chars):\n")
            results.insert(tk.END, f"'{text}'\n")
        else:
            results.insert(tk.END, "Auto-capture failed.\n")
            results.insert(tk.END, "This method requires xdotool on Linux.\n")
    
    # Create main window
    root = tk.Tk()
    root.title("Text Capture Test")
    root.geometry("800x600")
    
    # Create buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    
    tk.Button(button_frame, text="Test Capabilities", 
             command=test_capture, width=20).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Capture Selected Text", 
             command=test_selected_text, width=20).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Auto-Capture (3sec delay)", 
             command=test_auto_capture, width=20).pack(side=tk.LEFT, padx=5)
    
    # Create results area
    results_frame = tk.Frame(root)
    results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    results = tk.Text(results_frame, wrap=tk.WORD, font=('Courier', 10))
    scrollbar = tk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results.yview)
    results.configure(yscrollcommand=scrollbar.set)
    
    results.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Instructions
    results.insert('1.0', """TEXT CAPTURE TEST UTILITY

Instructions:
1. Click 'Test Capabilities' to see what methods are available
2. Select text in another application, then click 'Capture Selected Text'
3. Click 'Auto-Capture' to automatically select and capture text from the active window

This tests the feasibility of capturing text from external applications.
""")
    
    return root


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create and run test GUI
    app = create_test_gui()
    app.mainloop()
