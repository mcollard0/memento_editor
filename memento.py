#!/usr/bin/env python3
"""
Main application entry point for the Memento text editor.
Integrates all components and manages the application workflow.

Bootstraps shared MongoDB connection and EncryptionManager singletons.
"""

import sys;
import os;
import logging;
from tkinter import messagebox;

from constants import MEMENTO_ROOT, LOG_FILE, APP_NAME, VERSION, make_dirs_if_missing;
from storage import FileManager;
from selector import show_selector;
from editor import create_editor;


def setup_logging():
    """Setup logging to file."""
    make_dirs_if_missing( MEMENTO_ROOT );
    log_file = MEMENTO_ROOT / LOG_FILE;
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler( log_file ),
            logging.StreamHandler( sys.stdout )
        ]
    );
    
    logger = logging.getLogger( __name__ );
    logger.info( f"Starting {APP_NAME} v{VERSION}" );
    return logger;


def initialize_shared_services():
    """Initialize shared MongoDB connection and EncryptionManager singletons."""
    logger = logging.getLogger( __name__ );
    
    # Initialize MongoDB connection manager
    try:
        from mongodb_connection_manager import init_mongodb_connection;
        mongodb_uri = os.getenv( 'MONGODB_URI' ) or os.getenv( 'mongodb_uri' );
        
        if mongodb_uri:
            if init_mongodb_connection( mongodb_uri, "memento_storage" ):
                logger.info( "MongoDB connection manager initialized successfully" );
            else:
                logger.warning( "MongoDB connection initialization failed - using local storage only" );
        else:
            logger.info( "No MongoDB URI configured - using local storage only" );
    except Exception as e:
        logger.error( f"Error initializing MongoDB connection manager: {e}" );
    
    # Initialize shared EncryptionManager
    try:
        from encryption import init_encryption_manager;
        if init_encryption_manager( MEMENTO_ROOT ):
            logger.info( "EncryptionManager initialized successfully" );
        else:
            logger.warning( "EncryptionManager initialization failed - encryption features may be limited" );
    except Exception as e:
        logger.error( f"Error initializing EncryptionManager: {e}" );


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
    logger = setup_logging();
    
    try:
        # Ensure the .Memento directory exists
        make_dirs_if_missing( MEMENTO_ROOT );
        logger.info( f"Memento directory: {MEMENTO_ROOT}" );
        
        # Initialize shared services (MongoDB connection manager and EncryptionManager)
        initialize_shared_services();
        
        # Show the selector to start
        start_memento_selector();
        
    except KeyboardInterrupt:
        logger.info( "Application interrupted by user" );
    except Exception as e:
        logger.error( f"Unexpected error in main: {str(e)}" );
        messagebox.showerror( "Fatal Error", f"Unexpected error: {str(e)}" );
    finally:
        # Shutdown shared services
        try:
            from mongodb_connection_manager import MongoDBConnectionManager;
            MongoDBConnectionManager.shutdown();
        except Exception:
            pass;  # Ignore shutdown errors
        
        logger.info( "Application shutting down" );


if __name__ == "__main__":
    main()
