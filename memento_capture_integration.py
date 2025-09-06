#!/usr/bin/env python3
"""
Memento Text Capture Integration
Adds external text capture functionality to the Memento editor.
"""

import tkinter as tk
from tkinter import messagebox, Menu
import threading
import time
from typing import Optional
import logging

# Import our text capture module
from text_capture import TextCapture

logger = logging.getLogger(__name__)

class CaptureDialog:
    """Dialog for configuring text capture options."""
    
    def __init__(self, parent, capture_instance: TextCapture):
        self.parent = parent
        self.capture = capture_instance
        self.result = None
        self.capture_method = tk.StringVar(value="clipboard")
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Capture Text from External Application")
        self.dialog.geometry("750x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._center_dialog()
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Capture Text from External Application", 
                              font=('TkDefaultFont', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Capabilities info
        caps_frame = tk.LabelFrame(main_frame, text="Available Capture Methods", padx=10, pady=10)
        caps_frame.pack(fill=tk.X, pady=(0, 20))
        
        caps = self.capture.get_capabilities()
        for key, available in caps.items():
            status = "✓" if available else "✗"
            color = "green" if available else "red"
            label = tk.Label(caps_frame, text=f"{status} {key.replace('_', ' ').title()}", 
                           fg=color, font=('TkDefaultFont', 10))
            label.pack(anchor=tk.W)
        
        # Method selection
        method_frame = tk.LabelFrame(main_frame, text="Capture Method", padx=10, pady=10)
        method_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Radiobutton(method_frame, text="Capture Selected Text (from clipboard)", 
                      variable=self.capture_method, value="clipboard").pack(anchor=tk.W)
        
        if caps.get('auto_select', False):
            tk.Radiobutton(method_frame, text="Auto-select and Capture (Ctrl+A then Ctrl+C)", 
                          variable=self.capture_method, value="auto_select").pack(anchor=tk.W)
        
        # Instructions
        instructions_frame = tk.LabelFrame(main_frame, text="Instructions", padx=10, pady=10)
        instructions_frame.pack(fill=tk.X, pady=(0, 20))
        
        instructions_text = tk.Text(instructions_frame, height=8, wrap=tk.WORD, 
                                  font=('TkDefaultFont', 9))
        instructions_text.pack(fill=tk.BOTH, expand=True)
        
        instructions = """1. CLIPBOARD METHOD:
   • Select text in any application
   • Copy it (Ctrl+C) 
   • Click "Capture Now" below
   • The copied text will be inserted into your memento

2. AUTO-SELECT METHOD (if available):
   • Click "Capture in 3 seconds"
   • Switch to the target application window
   • Position cursor in the text field you want to capture
   • Wait for automatic capture (Ctrl+A + Ctrl+C will be sent)

3. The captured text will be inserted at your cursor position in the memento.

Note: This works with most text fields, browsers, documents, terminals, etc."""
        
        instructions_text.insert('1.0', instructions)
        instructions_text.config(state=tk.DISABLED)
        
        # Buttons - make them larger and more prominent
        button_frame = tk.Frame(main_frame, bg='lightgray', relief=tk.RAISED, bd=2)
        button_frame.pack(fill=tk.X, pady=(20, 0), padx=5)
        
        # Add some padding inside the button frame
        inner_button_frame = tk.Frame(button_frame)
        inner_button_frame.pack(pady=15, padx=15)
        
        tk.Button(inner_button_frame, text="Capture Now", 
                 command=self._capture_immediate, width=20, height=2, 
                 font=('TkDefaultFont', 10, 'bold'), bg='lightgreen').pack(side=tk.LEFT, padx=10)
        
        if caps.get('auto_select', False):
            tk.Button(inner_button_frame, text="Capture in 3 seconds", 
                     command=self._capture_delayed, width=20, height=2, 
                     font=('TkDefaultFont', 10, 'bold'), bg='lightblue').pack(side=tk.LEFT, padx=10)
        
        tk.Button(inner_button_frame, text="Cancel", 
                 command=self._cancel, width=20, height=2, 
                 font=('TkDefaultFont', 10, 'bold'), bg='lightcoral').pack(side=tk.RIGHT, padx=10)
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _capture_immediate(self):
        """Capture text immediately."""
        method = self.capture_method.get()
        
        if method == "clipboard":
            text = self.capture.capture_selected_text()
        elif method == "auto_select":
            text = self.capture.auto_select_and_capture()
        else:
            text = None
        
        if text and text.strip():
            self.result = text
            self.dialog.destroy()
        else:
            messagebox.showwarning("No Text Captured", 
                                 "No text was captured. Make sure you have selected and copied some text first.")
    
    def _capture_delayed(self):
        """Capture text after a 3-second delay."""
        self.dialog.withdraw()  # Hide dialog
        
        # Show countdown
        countdown_dialog = tk.Toplevel(self.parent)
        countdown_dialog.title("Capture Countdown")
        countdown_dialog.geometry("300x150")
        countdown_dialog.transient(self.parent)
        countdown_dialog.grab_set()
        
        label = tk.Label(countdown_dialog, text="Switch to target window...", 
                        font=('TkDefaultFont', 12))
        label.pack(expand=True)
        
        countdown_label = tk.Label(countdown_dialog, text="3", 
                                  font=('TkDefaultFont', 24, 'bold'))
        countdown_label.pack()
        
        def countdown(seconds):
            if seconds > 0:
                countdown_label.config(text=str(seconds))
                countdown_dialog.after(1000, lambda: countdown(seconds - 1))
            else:
                countdown_label.config(text="Capturing...")
                countdown_dialog.after(500, perform_capture)
        
        def perform_capture():
            text = self.capture.auto_select_and_capture()
            countdown_dialog.destroy()
            
            if text and text.strip():
                self.result = text
                self.dialog.destroy()
            else:
                self.dialog.deiconify()  # Show dialog again
                messagebox.showwarning("No Text Captured", 
                                     "Auto-capture failed. The target application may not support this method.")
        
        countdown(3)
    
    def _cancel(self):
        """Cancel the capture."""
        self.result = None
        self.dialog.destroy()
    
    def show(self) -> Optional[str]:
        """Show the dialog and return the result."""
        self.dialog.wait_window()
        return self.result


def add_text_capture_to_editor(editor_window):
    """Add text capture functionality to an existing EditorWindow."""
    
    # Initialize text capture
    try:
        text_capture = TextCapture()
        logger.info("Text capture functionality initialized")
    except Exception as e:
        logger.error(f"Failed to initialize text capture: {e}")
        return False
    
    # Add menu items
    def show_capture_dialog():
        """Show the text capture dialog."""
        try:
            dialog = CaptureDialog(editor_window.root, text_capture)
            captured_text = dialog.show()
            
            if captured_text:
                # Insert the captured text at cursor position
                editor_window.text_widget.insert(tk.INSERT, captured_text)
                
                # Mark as changed
                editor_window.save_status.mark_changed()
                editor_window._update_status_bar()
                
                # Trigger autosave
                editor_window.idle_saver.update(char_added=True)
                
                logger.info(f"Captured and inserted {len(captured_text)} characters")
                
        except Exception as e:
            logger.error(f"Error during text capture: {e}")
            messagebox.showerror("Capture Error", f"Failed to capture text: {str(e)}")
    
    def quick_clipboard_capture():
        """Quick capture from clipboard."""
        try:
            text = text_capture.capture_selected_text()
            if text and text.strip():
                # Insert at cursor position
                editor_window.text_widget.insert(tk.INSERT, text)
                
                # Mark as changed
                editor_window.save_status.mark_changed()
                editor_window._update_status_bar()
                
                # Trigger autosave
                editor_window.idle_saver.update(char_added=True)
                
                logger.info(f"Quick captured {len(text)} characters from clipboard")
            else:
                messagebox.showinfo("No Text", "No text found in clipboard to capture.")
        except Exception as e:
            logger.error(f"Error during quick capture: {e}")
            messagebox.showerror("Capture Error", f"Failed to capture from clipboard: {str(e)}")
    
    # Get or create the menubar
    try:
        menubar = editor_window.root.nametowidget(editor_window.root['menu'])
    except (KeyError, tk.TclError):
        # No menubar exists, create one
        menubar = Menu(editor_window.root)
        editor_window.root.config(menu=menubar)
    
    # Add Tools menu if it doesn't exist
    tools_menu = None
    try:
        # Try to find existing Tools menu
        for i in range(menubar.index('end') + 1):
            try:
                if menubar.entrycget(i, 'label') == 'Tools':
                    tools_menu = menubar.nametowidget(menubar.entrycget(i, 'menu'))
                    break
            except:
                continue
    except (tk.TclError, ValueError):
        # Menu is empty or index method failed
        pass
    
    if not tools_menu:
        tools_menu = Menu(menubar, tearoff=0)
        # Just add the Tools menu - don't worry about positioning
        menubar.add_cascade(label="Tools", menu=tools_menu)
    
    # Add capture menu items
    tools_menu.add_separator()
    tools_menu.add_command(label="Capture Text from External App...", 
                          command=show_capture_dialog, accelerator="Ctrl+Shift+V")
    tools_menu.add_command(label="Quick Capture from Clipboard", 
                          command=quick_clipboard_capture, accelerator="Ctrl+Alt+V")
    
    # Add keyboard shortcuts
    editor_window.root.bind('<Control-Shift-V>', lambda e: show_capture_dialog())
    editor_window.root.bind('<Control-Alt-v>', lambda e: quick_clipboard_capture())
    editor_window.root.bind('<Control-Alt-V>', lambda e: quick_clipboard_capture())
    
    return True


# Test the integration
def test_capture_integration():
    """Test the text capture integration with a simple editor."""
    
    class MockEditor:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("Memento - Text Capture Test")
            self.root.geometry("600x400")
            
            # Create basic text widget
            self.text_widget = tk.Text(self.root, wrap=tk.WORD)
            self.text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Mock save status
            class MockSaveStatus:
                def mark_changed(self): pass
            
            class MockIdleSaver:
                def update(self, char_added=False): pass
            
            self.save_status = MockSaveStatus()
            self.idle_saver = MockIdleSaver()
            
            # Create menu bar
            self.menubar = Menu(self.root)
            self.root.config(menu=self.menubar)
            
        def _update_status_bar(self):
            pass
    
    # Create mock editor
    editor = MockEditor()
    
    # Add text capture functionality
    success = add_text_capture_to_editor(editor)
    
    if success:
        editor.text_widget.insert('1.0', 
            "Text Capture Integration Test\n\n"
            "This editor now has text capture functionality!\n\n"
            "Try using:\n"
            "• Tools → Capture Text from External App...\n"
            "• Tools → Quick Capture from Clipboard\n"
            "• Ctrl+Shift+V for full capture dialog\n"
            "• Ctrl+Alt+V for quick clipboard capture\n\n"
            "Select some text in another application and test the capture features.")
        
        editor.root.mainloop()
    else:
        messagebox.showerror("Error", "Failed to initialize text capture functionality")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    test_capture_integration()
