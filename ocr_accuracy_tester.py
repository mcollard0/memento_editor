#!/usr/bin/env python3
"""
OCR Accuracy Test GUI for comparing different AI services
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import json
import os
from enhanced_ocr import EnhancedOCR
import subprocess
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class OCRAccuracyTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced OCR Test & Accuracy Comparison")
        self.root.geometry("1400x900")
        
        self.ocr = EnhancedOCR()
        self.last_results = {}
        self.accuracy_scores = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # API Key status (read-only, from environment)
        ttk.Label(config_frame, text="API Keys Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # Display API key status
        api_status = []
        if self.ocr.config.get("openai_api_key"):
            api_status.append("✓ OpenAI")
        else:
            api_status.append("✗ OpenAI")
            
        if self.ocr.config.get("anthropic_api_key"):
            api_status.append("✓ Anthropic")
        else:
            api_status.append("✗ Anthropic")
            
        if self.ocr.config.get("xai_api_key"):
            api_status.append("✓ XAI")
        else:
            api_status.append("✗ XAI")
        
        status_text = " | ".join(api_status)
        ttk.Label(config_frame, text=status_text).grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(config_frame, text="Note: API keys loaded from environment variables in ~/.bashrc", 
                 font=('TkDefaultFont', 8, 'italic')).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(main_frame, text="Instructions", padding="10")
        instructions_frame.grid(row=0, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N), padx=(10, 0))
        
        # Add Chrome-specific instructions for Wayland
        session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
        chrome_tip = ""
        if session_type == 'wayland':
            chrome_tip = "\n\n🌐 Chrome/Browser Testing:\n• Leave Window ID empty for full screenshot\n• Maximize browser with forms/input fields\n• Use F11 for fullscreen testing"
        
        instructions_text = (
            "Rating Guide (Higher is Better):\n\n"
            "10 = Perfect: All text captured accurately\n"
            "8-9 = Excellent: Minor formatting issues only\n"
            "6-7 = Good: Most text correct, some errors\n"
            "4-5 = Fair: Significant errors but usable\n"
            "2-3 = Poor: Many errors, barely readable\n"
            "1 = Failed: No useful text captured\n\n"
            "Focus on text input boxes and form fields!\n\n"
            "Tips:\n"
            "• Use windows with visible text input fields\n"
            "• Ensure good contrast and legible text\n"
            "• Test different applications (browser, editor, forms)\n"
            "• Rate based on practical usefulness" +
            chrome_tip
        )
        
        instructions_label = tk.Label(instructions_frame, text=instructions_text, 
                                    justify=tk.LEFT, font=('TkDefaultFont', 9),
                                    wraplength=250)
        instructions_label.grid(row=0, column=0, sticky=(tk.W, tk.N))
        
        # Window capture section
        capture_frame = ttk.LabelFrame(main_frame, text="Window Capture", padding="10")
        capture_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Row 1: Window ID input
        ttk.Label(capture_frame, text="Window ID (optional):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.window_id_var = tk.StringVar()
        ttk.Entry(capture_frame, textvariable=self.window_id_var, width=20).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(capture_frame, text="Get Active Window", command=self.get_active_window).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(capture_frame, text="Select Window", command=self.select_window).grid(row=0, column=3, padx=(0, 10))
        
        # Row 2: Capture button and info
        ttk.Button(capture_frame, text="🔍 Capture & Test All", command=self.capture_and_test).grid(row=1, column=0, columnspan=2, pady=(10, 5), sticky=tk.W)
        
        # Row 3: Wayland info
        session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
        if session_type == 'wayland':
            info_text = "ℹ️ Wayland detected: Chrome/browser windows use full screenshot mode"
            info_color = "blue"
        else:
            info_text = "ℹ️ X11 detected: Individual window selection available"
            info_color = "green"
            
        info_label = tk.Label(capture_frame, text=info_text, 
                             font=('TkDefaultFont', 8), fg=info_color)
        info_label.grid(row=2, column=0, columnspan=5, sticky=tk.W, pady=(0, 5))
        
        # Progress bar
        self.progress = ttk.Progressbar(capture_frame, mode='indeterminate')
        self.progress.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10)
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="OCR Results", padding="10")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create notebook for different OCR services
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs for each service (primary first, then individual services)
        self.service_tabs = {}
        services = ['primary', 'anthropic', 'xai', 'openai', 'tesseract', 'text_boxes']
        
        for service in services:
            frame = ttk.Frame(self.notebook)
            
            # Special labeling for primary tab
            if service == 'primary':
                tab_label = "🏆 Best Result"
            elif service == 'text_boxes':
                tab_label = "📦 Text Boxes"
            elif service == 'tesseract':
                tab_label = "🐌 Tesseract (CPU)"
            else:
                tab_label = service.title()
                
            self.notebook.add(frame, text=tab_label)
            
            # Text area for results
            text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15)
            text_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            
            # Accuracy rating section
            rating_frame = ttk.Frame(frame)
            rating_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            ttk.Label(rating_frame, text="Accuracy Rating (1=Failed, 10=Perfect):").grid(row=0, column=0, padx=(0, 10))
            
            rating_var = tk.IntVar(value=5)
            rating_scale = tk.Scale(rating_frame, from_=1, to=10, orient=tk.HORIZONTAL, 
                                   variable=rating_var, length=250, resolution=1)
            rating_scale.grid(row=0, column=1, padx=(0, 10))
            
            # Add current rating display
            rating_display = tk.Label(rating_frame, text="5", font=('TkDefaultFont', 12, 'bold'))
            rating_display.grid(row=0, column=2, padx=(5, 10))
            
            # Update display when scale changes
            def update_rating_display(*args):
                rating_display.config(text=str(rating_var.get()))
            rating_var.trace('w', update_rating_display)
            
            ttk.Button(rating_frame, text="Save Rating", 
                       command=lambda s=service, r=rating_var: self.save_rating(s, r.get())).grid(row=0, column=2)
            
            self.service_tabs[service] = {
                'text_area': text_area,
                'rating_var': rating_var,
                'rating_scale': rating_scale
            }
            
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
        
        # Accuracy summary section
        summary_frame = ttk.LabelFrame(main_frame, text="Accuracy Summary", padding="10")
        summary_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=5)
        self.summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Button(summary_frame, text="Load Test Results", command=self.load_test_results).grid(row=1, column=0, pady=5)
        ttk.Button(summary_frame, text="Save Test Results", command=self.save_test_results).grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # Configure grid weights
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(2, weight=0)  # Instructions panel
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)
        
        self.load_accuracy_scores()
        self.update_summary()
        
    # Configuration is now loaded from environment variables automatically
        
    def get_active_window(self):
        """Get the currently active window ID."""
        try:
            result = subprocess.run(['xdotool', 'getactivewindow'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                window_id = result.stdout.strip()
                self.window_id_var.set(window_id)
                logger.info(f"Active window ID: {window_id}")
            else:
                messagebox.showerror("Error", "Failed to get active window ID")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get active window: {e}")
    
    def select_window(self):
        """Allow user to select a window by clicking."""
        try:
            messagebox.showinfo("Select Window", "Click on the window you want to capture text from.")
            result = subprocess.run(['xdotool', 'selectwindow'], 
                                   capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                window_id = result.stdout.strip()
                self.window_id_var.set(window_id)
                logger.info(f"Selected window ID: {window_id}")
            else:
                messagebox.showerror("Error", "Failed to select window")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to select window: {e}")
    
    def capture_and_test(self):
        """Capture window and test all OCR services."""
        window_id = self.window_id_var.get().strip()
        
        # Check if we're on Wayland and explain the capture process
        session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
        
        if session_type == 'wayland':
            if window_id:
                message = ("Capture will begin in 3 seconds.\n\n"
                          "On Wayland, window-specific capture may require interaction.\n"
                          "If window capture fails, full screen capture will be used.\n\n"
                          "Please ensure the target content is visible.")
            else:
                message = ("Capture will begin in 3 seconds.\n\n"
                          "Full screen capture will be used.\n\n"
                          "Please ensure the target content is visible and not obscured.")
        else:
            if not window_id:
                messagebox.showerror("Error", "Please provide a window ID or get the active window")
                return
            message = ("Capture will begin in 3 seconds.\n\n"
                      "Please ensure the target window is visible and contains text.")
        
        # Notify user about capture process
        messagebox.showinfo("Capture Starting", message)
        
        # Start progress bar
        self.progress.start()
        
        # Run capture in separate thread
        thread = threading.Thread(target=self._run_capture_test, args=(window_id,))
        thread.daemon = True
        thread.start()
    
    def _run_capture_test(self, window_id):
        """Run the capture test in a separate thread."""
        try:
            logger.info(f"Starting OCR test for window {window_id}")
            results = self.ocr.capture_and_ocr_window(window_id)
            self.last_results = results
            
            # Update UI in main thread
            self.root.after(0, self._update_results, results)
            
        except Exception as e:
            logger.error(f"Capture test failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Capture test failed: {e}"))
        finally:
            self.root.after(0, self.progress.stop)
    
    def _update_results(self, results):
        """Update the results display."""
        for service, text in results.items():
            if service in self.service_tabs:
                text_area = self.service_tabs[service]['text_area']
                text_area.delete(1.0, tk.END)
                text_area.insert(1.0, text)
        
        logger.info(f"Updated results for {len(results)} services")
    
    def save_rating(self, service, rating):
        """Save accuracy rating for a service."""
        if service not in self.last_results:
            messagebox.showwarning("Warning", f"No results available for {service}")
            return
        
        timestamp = int(time.time())
        
        if service not in self.accuracy_scores:
            self.accuracy_scores[service] = []
        
        self.accuracy_scores[service].append({
            'rating': rating,
            'timestamp': timestamp,
            'text_length': len(self.last_results[service]),
            'text_preview': self.last_results[service][:100]
        })
        
        self.save_accuracy_scores()
        self.update_summary()
        
        messagebox.showinfo("Rating Saved", f"Rating {rating}/10 saved for {service}")
    
    def load_accuracy_scores(self):
        """Load accuracy scores from file."""
        try:
            if os.path.exists('accuracy_scores.json'):
                with open('accuracy_scores.json', 'r') as f:
                    self.accuracy_scores = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load accuracy scores: {e}")
            self.accuracy_scores = {}
    
    def save_accuracy_scores(self):
        """Save accuracy scores to file."""
        try:
            with open('accuracy_scores.json', 'w') as f:
                json.dump(self.accuracy_scores, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save accuracy scores: {e}")
    
    def update_summary(self):
        """Update the accuracy summary display."""
        summary_lines = ["=== Accuracy Summary ===", ""]
        
        for service, scores in self.accuracy_scores.items():
            if scores:
                ratings = [score['rating'] for score in scores]
                avg_rating = sum(ratings) / len(ratings)
                summary_lines.append(f"{service.title()}: {avg_rating:.1f}/10 (from {len(ratings)} tests)")
        
        if len(summary_lines) == 2:
            summary_lines.append("No accuracy ratings yet. Test some OCR services and rate their accuracy.")
        
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, "\n".join(summary_lines))
    
    def save_test_results(self):
        """Save current test results to a file."""
        if not self.last_results:
            messagebox.showwarning("Warning", "No test results to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.last_results, f, indent=2)
                messagebox.showinfo("Saved", f"Test results saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save results: {e}")
    
    def load_test_results(self):
        """Load test results from a file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    results = json.load(f)
                self.last_results = results
                self._update_results(results)
                messagebox.showinfo("Loaded", f"Test results loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load results: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = OCRAccuracyTester(root)
    root.mainloop()
