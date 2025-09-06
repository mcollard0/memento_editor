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

from constants import APP_NAME, MEMENTO_ROOT
from storage import FileManager
from autosave import IdleSaver, SaveStatus

# Optional encryption support
try:
    from encryption import EncryptionManager, get_missing_dependencies
    from encryption_dialog import get_passphrase_for_creation, get_passphrase_for_decryption
    HAS_ENCRYPTION = True
except ImportError:
    HAS_ENCRYPTION = False


class EditorWindow:
    """Main text editor window with autosave functionality."""
    
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.save_status = SaveStatus()
        self.is_closing = False
        
        # Initialize encryption manager if available
        self.encryption_manager = None
        self.current_passphrase = None
        if HAS_ENCRYPTION:
            self.encryption_manager = EncryptionManager(MEMENTO_ROOT)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - #{file_manager.memento_id}")
        self.root.geometry("800x600")
        self.root.minsize(400, 300)
        
        # Create autosave manager
        self.idle_saver = IdleSaver(self._save_callback)
        
        self._create_menu()
        self._create_widgets()
        self._load_content()
        self._setup_bindings()
        
        # Start autosave
        self.idle_saver.start()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _show_encrypted_placeholder(self):
        """Show placeholder content for encrypted memento without passphrase."""
        self.is_encrypted_content = True
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete('1.0', tk.END)
        
        placeholder_text = (
            "🔒 ENCRYPTED MEMENTO\n\n"
            "This memento is encrypted and requires a passphrase to view.\n\n"
            "📌 TEST PASSPHRASE: bysextel\n\n"
            "To decrypt:\n"
            "• Press Ctrl+D, or\n"
            "• Use Encryption menu → Decrypt Content\n\n"
            "Once decrypted, you can edit and it will auto-save to MongoDB with encryption."
        )
        
        self.text_widget.insert('1.0', placeholder_text)
        self.text_widget.configure(state=tk.DISABLED)
        
        # Bind Ctrl+D to unlock
        self.root.bind('<Control-d>', lambda e: self._prompt_for_passphrase(reload_content=True))
        self.root.bind('<Control-D>', lambda e: self._prompt_for_passphrase(reload_content=True))
    
    def _prompt_for_passphrase(self, reload_content=True):
        """Prompt user for passphrase to decrypt content."""
        if not self.file_manager.is_encrypted():
            return False
        
        try:
            from tkinter import simpledialog
            import logging
            logger = logging.getLogger(__name__)
            
            passphrase = simpledialog.askstring(
                "Enter Passphrase",
                "Enter passphrase to decrypt this memento:",
                show='*',
                parent=self.root
            )
            
            if passphrase:
                logger.info(f"Attempting to verify passphrase for memento {self.file_manager.memento_id}")
                
                if self.file_manager.verify_passphrase(passphrase):
                    logger.info("Passphrase verification successful")
                    self.current_passphrase = passphrase
                    self.file_manager._prepare_aes_key(passphrase)
                    if reload_content:
                        logger.info("Reloading content after successful decryption")
                        self._load_content()  # Reload with passphrase
                    return True
                else:  # Wrong passphrase
                    logger.warning("Passphrase verification failed")
                    messagebox.showerror(
                        "Invalid Passphrase",
                        "The passphrase you entered is incorrect.\n\nHint: The test passphrase is 'bysextel'"
                    )
                    return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during passphrase prompt: {e}")
            messagebox.showerror(
                "Error",
                f"Error opening passphrase dialog: {str(e)}"
            )
            return False
        
        return False  # User cancelled or no passphrase
    
    def _create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        file_menu.add_command(label="Save to File...", command=self._save_to_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        
        # Encryption submenu (if available)
        if HAS_ENCRYPTION and self.encryption_manager and self.encryption_manager.has_encryption_support:
            encryption_menu = tk.Menu(file_menu, tearoff=0)
            file_menu.add_cascade(label="Encryption", menu=encryption_menu)
            
            encryption_menu.add_command(label="Decrypt Content...", command=self._prompt_for_passphrase)
            encryption_menu.add_separator()
            encryption_menu.add_command(label="Enable Encryption...", command=self._enable_encryption)
            encryption_menu.add_command(label="Change Passphrase...", command=self._change_passphrase)
            encryption_menu.add_separator()
            encryption_menu.add_command(label="Disable Encryption", command=self._disable_encryption)
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
        import logging
        logger = logging.getLogger(__name__)
        
        self.is_encrypted_content = False
        logger.info(f"Loading content for memento {self.file_manager.memento_id}")
        
        try:
            # Check if memento is encrypted
            if self.file_manager.is_encrypted():
                logger.info("Memento is encrypted")
                if not self.current_passphrase:
                    # Show placeholder immediately - user can click to decrypt
                    logger.info("No passphrase available - showing placeholder")
                    self._show_encrypted_placeholder()
                    return
                
                # We have the passphrase, prepare the key
                logger.info("Preparing AES key with passphrase")
                self.file_manager._prepare_aes_key(self.current_passphrase)
            
            # Load content (will be decrypted automatically if encrypted)
            logger.info("Loading current snapshot")
            content = self.file_manager.load_current_snapshot()
            logger.info(f"Loaded content: {len(content) if content else 0} characters")
            
            # Handle None content gracefully
            if content is None:
                logger.warning("Content is None - using empty string")
                content = ""
            
            # Clear and update text widget
            logger.info("Updating text widget")
            self.text_widget.configure(state=tk.NORMAL)  # Ensure it's editable first
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)
            
            # Update window title to show encryption status
            self._update_window_title()
            
            # Mark as saved since we just loaded
            self.save_status.mark_saved()
            self._update_status_bar()
            
            # Reset undo/redo stack
            self.text_widget.edit_reset()
            
            # Ensure text widget can be edited
            self.text_widget.focus_set()
            logger.info("Content loading completed successfully")
            
        except Exception as e:
            logger.error(f"Error loading content: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            messagebox.showerror(
                "Load Error",
                f"Failed to load memento content: {str(e)}"
            )
            # Don't destroy the window - let user try again
            return
    
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
• Adaptive auto-saving: starts at 2 characters, grows to 64 based on typing patterns
• Idle detection: saves after 1.5 seconds of inactivity
• Ring buffer versioning (3-50 save points)
• Multiple mementos (documents)
• Export to external files with Ctrl+S
• Cross-platform compatibility

