#!/usr/bin/env python3
"""
Test script for Enhanced OCR System
Demonstrates multi-service OCR with text input box detection
"""

import sys
import os
import time
from enhanced_ocr import EnhancedOCR
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_active_window_id():
    """Get the currently active window ID."""
    try:
        result = subprocess.run(['xdotool', 'getactivewindow'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"Failed to get active window: {e}")
        return None

def main():
    print("=== Enhanced OCR Test System ===")
    print("\nThis system uses multiple AI services to extract text from windows:")
    print("- Local: Tesseract OCR")
    print("- Cloud: OpenAI Vision, Anthropic Claude Vision, XAI Vision")
    print("- Features: Text input box detection, image preprocessing")
    print()
    
    # Initialize OCR system
    ocr = EnhancedOCR()
    
    print(f"Available services: {[k for k, v in ocr.available_services.items() if v]}")
    print()
    
    # Check if we're on Wayland
    session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
    
    if len(sys.argv) > 1:
        # Use provided window ID
        window_id = sys.argv[1]
        print(f"Using window ID: {window_id}")
    elif session_type == 'wayland':
        # On Wayland, use full screenshot mode
        window_id = None
        print("Running on Wayland - using full screenshot mode")
        print("Window-specific capture may not work due to security restrictions")
    else:
        # Get active window on X11
        print("Getting active window ID...")
        window_id = get_active_window_id()
        if not window_id:
            print("Error: Could not get active window ID")
            print("Usage: python3 test_enhanced_ocr.py [window_id]")
            return
        print(f"Active window ID: {window_id}")
    
    print(f"\nStarting OCR capture in 3 seconds...")
    print("Make sure the target window contains visible text input fields!")
    
    # Countdown
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    print("\nCapturing and processing...")
    
    # Run OCR with all available services
    results = ocr.capture_and_ocr_window(window_id)
    
    print("\n=== OCR RESULTS ===")
    print()
    
    if not results:
        print("No results returned!")
        return
    
    # Display results for each service
    for service, text in results.items():
        print(f"--- {service.upper()} ---")
        
        if text.startswith("Error:"):
            print(f"❌ {text}")
        elif not text or len(text.strip()) < 3:
            print("❌ No meaningful text captured")
        else:
            print(f"✅ Captured {len(text)} characters:")
            
            # Show preview (first 200 characters)
            preview = text[:200]
            if len(text) > 200:
                preview += "..."
            
            print(f'"{preview}"')
        
        print()
    
    # Summary
    successful_services = [s for s, t in results.items() 
                          if t and not t.startswith("Error:") and len(t.strip()) >= 3]
    
    print(f"Summary: {len(successful_services)}/{len(results)} services captured text successfully")
    
    if successful_services:
        print("✅ Success! The enhanced OCR system is working.")
        print("\nNow you can:")
        print("1. Run 'python3 ocr_accuracy_tester.py' to test and rate accuracy")
        print("2. Use different windows with text input fields")
        print("3. Compare results between AI services")
    else:
        print("❌ No services captured meaningful text.")
        print("\nTroubleshooting:")
        print("1. Ensure the window contains visible text")
        print("2. Check that text is not just images")
        print("3. Try windows with text input fields or forms")
        print("4. Verify API keys are properly set in ~/.bashrc")

if __name__ == "__main__":
    main()
