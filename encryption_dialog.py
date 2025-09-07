#!/usr/bin/env python3
"""
Encryption dialog for memento.
Provides UI for entering passphrases and managing encryption settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional


class PassphraseDialog:
    """Dialog for entering encryption passphrase."""
    
    def __init__(self, parent, title: str, message: str, is_creation: bool = False, 
                 show_size_limit: bool = False, max_size_mb: int = 40):
        self.parent = parent
        self.result = None
        self.is_creation = is_creation
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("650x700" if show_size_limit else "600x600")
        self.dialog.resizable(True, True)
        self.dialog.minsize(550, 500)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self._center_dialog()
        
        self._create_widgets(message, show_size_limit, max_size_mb)
        
        # Bind Enter/Escape keys
        self.dialog.bind('<Return>', self._on_ok)
        self.dialog.bind('<Escape>', self._on_cancel)
        
        # Focus on first password entry
        self.password_entry.focus_set()
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent geometry
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _create_widgets(self, message: str, show_size_limit: bool, max_size_mb: int):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="40")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon and message
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Use a lock symbol 
        icon_label = ttk.Label(icon_frame, text="🔒", font=('Arial', 24))
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        message_label = ttk.Label(icon_frame, text=message, font=('Arial', 10), wraplength=400)
        message_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Size limit warning if needed
        if show_size_limit:
            size_frame = ttk.Frame(main_frame)
            size_frame.pack(fill=tk.X, pady=(0, 25))
            
            size_label = ttk.Label(
                size_frame, 
                text=f"⚠️ MongoDB Storage Limit: Using encryption with Brotli compression "
                     f"has an approximate limit of {max_size_mb}MB of uncompressed text.",
                font=('Arial', 9),
                foreground='orange',
                wraplength=450
            )
            size_label.pack()
        
        # Password fields
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Main password
        ttk.Label(fields_frame, text="Passphrase:", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(10, 8))
        self.password_entry = ttk.Entry(fields_frame, show="*", width=60, font=('Arial', 14))
        self.password_entry.pack(fill=tk.X, pady=(5, 25), ipady=12)
        
        # Confirmation password (only for creation)
        if self.is_creation:
            ttk.Label(fields_frame, text="Confirm Passphrase:", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(10, 8))
            self.confirm_entry = ttk.Entry(fields_frame, show="*", width=60, font=('Arial', 14))
            self.confirm_entry.pack(fill=tk.X, pady=(5, 25), ipady=12)
            
            # Strength indicator
            self.strength_label = ttk.Label(fields_frame, text="", foreground="gray")
            self.strength_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Bind to check strength
            self.password_entry.bind('<KeyRelease>', self._check_password_strength)
        
        # Show/Hide password checkbox
        self.show_password = tk.BooleanVar()
        show_check = ttk.Checkbutton(
            fields_frame, 
            text="Show passphrase", 
            variable=self.show_password,
            command=self._toggle_password_visibility
        )
        show_check.pack(anchor=tk.W, pady=(0, 25))
        
        # Help text
        help_frame = ttk.Frame(main_frame)
        help_frame.pack(fill=tk.X, pady=(0, 30))
        
        help_text = (
            "💡 Tips for a strong passphrase:\\n"
            "• Use at least 12 characters\\n"
            "• Include uppercase, lowercase, numbers, and symbols\\n"
            "• Avoid dictionary words or personal information\\n"
            "• Consider using a passphrase like 'Coffee#Mug$Dancing7!'"
        )
        
        help_label = ttk.Label(
            help_frame, 
            text=help_text, 
            font=('Arial', 9),
            foreground='gray',
            wraplength=450
        )
        help_label.pack()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(40, 20))
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._on_cancel, width=15)
        cancel_btn.pack(side=tk.RIGHT, padx=(20, 0), pady=15, ipadx=25, ipady=8)
        
        ok_btn = ttk.Button(button_frame, text="Create Passphrase" if self.is_creation else "Unlock", command=self._on_ok, width=20)
        ok_btn.pack(side=tk.RIGHT, pady=15, ipadx=25, ipady=8)
    
    def _toggle_password_visibility(self):
        """Toggle password visibility."""
        show = "" if self.show_password.get() else "*"
        self.password_entry.config(show=show)
        if hasattr(self, 'confirm_entry'):
            self.confirm_entry.config(show=show)
    
    def _check_password_strength(self, event=None):
        """Check and display password strength."""
        if not hasattr(self, 'strength_label'):
            return
            
        password = self.password_entry.get()
        strength, color, message = self._calculate_password_strength(password)
        
        self.strength_label.config(text=f"Strength: {message}", foreground=color)
    
    def _calculate_password_strength(self, password: str) -> tuple:
        """Calculate password strength."""
        if len(password) == 0:
            return 0, "gray", ""
        
        score = 0
        feedback = []
        
        # Length scoring
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            feedback.append("too short")
        
        # Character variety
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(not c.isalnum() for c in password)
        
        variety = sum([has_lower, has_upper, has_digit, has_symbol])
        score += variety
        
        if variety < 3:
            feedback.append("needs more variety")
        
        # Determine strength level
        if score >= 5:
            return score, "green", "Strong"
        elif score >= 3:
            return score, "orange", "Medium" + (f" ({', '.join(feedback)})" if feedback else "")
        else:
            return score, "red", "Weak" + (f" ({', '.join(feedback)})" if feedback else "")
    
    def _on_ok(self, event=None):
        """Handle OK button."""
        password = self.password_entry.get().strip()
        
        # Check if password is empty
        if not password:
            self.result = None
            self.dialog.destroy()
            return
        
        # For creation, check confirmation
        if self.is_creation:
            confirm = self.confirm_entry.get().strip()
            if password != confirm:
                messagebox.showerror(
                    "Password Mismatch",
                    "The passphrases do not match. Please try again.",
                    parent=self.dialog
                )
                self.confirm_entry.delete(0, tk.END)
                self.confirm_entry.focus_set()
                return
            
            # Check minimum strength for creation
            strength, _, _ = self._calculate_password_strength(password)
            if strength < 3:
                response = messagebox.askyesno(
                    "Weak Passphrase",
                    "The passphrase you entered is considered weak. "
                    "A weak passphrase may be easier to crack.\\n\\n"
                    "Do you want to use this passphrase anyway?",
                    parent=self.dialog
                )
                if not response:
                    return
        
        self.result = password
        self.dialog.destroy()
    
    def _on_cancel(self, event=None):
        """Handle Cancel button."""
        self.result = None
        self.dialog.destroy()
    
    def show(self) -> Optional[str]:
        """Show the dialog and return the result."""
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result


def get_passphrase_for_creation(parent, show_size_limit: bool = False, max_size_mb: int = 40) -> Optional[str]:
    """Show dialog to create new passphrase."""
    dialog = PassphraseDialog(
        parent,
        "Create Encryption Passphrase",
        "Create a strong passphrase to protect your memento with encryption.\\n"
        "This passphrase will be required to access your encrypted content.",
        is_creation=True,
        show_size_limit=show_size_limit,
        max_size_mb=max_size_mb
    )
    return dialog.show()


def get_passphrase_for_decryption(parent) -> Optional[str]:
    """Show dialog to enter existing passphrase."""
    dialog = PassphraseDialog(
        parent,
        "Enter Encryption Passphrase",
        "Enter your passphrase to decrypt and access this memento.",
        is_creation=False
    )
    return dialog.show()
