#!/usr/bin/env python3
"""
Wayland-compatible screenshot utility
Handles different display protocols and screenshot tools
"""

import subprocess
import tempfile
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class WaylandScreenshot:
    def __init__(self):
        self.session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
        self.desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
        
    def _command_available(self, command: str) -> bool:
        """Check if a command is available in the system."""
        try:
            result = subprocess.run(['which', command], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def take_window_screenshot(self, window_id: str = None, output_path: str = None) -> Optional[str]:
        """Take a screenshot, trying different methods based on the session type."""
        
        if not output_path:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                output_path = temp_file.name
        
        logger.info(f"Taking screenshot with session type: {self.session_type}")
        
        # Method 1: Try Wayland-native tools first
        if self.session_type == 'wayland':
            screenshot_path = self._try_wayland_screenshot(output_path, window_id)
            if screenshot_path:
                return screenshot_path
        
        # Method 2: Try X11 tools (may work via XWayland)
        screenshot_path = self._try_x11_screenshot(output_path, window_id)
        if screenshot_path:
            return screenshot_path
        
        # Method 3: Try desktop-specific tools
        screenshot_path = self._try_desktop_specific_screenshot(output_path, window_id)
        if screenshot_path:
            return screenshot_path
        
        # Method 4: Interactive fallback
        screenshot_path = self._try_interactive_screenshot(output_path)
        if screenshot_path:
            return screenshot_path
            
        logger.error("All screenshot methods failed")
        return None
    
    def _try_wayland_screenshot(self, output_path: str, window_id: str = None) -> Optional[str]:
        """Try Wayland-native screenshot tools."""
        
        # Method 1: grim (best for Wayland)
        if self._command_available('grim'):
            try:
                logger.debug("Trying grim screenshot")
                
                if window_id and self._command_available('slurp'):
                    # Try to get window geometry and use slurp
                    # Note: This is tricky with Wayland security, may require user interaction
                    logger.debug("Requesting user to select window area")
                    result = subprocess.run(['grim', '-g', '$(slurp)', output_path], 
                                          shell=True, capture_output=True, text=True, timeout=30)
                else:
                    # Full screen capture
                    result = subprocess.run(['grim', output_path], 
                                          capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    logger.debug("grim screenshot successful")
                    return output_path
                else:
                    logger.debug(f"grim failed: {result.stderr}")
                    
            except Exception as e:
                logger.debug(f"grim screenshot failed: {e}")
        
        return None
    
    def _try_x11_screenshot(self, output_path: str, window_id: str = None) -> Optional[str]:
        """Try X11 screenshot tools (may work via XWayland)."""
        
        # Method 1: xwd (if available and window_id provided)
        if window_id and self._command_available('xwd') and self._command_available('convert'):
            try:
                logger.debug(f"Trying xwd screenshot for window {window_id}")
                
                xwd_path = output_path + '.xwd'
                result = subprocess.run(['xwd', '-id', window_id, '-out', xwd_path],
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    # Convert to PNG
                    conv_result = subprocess.run(['convert', xwd_path, output_path],
                                               capture_output=True, timeout=5)
                    
                    # Cleanup XWD file
                    try:
                        os.unlink(xwd_path)
                    except:
                        pass
                    
                    if conv_result.returncode == 0 and os.path.exists(output_path):
                        logger.debug("xwd screenshot successful")
                        return output_path
                else:
                    logger.debug(f"xwd failed: {result.stderr}")
                    
            except Exception as e:
                logger.debug(f"xwd screenshot failed: {e}")
        
        return None
    
    def _try_desktop_specific_screenshot(self, output_path: str, window_id: str = None) -> Optional[str]:
        """Try desktop environment specific screenshot tools."""
        
        # GNOME Screenshot
        if 'gnome' in self.desktop.lower() and self._command_available('gnome-screenshot'):
            try:
                logger.debug("Trying gnome-screenshot")
                
                if window_id:
                    # Window screenshot (requires user interaction in Wayland)
                    result = subprocess.run(['gnome-screenshot', '--window', '--file', output_path],
                                          capture_output=True, timeout=15)
                else:
                    # Full screen
                    result = subprocess.run(['gnome-screenshot', '--file', output_path],
                                          capture_output=True, timeout=10)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    logger.debug("gnome-screenshot successful")
                    return output_path
                else:
                    logger.debug(f"gnome-screenshot failed: {result.stderr}")
                    
            except Exception as e:
                logger.debug(f"gnome-screenshot failed: {e}")
        
        return None
    
    def _try_interactive_screenshot(self, output_path: str) -> Optional[str]:
        """Try interactive screenshot methods that require user selection."""
        
        # Try spectacle (KDE)
        if self._command_available('spectacle'):
            try:
                logger.info("Using spectacle - please select the window to capture")
                result = subprocess.run(['spectacle', '--region', '--background', 
                                       '--output', output_path],
                                      capture_output=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    logger.debug("spectacle screenshot successful")
                    return output_path
                    
            except Exception as e:
                logger.debug(f"spectacle failed: {e}")
        
        # Try scrot with selection
        if self._command_available('scrot'):
            try:
                logger.info("Using scrot - please click and drag to select area")
                result = subprocess.run(['scrot', '--select', '--freeze', output_path],
                                      capture_output=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    logger.debug("scrot screenshot successful")
                    return output_path
                    
            except Exception as e:
                logger.debug(f"scrot failed: {e}")
        
        return None
    
    def take_full_screenshot(self, output_path: str = None) -> Optional[str]:
        """Take a full screen screenshot (easier than window-specific)."""
        
        if not output_path:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                output_path = temp_file.name
        
        # Try different methods in order of preference
        methods = []
        
        if self.session_type == 'wayland':
            if self._command_available('grim'):
                methods.append((['grim', output_path], "grim"))
        
        if 'gnome' in self.desktop.lower() and self._command_available('gnome-screenshot'):
            methods.append((['gnome-screenshot', '--file', output_path], "gnome-screenshot"))
        
        if self._command_available('spectacle'):
            methods.append((['spectacle', '--fullscreen', '--background', '--output', output_path], "spectacle"))
        
        if self._command_available('scrot'):
            methods.append((['scrot', output_path], "scrot"))
        
        for command, name in methods:
            try:
                logger.debug(f"Trying {name} for full screenshot")
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    logger.debug(f"{name} screenshot successful")
                    return output_path
                else:
                    logger.debug(f"{name} failed: {result.stderr}")
                    
            except Exception as e:
                logger.debug(f"{name} failed: {e}")
        
        logger.error("All full screenshot methods failed")
        return None


def test_screenshot():
    """Test the screenshot functionality."""
    screenshot = WaylandScreenshot()
    
    print(f"Session type: {screenshot.session_type}")
    print(f"Desktop: {screenshot.desktop}")
    print()
    
    print("Testing full screenshot...")
    result = screenshot.take_full_screenshot()
    
    if result:
        print(f"✅ Screenshot saved to: {result}")
        print(f"File size: {os.path.getsize(result)} bytes")
    else:
        print("❌ Screenshot failed")

if __name__ == "__main__":
    test_screenshot()
