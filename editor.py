#!/usr/bin/env python3
"""
Main editor window for the Memento text editor application.
Provides the text editing interface with autosave functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import Optional
import pathlib

from constants import APP_NAME, CHAR_COUNT_THRESHOLD
from storage import FileManager
from autosave import IdleSaver, SaveStatus


class EditorWindow:
    """Main text editor window with autosave functionality."""
    
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.save_status = SaveStatus()
        self.is_closing = False
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - #{file_manager.memento_id}")
        self.root.geometry("800x600")
        self.root.minsize(400, 300)
        
        # Create autosave manager
        self.idle_saver = IdleSaver(self._save_callback, char_threshold=CHAR_COUNT_THRESHOLD)
        
        self._create_menu()
        self._create_widgets()
        self._load_content()
        self._setup_bindings()
        
        # Start autosave
        self.idle_saver.start()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        file_menu.add_command(label="Save to File...", command=self._save_to_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="New Memento", command=self._new_memento, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Memento...", command=self._open_memento, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        edit_menu.add_command(label="Auto Save (Ring Buffer)", command=self._force_save)
        edit_menu.add_separator()
        edit_menu.add_command(label="Undo", command=lambda: self.text_widget.edit_undo(), accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=lambda: self.text_widget.edit_redo(), accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=self._select_all, accelerator="Ctrl+A")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        help_menu.add_command(label="About Memento", command=self._show_about)
    
    def _create_widgets(self):
        """Create and layout the UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text widget
        self.text_widget = tk.Text(text_frame, 
                                  wrap=tk.WORD,
                                  undo=True,
                                  font=('Consolas', 11),
                                  bg='#fafafa',
                                  fg='#333333',
                                  insertbackground='#333333',
                                  selectbackground='#3399ff',
                                  relief=tk.FLAT,
                                  borderwidth=0,
                                  padx=10,
                                  pady=10)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, 
                                   text=self.save_status.get_status_text(),
                                   relief=tk.SUNKEN,
                                   anchor=tk.W,
                                   padding="5")
        self.status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Set focus to text widget
        self.text_widget.focus_set()
    
    def _setup_bindings(self):
        """Setup event bindings for the text widget."""
        # Bind key events to trigger autosave timer
        self.text_widget.bind('<KeyPress>', self._on_key_press)
        self.text_widget.bind('<Button-1>', self._on_text_change)
        self.text_widget.bind('<Control-Key>', self._on_text_change)
        self.text_widget.bind('<BackSpace>', self._on_text_change)
        self.text_widget.bind('<Delete>', self._on_text_change)
        
        # Bind Ctrl+S for save to file (includes ring buffer save)
        self.root.bind('<Control-s>', lambda e: self._save_to_file())
        self.root.bind('<Control-S>', lambda e: self._save_to_file())
        
        # Bind Ctrl+N for new memento
        self.root.bind('<Control-n>', lambda e: self._new_memento())
        self.root.bind('<Control-N>', lambda e: self._new_memento())
        
        # Bind Ctrl+O for open memento
        self.root.bind('<Control-o>', lambda e: self._open_memento())
        self.root.bind('<Control-O>', lambda e: self._open_memento())
        
        # Bind Ctrl+Q for exit
        self.root.bind('<Control-q>', lambda e: self._on_closing())
        self.root.bind('<Control-Q>', lambda e: self._on_closing())
        
        # Bind Ctrl+A for select all
        self.root.bind('<Control-a>', lambda e: self._select_all())
        self.root.bind('<Control-A>', lambda e: self._select_all())
    
    def _load_content(self):
        """Load the current content from the file manager."""
        content = self.file_manager.load_current_snapshot()
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.insert('1.0', content)
        
        # Mark as saved since we just loaded
        self.save_status.mark_saved()
        self._update_status_bar()
        
        # Reset undo/redo stack
        self.text_widget.edit_reset()
    
    def _on_key_press(self, event=None):
        """Handle key press events to detect character additions."""
        if self.is_closing:
            return
        
        # Check if this key press adds a character
        char_added = False
        if event and len(event.char) == 1 and event.char.isprintable():
            char_added = True
        
        self._on_text_change(event, char_added)
    
    def _on_text_change(self, event=None, char_added=False):
        """Handle text changes to trigger autosave and update status."""
        if self.is_closing:
            return
        
        # Mark as changed
        self.save_status.mark_changed()
        self._update_status_bar()
        
        # Trigger autosave timer with character count info
        self.idle_saver.update(char_added=char_added)
    
    def _save_callback(self):
        """Callback function for autosave."""
        if self.is_closing:
            return
        
        # Get current content
        content = self.text_widget.get('1.0', tk.END + '-1c')  # Exclude final newline
        
        try:
            # Update status to saving
            self.save_status.mark_saving()
            self._update_status_bar_thread_safe()
            
            # Perform save
            self.file_manager.write_snapshot(content)
            
            # Update status to saved
            self.save_status.mark_saved()
            self._update_status_bar_thread_safe()
            
        except Exception as e:
            # Handle save error
            self._show_error_thread_safe(f"Error saving: {str(e)}")
    
    def _force_save(self):
        """Force an immediate save."""
        self.idle_saver.force_save()
    
    def _save_to_file(self):
        """Save current content to ring buffer and export to a user-chosen file."""
        try:
            # First, force save to ring buffer
            self._force_save()
            
            # Get current content
            content = self.text_widget.get('1.0', tk.END + '-1c')
            
            # Show file save dialog
            file_path = filedialog.asksaveasfilename(
                title="Save Memento to File",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Markdown files", "*.md"),
                    ("All files", "*.*")
                ],
                initialdir=str(pathlib.Path.home()),
                confirmoverwrite=True
            )
            
            if file_path:  # User didn't cancel
                # Write to the chosen file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Update status to show successful export
                self.save_status.mark_saved()
                self._update_status_bar()
                
                # Show success message
                messagebox.showinfo(
                    "Export Successful", 
                    f"Memento #{self.file_manager.memento_id} exported to:\n{file_path}"
                )
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save file:\n{str(e)}")
    
    def _select_all(self):
        """Select all text in the editor."""
        self.text_widget.tag_add(tk.SEL, '1.0', tk.END)
        self.text_widget.mark_set(tk.INSERT, '1.0')
        self.text_widget.see(tk.INSERT)
    
    def _show_about(self):
        """Show about dialog."""
        from constants import APP_NAME, VERSION
        
        about_text = f"""{APP_NAME} v{VERSION}

A simple, elegant text editor with automatic saving and version history through ring buffers.

Features:
• Automatic saving when you stop typing OR after 50 characters
• Ring buffer versioning (3-50 save points)
• Multiple mementos (documents)
• Export to external files with Ctrl+S
• Cross-platform compatibility

Data stored in: ~/.Memento/

Keyboard Shortcuts:
Ctrl+S - Save to ring buffer AND export to file
Ctrl+N - New memento
Ctrl+O - Open memento selector
Ctrl+Q - Exit
Ctrl+A - Select all
Ctrl+Z - Undo
Ctrl+Y - Redo"""
        
        messagebox.showinfo("About Memento", about_text)
    
    def _update_status_bar(self):
        """Update the status bar text."""
        self.status_bar.config(text=self.save_status.get_status_text())
    
    def _update_status_bar_thread_safe(self):
        """Thread-safe status bar update."""
        if self.is_closing:
            return
        try:
            self.root.after_idle(self._update_status_bar)
        except tk.TclError:
            # Window may have been destroyed
            pass
    
    def _show_error_thread_safe(self, message: str):
        """Thread-safe error message display."""
        if self.is_closing:
            return
        try:
            self.root.after_idle(lambda: messagebox.showerror("Save Error", message))
        except tk.TclError:
            # Window may have been destroyed
            pass
    
    def _new_memento(self):
        """Create a new memento."""
        try:
            # Force save current memento
            self._force_save()
            
            # Import here to avoid circular imports
            from app import start_new_memento
            
            # Close current window
            self._close_without_confirmation()
            
            # Start new memento
            start_new_memento()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error creating new memento: {str(e)}")
    
    def _open_memento(self):
        """Open memento selector."""
        try:
            # Force save current memento
            self._force_save()
            
            # Import here to avoid circular imports  
            from app import start_memento_selector
            
            # Close current window
            self._close_without_confirmation()
            
            # Show selector
            start_memento_selector()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error opening memento selector: {str(e)}")
    
    def _on_closing(self):
        """Handle window close event."""
        if self.is_closing:
            return
        
        self.is_closing = True
        
        # Stop autosave
        self.idle_saver.stop()
        
        # Force final save
        try:
            content = self.text_widget.get('1.0', tk.END + '-1c')
            self.file_manager.write_snapshot(content)
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving before close: {str(e)}")
        
        # Close the window
        self.root.destroy()
    
    def _close_without_confirmation(self):
        """Close the window without save confirmation."""
        self.is_closing = True
        self.idle_saver.stop()
        self.root.destroy()
    
    def run(self):
        """Start the main event loop."""
        try:
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Application Error", f"Unexpected error: {str(e)}")
        finally:
            # Ensure autosave is stopped
            if hasattr(self, 'idle_saver'):
                self.idle_saver.stop()


def create_editor(file_manager: FileManager) -> EditorWindow:
    """Create and return a new editor window."""
    return EditorWindow(file_manager)
