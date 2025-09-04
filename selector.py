#!/usr/bin/env python3
"""
Startup selector window for the Memento text editor.
Allows users to choose existing mementos or create new ones.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from storage import FileManager, MementoInfo


class StartupSelector:
    """Window for selecting existing mementos or creating new ones."""
    
    def __init__(self, parent=None):
        self.result = None  # Will hold the selected memento_id or None for new
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("Memento - Select or Create")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # Center the window
        self.root.transient(parent)
        self.root.grab_set()
        
        self._create_widgets()
        self._load_mementos()
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_widgets(self):
        """Create and layout the UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Choose a memento to open or create a new one:", 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Listbox with scrollbar for mementos
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Create treeview for better display
        self.memento_tree = ttk.Treeview(list_frame, columns=('first_line', 'modified'), show='tree headings')
        self.memento_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure columns
        self.memento_tree.column('#0', width=80, minwidth=60)
        self.memento_tree.column('first_line', width=300, minwidth=200)
        self.memento_tree.column('modified', width=150, minwidth=100)
        
        self.memento_tree.heading('#0', text='ID', anchor=tk.W)
        self.memento_tree.heading('first_line', text='Content Preview', anchor=tk.W)
        self.memento_tree.heading('modified', text='Last Modified', anchor=tk.W)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.memento_tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.memento_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Buttons
        self.open_button = ttk.Button(button_frame, text="Open Selected", command=self._on_open)
        self.open_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.new_button = ttk.Button(button_frame, text="Create New", command=self._on_new)
        self.new_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack(side=tk.RIGHT)
        
        # Initially disable open button
        self.open_button.configure(state=tk.DISABLED)
        
        # Bind double-click to open
        self.memento_tree.bind('<Double-1>', lambda e: self._on_open())
        self.memento_tree.bind('<<TreeviewSelect>>', self._on_selection_changed)
    
    def _load_mementos(self):
        """Load and display existing mementos."""
        mementos = FileManager.list_mementos()
        
        # Clear existing items
        for item in self.memento_tree.get_children():
            self.memento_tree.delete(item)
        
        if not mementos:
            # Show message if no mementos exist
            self.memento_tree.insert('', tk.END, text='No mementos found', values=('', ''))
            return
        
        # Add mementos to tree
        for memento in mementos:
            # Truncate first line if too long
            first_line = memento.first_line
            if len(first_line) > 50:
                first_line = first_line[:47] + "..."
            
            # Format date
            date_str = memento.last_modified.strftime("%Y-%m-%d %H:%M")
            
            self.memento_tree.insert('', tk.END, 
                                   text=f"#{memento.memento_id}",
                                   values=(first_line, date_str),
                                   tags=(str(memento.memento_id),))
    
    def _on_selection_changed(self, event=None):
        """Handle selection change in the treeview."""
        selection = self.memento_tree.selection()
        self.open_button.configure(state=tk.NORMAL if selection else tk.DISABLED)
    
    def _on_open(self):
        """Handle opening selected memento."""
        selection = self.memento_tree.selection()
        if not selection:
            return
        
        # Get the memento ID from the item text
        item = selection[0]
        item_text = self.memento_tree.item(item, 'text')
        
        if item_text.startswith('#'):
            try:
                memento_id = int(item_text[1:])
                self.result = memento_id
                self.root.destroy()
            except ValueError:
                pass
    
    def _on_new(self):
        """Handle creating new memento."""
        self.result = None  # None indicates new memento
        self.root.destroy()
    
    def _on_cancel(self):
        """Handle cancel/close."""
        self.result = "CANCEL"
        self.root.destroy()
    
    def show(self) -> Optional[int]:
        """Show the selector and return the result.
        
        Returns:
            int: memento_id to open
            None: create new memento
            "CANCEL": user cancelled
        """
        # Focus on the window
        self.root.focus_set()
        
        # If there are items, select the first one
        children = self.memento_tree.get_children()
        if children:
            first_item = children[0]
            # Only select if it's a real memento (has # in text)
            if self.memento_tree.item(first_item, 'text').startswith('#'):
                self.memento_tree.selection_set(first_item)
                self.memento_tree.focus(first_item)
                self._on_selection_changed()
        
        # Start the GUI event loop
        self.root.mainloop()
        
        return self.result


def show_selector(parent=None) -> Optional[int]:
    """Convenience function to show the selector.
    
    Returns:
        int: memento_id to open
        None: create new memento  
        "CANCEL": user cancelled
    """
    selector = StartupSelector(parent)
    return selector.show()
