#!/usr/bin/env python3
"""
Main application entry point for the memento text editor.
Integrates all components and manages the application workflow.
"""

import sys
import logging
from tkinter import messagebox

from constants import MEMENTO_ROOT, LOG_FILE, APP_NAME, VERSION, make_dirs_if_missing
from storage import FileManager
from selector import show_selector
from editor import create_editor


def setup_logging():
    """Setup logging to file."""
    make_dirs_if_missing(MEMENTO_ROOT)
    log_file = MEMENTO_ROOT / LOG_FILE
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {APP_NAME} v{VERSION}")
    return logger


def start_memento_selector():
    """Show the memento selector and handle the result."""
    logger = logging.getLogger(__name__)
    
    try:
        result = show_selector()
        
        if result == "CANCEL":
            logger.info("User cancelled selection")
            return
        
        if result is None:
            # Create new memento
            logger.info("Creating new memento")
            start_new_memento()
        else:
            # Open existing memento
            logger.info(f"Opening memento {result}")
            start_existing_memento(result)
            
    except Exception as e:
        logger.error(f"Error in memento selector: {str(e)}")
        messagebox.showerror("Error", f"Error showing memento selector: {str(e)}")


def start_new_memento():
    """Create and start editing a new memento."""
    logger = logging.getLogger(__name__)
    
    try:
        # Create new memento
        file_manager = FileManager.create_new_memento()
        logger.info(f"Created new memento with ID: {file_manager.memento_id}")
        
        # Start editor
        editor = create_editor(file_manager)
        editor.run()
        
    except Exception as e:
        logger.error(f"Error creating new memento: {str(e)}")
        messagebox.showerror("Error", f"Error creating new memento: {str(e)}")


def start_existing_memento(memento_id: int):
    """Load and start editing an existing memento."""
    logger = logging.getLogger(__name__)
    
    try:
        # Load existing memento
        file_manager = FileManager.load_memento(memento_id)
        
        if file_manager is None:
            raise Exception(f"Could not load memento {memento_id}")
        
        logger.info(f"Loaded memento {memento_id}")
        
        # Start editor
        editor = create_editor(file_manager)
        editor.run()
        
    except Exception as e:
        logger.error(f"Error loading memento {memento_id}: {str(e)}")
        messagebox.showerror("Error", f"Error loading memento {memento_id}: {str(e)}")


def main():
    """Main application entry point."""
    logger = setup_logging()
    
    try:
        # Ensure the .memento directory exists
        make_dirs_if_missing(MEMENTO_ROOT)
        logger.info(f"memento directory: {MEMENTO_ROOT}")
        
        # Show the selector to start
        start_memento_selector()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}")
        messagebox.showerror("Fatal Error", f"Unexpected error: {str(e)}")
    finally:
        logger.info("Application shutting down")


if __name__ == "__main__":
    main()