Data stored in: ~/.Memento/

Dynamic Thresholds: 2, 4, 8, 16, 32, 64 characters
Adapts based on your average typing between pauses

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
    
    def _enable_encryption(self):
        """Enable encryption for this memento."""
        if not self.encryption_manager or not self.encryption_manager.has_encryption_support:
            missing_deps = get_missing_dependencies()
            messagebox.showerror(
                "Encryption Not Available",
                f"Encryption requires additional packages: {', '.join(missing_deps)}\n\n"
                f"Install with: pip install {' '.join(missing_deps)}"
            )
            return
        
        # Check if already encrypted
        if self.file_manager.is_encrypted():
            messagebox.showinfo(
                "Already Encrypted",
                "This memento is already encrypted."
            )
            return
        
        try:
            # Get passphrase from user
            passphrase = get_passphrase_for_creation(
                self.root,
                show_size_limit=self.encryption_manager.has_mongodb_support,
                max_size_mb=self.encryption_manager.estimated_max_size_mb
            )
            
            if not passphrase:  # User cancelled or entered blank
                return
            
            # Force save current content to ensure it's up to date
            self._force_save()
            
            # Enable encryption in file manager
            self.file_manager.enable_encryption(passphrase)
            
            # Store passphrase for this session
            self.current_passphrase = passphrase
            
            # Update window title to show encryption status
            self._update_window_title()
            
            messagebox.showinfo(
                "Encryption Enabled",
                "Encryption has been enabled for this memento.\n"
                "Your content is now protected and will be compressed before storage."
            )
            
        except Exception as e:
            messagebox.showerror("Encryption Error", f"Failed to enable encryption: {str(e)}")
    
    def _change_passphrase(self):
        """Change the encryption passphrase."""
        if not self.encryption_manager or not self.encryption_manager.has_encryption_support:
            messagebox.showerror("Encryption Not Available", "Encryption is not available.")
            return
        
        if not self.file_manager.is_encrypted():
            messagebox.showinfo(
                "Not Encrypted",
                "This memento is not encrypted. Enable encryption first."
            )
            return
        
        try:
            # Get current passphrase if not already known
            if not self.current_passphrase:
                current_passphrase = get_passphrase_for_decryption(self.root)
                if not current_passphrase:
                    return
                
                # Verify current passphrase
                if not self.file_manager.verify_passphrase(current_passphrase):
                    messagebox.showerror("Invalid Passphrase", "The current passphrase is incorrect.")
                    return
                
                self.current_passphrase = current_passphrase
            
            # Get new passphrase
            new_passphrase = get_passphrase_for_creation(
                self.root,
                show_size_limit=self.encryption_manager.has_mongodb_support,
                max_size_mb=self.encryption_manager.estimated_max_size_mb
            )
            
            if not new_passphrase:
                return
            
            # Change passphrase in file manager
            self.file_manager.change_passphrase(self.current_passphrase, new_passphrase)
            self.current_passphrase = new_passphrase
            
            messagebox.showinfo(
                "Passphrase Changed",
                "The encryption passphrase has been successfully changed."
            )
            
        except Exception as e:
            messagebox.showerror("Passphrase Change Error", f"Failed to change passphrase: {str(e)}")
    
    def _disable_encryption(self):
        """Disable encryption for this memento."""
        if not self.file_manager.is_encrypted():
            messagebox.showinfo(
                "Not Encrypted",
                "This memento is not encrypted."
            )
            return
        
        # Confirm with user
        response = messagebox.askyesno(
            "Disable Encryption",
            "Are you sure you want to disable encryption?\n\n"
            "This will decrypt your content and store it in plain text.\n"
            "This action cannot be undone.",
            default='no'
        )
        
        if not response:
            return
        
        try:
            # Get current passphrase if not already known
            if not self.current_passphrase:
                current_passphrase = get_passphrase_for_decryption(self.root)
                if not current_passphrase:
                    return
                
                # Verify current passphrase
                if not self.file_manager.verify_passphrase(current_passphrase):
                    messagebox.showerror("Invalid Passphrase", "The current passphrase is incorrect.")
                    return
                
                self.current_passphrase = current_passphrase
            
            # Disable encryption in file manager
            self.file_manager.disable_encryption(self.current_passphrase)
            self.current_passphrase = None
            
            # Update window title
            self._update_window_title()
            
            messagebox.showinfo(
                "Encryption Disabled",
                "Encryption has been disabled. Your content is now stored in plain text."
            )
            
        except Exception as e:
            messagebox.showerror("Disable Encryption Error", f"Failed to disable encryption: {str(e)}")
    
    def _update_window_title(self):
        """Update the window title to reflect encryption status."""
        base_title = f"{APP_NAME} - #{self.file_manager.memento_id}"
        if self.file_manager.is_encrypted():
            self.root.title(f"{base_title} 🔒")
        else:
            self.root.title(base_title)
    
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
