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
            methods['xprop'] = self._command_available('xprop')
            methods['xclip'] = self._command_available('xclip')
            methods['xsel'] = self._command_available('xsel')
            methods['wmctrl'] = self._command_available('wmctrl')
            
            # Check for advanced text capture tools
            methods['tesseract'] = self._command_available('tesseract')
            methods['scrot'] = self._command_available('scrot')
            methods['import'] = self._command_available('import')  # ImageMagick
            methods['accerciser'] = self._command_available('accerciser')  # AT-SPI
            
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
            # Method 1: Try xprop to get active window from root
            try:
                result = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and 'window id #' in result.stdout:
                    window_id_hex = result.stdout.split('window id # ')[1].strip()
                    if window_id_hex != '0x0':  # Valid active window
                        window_id = str(int(window_id_hex, 16))  # Convert hex to decimal
                        info['window_id'] = window_id
                        
                        # Try to get window name with xprop
                        try:
                            result = subprocess.run(['xprop', '-id', window_id, 'WM_NAME'], 
                                                  capture_output=True, text=True, timeout=2)
                            if result.returncode == 0 and '=' in result.stdout:
                                name = result.stdout.split('=')[1].strip().strip('"')
                                info['window_name'] = name
                        except:
                            pass
                        
                        # Try to get window class with xprop
                        try:
                            result = subprocess.run(['xprop', '-id', window_id, 'WM_CLASS'], 
                                                  capture_output=True, text=True, timeout=2)
                            if result.returncode == 0 and '=' in result.stdout:
                                class_info = result.stdout.split('=')[1].strip()
                                info['window_class'] = class_info
                        except:
                            pass
                        
                        if 'window_name' not in info:
                            info['window_name'] = 'Unknown Window'
                        if 'window_class' not in info:
                            info['window_class'] = 'Unknown'
                            
                        return info
            except Exception as e:
                logger.debug(f"xprop method failed: {e}")
            
            # Method 2: Try xdotool with better error handling
            if self.available_methods.get('xdotool'):
                try:
                    # First get focused window instead of active window
                    result = subprocess.run(['xdotool', 'getwindowfocus'], 
                                          capture_output=True, text=True, timeout=3)
                    if result.returncode == 0 and result.stdout.strip():
                        window_id = result.stdout.strip()
                        if window_id and window_id != '0':
                            info['window_id'] = window_id
                            
                            # Get window name
                            try:
                                result = subprocess.run(['xdotool', 'getwindowname', window_id],
                                                      capture_output=True, text=True, timeout=2)
                                if result.returncode == 0:
                                    info['window_name'] = result.stdout.strip()
                            except:
                                info['window_name'] = 'Unknown'
                            
                            # Get window class
                            try:
                                result = subprocess.run(['xdotool', 'getwindowclassname', window_id],
                                                      capture_output=True, text=True, timeout=2)
                                if result.returncode == 0:
                                    info['window_class'] = result.stdout.strip()
                            except:
                                info['window_class'] = 'Unknown'
                            
                            return info
                except Exception as e:
                    logger.debug(f"xdotool method failed: {e}")
            
            # Method 3: Use wmctrl to get window list and pick the most recent
            if self.available_methods.get('wmctrl'):
                try:
                    result = subprocess.run(['wmctrl', '-l'], 
                                          capture_output=True, text=True, timeout=3)
                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split('\n')
                        # Take the last window in the list as active
                        if lines:
                            line = lines[-1]  # or could use [0] for first window
                            parts = line.split(None, 3)
                            if len(parts) >= 4:
                                info['window_id'] = parts[0]
                                info['window_name'] = parts[3] if len(parts) > 3 else 'Unknown'
                                info['window_class'] = 'wmctrl'
                                return info
                except Exception as e:
                    logger.debug(f"wmctrl method failed: {e}")
            
            # Method 4: Fallback - simulate a window for testing
            if not info:
                info['window_id'] = 'fallback'
                info['window_name'] = 'Simulated Window'
                info['window_class'] = 'Test'
                logger.debug("Using fallback window info for testing")
                return info
            
        except Exception as e:
            logger.error(f"Error in window detection: {e}")
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
    
    def capture_all_window_text(self, window_id: str = None) -> Optional[str]:
        """Capture all visible text from a window using various methods."""
        if self.platform == "linux":
            return self._capture_all_window_text_linux(window_id)
        elif self.platform == "windows":
            return self._capture_all_window_text_windows(window_id)
        else:
            return None
    
    def _capture_all_window_text_linux(self, window_id: str = None) -> Optional[str]:
        """Capture all text from a Linux window using multiple methods."""
        
        # If no window_id provided, get the active window
        if not window_id:
            window_info = self.get_active_window_info()
            window_id = window_info.get('window_id')
            if not window_id:
                return None
        
        captured_texts = []
        
        # Method 1: Try OCR capture (captures ALL visible text, not just selectable)
        text = self._try_ocr_capture(window_id)
        if text and len(text.strip()) > 10:
            logger.debug(f"OCR captured {len(text)} characters")
            captured_texts.append(("ocr", text))
        
        # Method 2: Try focused window auto-select (reliable for text widgets)
        text = self._try_focused_window_select_all(window_id)
        if text and len(text.strip()) > 5:
            logger.debug(f"Focused window select-all captured {len(text)} characters")
            captured_texts.append(("select_all", text))
        
        # Method 3: Try xdotool advanced capture
        text = self._try_xdotool_advanced_capture(window_id)
        if text and len(text.strip()) > 5:
            logger.debug(f"xdotool advanced capture captured {len(text)} characters")
            captured_texts.append(("xdotool_advanced", text))
        
        # Method 4: Try clipboard-based capture with window focus
        text = self._try_clipboard_based_capture(window_id)
        if text and len(text.strip()) > 5:
            logger.debug(f"Clipboard-based capture captured {len(text)} characters")
            captured_texts.append(("clipboard", text))
        
        # Method 5: Try window properties for additional context
        text = self._try_window_properties_capture(window_id)
        if text and len(text.strip()) > 3:
            logger.debug(f"Window properties captured {len(text)} characters")
            captured_texts.append(("properties", text))
        
        # Choose the best capture result
        if captured_texts:
            # Prioritize OCR (captures all visible text) then selection methods
            best_text = None
            best_length = 0
            best_priority = 0
            
            # Priority order: OCR > select_all > advanced > clipboard > properties
            priority_map = {
                "ocr": 5,
                "select_all": 4, 
                "xdotool_advanced": 3,
                "clipboard": 2,
                "properties": 1
            }
            
            for method, text in captured_texts:
                text_length = len(text.strip())
                method_priority = priority_map.get(method, 0)
                
                # Choose based on priority, then length as tiebreaker
                if (method_priority > best_priority or 
                   (method_priority == best_priority and text_length > best_length)):
                    best_text = text
                    best_length = text_length
                    best_priority = method_priority
            
            if best_text:
                logger.debug(f"Selected best result: {best_priority} priority, {best_length} chars")
                return best_text
        
        # Fallback - basic window info
        return self._try_basic_window_info(window_id)
    
    def _try_ocr_capture(self, window_id: str) -> Optional[str]:
        """Try to capture text using enhanced OCR with window screenshot."""
        try:
            from enhanced_ocr import EnhancedOCR
            
            # Use the enhanced OCR system
            ocr = EnhancedOCR()
            results = ocr.capture_and_ocr_window(window_id)
            
            # Return the best result available
            # Priority: openai > anthropic > xai > tesseract > text_boxes
            priority_order = ['openai', 'anthropic', 'xai', 'tesseract', 'text_boxes']
            
            for service in priority_order:
                if service in results and results[service] and not results[service].startswith('Error:'):
                    text = results[service].strip()
                    if len(text) > 3:  # Minimum text length
                        logger.debug(f"Enhanced OCR success with {service}: {len(text)} characters")
                        return text
            
            logger.debug("Enhanced OCR: all services failed or returned empty results")
            return None
            
        except Exception as e:
            logger.debug(f"Enhanced OCR failed: {e}")
            # Fallback to basic tesseract if enhanced OCR fails
            return self._fallback_tesseract_ocr(window_id)
    
    def _fallback_tesseract_ocr(self, window_id: str) -> Optional[str]:
        """Fallback OCR using basic tesseract."""
        try:
            import tempfile
            import os
            
            # Check if necessary tools are available
            if not self._command_available('tesseract'):
                logger.debug("Tesseract not available")
                return None
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                temp_path = temp_img.name
            
            try:
                logger.debug(f"Taking screenshot for fallback OCR: {window_id}")
                
                # Try xwd method
                if self._command_available('xwd'):
                    result = subprocess.run(['xwd', '-id', window_id, '-out', temp_path],
                                          capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        # Convert xwd to png
                        png_path = temp_path + '.png'
                        conv_result = subprocess.run(['convert', temp_path, png_path],
                                                   capture_output=True, timeout=5)
                        if conv_result.returncode == 0:
                            temp_path = png_path
                            logger.debug("Fallback: xwd screenshot converted to png")
                        else:
                            logger.debug(f"Fallback: xwd conversion failed: {conv_result.stderr}")
                            return None
                    else:
                        logger.debug(f"Fallback: xwd failed: {result.stderr}")
                        return None
                else:
                    logger.debug("Fallback: xwd not available")
                    return None
                
                # Check if file exists and has content
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    logger.debug("Fallback: screenshot file is empty or doesn't exist")
                    return None
                
                # Run basic tesseract OCR
                result = subprocess.run(['tesseract', temp_path, 'stdout', '-l', 'eng'], 
                                      capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    text_content = result.stdout.strip()
                    if text_content and len(text_content) > 3:
                        logger.debug(f"Fallback OCR extracted {len(text_content)} characters")
                        return text_content
                    else:
                        logger.debug("Fallback OCR returned empty or very short result")
                else:
                    logger.debug(f"Fallback OCR failed: {result.stderr}")
                    
                return None
                    
            finally:
                # Clean up temp file
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.debug(f"Failed to cleanup temp file: {cleanup_error}")
                    
        except Exception as e:
            logger.debug(f"Fallback OCR failed: {e}")
            return None
    
    def _try_xdotool_text_dump(self, window_id: str) -> Optional[str]:
        """Try to extract text using xdotool window inspection."""
        try:
            if not self.available_methods.get('xdotool'):
                return None
            
            # Try to get window text content
            # Note: This might not work for all window types
            result = subprocess.run(['xdotool', 'selectwindow', '--sync', window_id],
                                  capture_output=True, timeout=3)
            
            if result.returncode == 0:
                # Try to select all text in the window
                subprocess.run(['xdotool', 'key', '--window', window_id, 'ctrl+a'], timeout=2)
                time.sleep(0.2)
                
                # Copy to clipboard
                subprocess.run(['xdotool', 'key', '--window', window_id, 'ctrl+c'], timeout=2)
                time.sleep(0.2)
                
                # Get from clipboard
                return self.capture_selected_text()
                
        except Exception as e:
            logger.debug(f"xdotool text dump failed: {e}")
            return None
    
    def _try_accessibility_capture(self, window_id: str) -> Optional[str]:
        """Try to capture text using accessibility APIs (AT-SPI)."""
        try:
            # Check if AT-SPI tools are available
            if not self._command_available('accerciser'):
                return None
            
            # This would require more complex AT-SPI integration
            # For now, return None - this is a placeholder for future implementation
            return None
            
        except Exception as e:
            logger.debug(f"Accessibility capture failed: {e}")
            return None
    
    def _try_window_properties_capture(self, window_id: str) -> Optional[str]:
        """Try to extract text from window properties."""
        try:
            if not self.available_methods.get('xprop'):
                return None
            
            # Get various window properties that might contain text
            properties = ['WM_NAME', 'WM_ICON_NAME', '_NET_WM_NAME', 
                         'WM_CLIENT_MACHINE', 'WM_COMMAND']
            
            captured_text = []
            
            for prop in properties:
                try:
                    result = subprocess.run(['xprop', '-id', window_id, prop],
                                          capture_output=True, text=True, timeout=2)
                    
                    if result.returncode == 0 and '=' in result.stdout:
                        value = result.stdout.split('=', 1)[1].strip()
                        if value and value != '""' and len(value) > 3:
                            # Clean up the value
                            value = value.strip('"')
                            if value and value not in captured_text:
                                captured_text.append(value)
                                
                except Exception:
                    continue
            
            if captured_text:
                return '\n'.join(captured_text)
                
        except Exception as e:
            logger.debug(f"Window properties capture failed: {e}")
            return None
    
    def _try_basic_window_info(self, window_id: str) -> Optional[str]:
        """Get basic window information as fallback text."""
        try:
            window_info = self.get_active_window_info()
            
            info_text = []
            if window_info.get('window_name'):
                info_text.append(f"Window: {window_info['window_name']}")
            if window_info.get('window_class'):
                info_text.append(f"Application: {window_info['window_class']}")
            
            info_text.append(f"Window ID: {window_id}")
            info_text.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return '\n'.join(info_text)
            
        except Exception as e:
            logger.debug(f"Basic window info capture failed: {e}")
            return "Unable to capture window content"
    
    def _try_focused_window_select_all(self, window_id: str) -> Optional[str]:
        """Try to focus window and select all text."""
        try:
            if not self.available_methods.get('xdotool'):
                return None
            
            # Focus the window first
            subprocess.run(['xdotool', 'windowfocus', window_id], timeout=2)
            time.sleep(0.3)  # Give window time to focus
            
            # Select all text with Ctrl+A
            subprocess.run(['xdotool', 'key', 'ctrl+a'], timeout=2)
            time.sleep(0.2)
            
            # Copy to clipboard with Ctrl+C
            subprocess.run(['xdotool', 'key', 'ctrl+c'], timeout=2)
            time.sleep(0.2)
            
            # Get from clipboard
            return self.capture_selected_text()
            
        except Exception as e:
            logger.debug(f"Focused window select all failed: {e}")
            return None
    
    def _try_xdotool_advanced_capture(self, window_id: str) -> Optional[str]:
        """Try advanced xdotool text extraction methods."""
        try:
            if not self.available_methods.get('xdotool'):
                return None
            
            captured_texts = []
            
            # Method 1: Try multiple selection methods
            for key_combo in ['ctrl+a', 'ctrl+shift+End', 'ctrl+shift+Home']:
                try:
                    # Focus window
                    subprocess.run(['xdotool', 'windowfocus', window_id], timeout=2)
                    time.sleep(0.2)
                    
                    # Clear any existing selection first
                    subprocess.run(['xdotool', 'key', 'Escape'], timeout=1)
                    time.sleep(0.1)
                    
                    # Try selection
                    subprocess.run(['xdotool', 'key', key_combo], timeout=2)
                    time.sleep(0.2)
                    
                    # Copy
                    subprocess.run(['xdotool', 'key', 'ctrl+c'], timeout=2)
                    time.sleep(0.2)
                    
                    # Get text
                    text = self.capture_selected_text()
                    if text and len(text.strip()) > 5:
                        captured_texts.append(text)
                        
                except Exception:
                    continue
            
            # Return the longest captured text
            if captured_texts:
                return max(captured_texts, key=len)
                
        except Exception as e:
            logger.debug(f"xdotool advanced capture failed: {e}")
            return None
    
    def _try_clipboard_based_capture(self, window_id: str) -> Optional[str]:
        """Try clipboard-based text capture with different methods."""
        try:
            if not self.available_methods.get('xdotool'):
                return None
            
            # Store original clipboard content
            original_clipboard = None
            try:
                original_clipboard = self.capture_selected_text()
            except:
                pass
            
            captured_texts = []
            
            # Method 1: Focus and try various text selection approaches
            selection_methods = [
                ['ctrl+a'],  # Select all
                ['ctrl+Home', 'ctrl+shift+End'],  # From start to end
                ['Home', 'ctrl+shift+End'],  # From home to end
                ['ctrl+End', 'ctrl+shift+Home'],  # From end to start
            ]
            
            for method in selection_methods:
                try:
                    # Clear clipboard first
                    subprocess.run(['xclip', '-selection', 'clipboard', '/dev/null'], 
                                 stdin=subprocess.PIPE, timeout=1)
                    time.sleep(0.1)
                    
                    # Focus window
                    subprocess.run(['xdotool', 'windowfocus', window_id], timeout=2)
                    time.sleep(0.3)
                    
                    # Execute selection method
                    for key in method:
                        subprocess.run(['xdotool', 'key', key], timeout=2)
                        time.sleep(0.1)
                    
                    # Copy to clipboard
                    subprocess.run(['xdotool', 'key', 'ctrl+c'], timeout=2)
                    time.sleep(0.3)
                    
                    # Get text from clipboard
                    text = self.capture_selected_text()
                    if text and len(text.strip()) > 5:
                        captured_texts.append(text)
                        
                except Exception:
                    continue
            
            # Restore original clipboard if possible
            if original_clipboard:
                try:
                    root = tk.Tk()
                    root.withdraw()
                    root.clipboard_clear()
                    root.clipboard_append(original_clipboard)
                    root.destroy()
                except:
                    pass
            
            # Return the longest captured text
            if captured_texts:
                return max(captured_texts, key=len)
                
        except Exception as e:
            logger.debug(f"Clipboard-based capture failed: {e}")
            return None
    
    def _capture_all_window_text_windows(self, window_id: str = None) -> Optional[str]:
        """Capture all text from a Windows window."""
        # Windows implementation placeholder
        # Would use Win32 APIs or PowerShell to extract text
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
    
    def test_comprehensive_capture():
        """Test comprehensive text capture."""
        results.delete('1.0', tk.END)
        results.insert(tk.END, "Comprehensive text capture...\n")
        results.insert(tk.END, "This will try multiple methods to capture all window text.\n\n")
        
        # Give user time to switch windows
        root.after(3000, lambda: perform_comprehensive_capture())
    
    def perform_auto_capture():
        capture = TextCapture()
        text = capture.auto_select_and_capture()
        
        if text:
            results.insert(tk.END, f"Auto-captured text ({len(text)} chars):\n")
            results.insert(tk.END, f"'{text}'\n")
        else:
            results.insert(tk.END, "Auto-capture failed.\n")
            results.insert(tk.END, "This method requires xdotool on Linux.\n")
    
    def perform_comprehensive_capture():
        capture = TextCapture()
        text = capture.capture_all_window_text()
        
        if text:
            results.insert(tk.END, f"Comprehensive captured text ({len(text)} chars):\n")
            results.insert(tk.END, "=" * 40 + "\n")
            results.insert(tk.END, f"{text}\n")
            results.insert(tk.END, "=" * 40 + "\n")
        else:
            results.insert(tk.END, "Comprehensive capture failed.\n")
    
    # Create main window
    root = tk.Tk()
    root.title("Text Capture Test")
    root.geometry("800x600")
    
    # Create buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    
    tk.Button(button_frame, text="Test Capabilities", 
             command=test_capture, width=18).pack(side=tk.LEFT, padx=2)
    tk.Button(button_frame, text="Capture Selected Text", 
             command=test_selected_text, width=18).pack(side=tk.LEFT, padx=2)
    tk.Button(button_frame, text="Auto-Capture (3s)", 
             command=test_auto_capture, width=18).pack(side=tk.LEFT, padx=2)
    tk.Button(button_frame, text="Comprehensive (3s)", 
             command=test_comprehensive_capture, width=18).pack(side=tk.LEFT, padx=2)
    
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
