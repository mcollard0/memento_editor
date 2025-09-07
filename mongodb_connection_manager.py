#!/usr/bin/env python3
"""
MongoDB Connection Manager for Memento Editor.

Provides a singleton connection manager that:
- Opens one connection per process and reuses it for all document operations
- Sets 1-hour session timeout with automatic reconnection
- Gracefully handles connection drops and network issues
- Falls back to local storage on persistent connection failures

Design follows user preferences: spaces in brackets/braces and semicolons on statements.
"""

import os;
import time;
import logging;
import threading;
from typing import Optional, Callable, Any;
from datetime import datetime, timedelta;

# Optional dependencies - graceful degradation if not available
try:
    import pymongo;
    from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure;
    HAS_PYMONGO = True;
except ImportError:
    HAS_PYMONGO = False;
    pymongo = None;

logger = logging.getLogger( __name__ );


class ConnectionUnavailableError( Exception ):
    """Raised when MongoDB connection cannot be established after retries."""
    pass;


class MongoDBConnectionManager:
    """Singleton MongoDB connection manager with persistent connections and auto-reconnect."""
    
    # Class-level variables for singleton behavior
    _instance = None;
    _client = None; 
    _db = None;
    _uri = None;
    _db_name = None;
    _last_ping_time = None;
    _heartbeat_thread = None;
    _is_shutting_down = False;
    _connection_lock = threading.RLock();
    
    # Connection configuration (1 hour timeout as requested)
    IDLE_TIMEOUT_MS = 60 * 60 * 1000;  # 1 hour in milliseconds
    HEARTBEAT_INTERVAL_SEC = 5 * 60;   # 5 minutes
    CONNECTION_TIMEOUT_MS = 10000;     # 10 seconds
    SERVER_SELECTION_TIMEOUT_MS = 5000; # 5 seconds
    MAX_RECONNECT_ATTEMPTS = 3;
    BACKOFF_BASE_DELAY_SEC = 1.0;      # Exponential backoff starting delay
    
    def __init__( self ):
        """Private constructor - use init() class method instead."""
        if MongoDBConnectionManager._instance is not None:
            raise RuntimeError( "MongoDBConnectionManager is a singleton - use init() instead" );
        MongoDBConnectionManager._instance = self;
    
    @classmethod
    def init( cls, mongodb_uri: str, database_name: str = "memento_storage" ) -> bool:
        """
        Initialize the singleton connection manager.
        
        Args:
            mongodb_uri: MongoDB connection URI
            database_name: Database name (default: memento_storage)
            
        Returns:
            True if connection established successfully, False otherwise
        """
        if not HAS_PYMONGO:
            logger.warning( "PyMongo not available - MongoDB features disabled" );
            return False;
        
        if not mongodb_uri:
            logger.info( "No MongoDB URI provided - using local storage only" );
            return False;
        
        with cls._connection_lock:
            # Create singleton instance if it doesn't exist
            if cls._instance is None:
                cls._instance = MongoDBConnectionManager();
            
            # Store connection parameters
            cls._uri = mongodb_uri;
            cls._db_name = database_name;
            
            # Attempt initial connection
            success = cls._establish_connection();
            
            if success:
                # Start heartbeat monitoring thread
                cls._start_heartbeat_monitor();
                logger.info( f"MongoDB connection established to database '{database_name}'" );
            else:
                logger.error( "Failed to establish initial MongoDB connection" );
                
            return success;
    
    @classmethod
    def get_client( cls ) -> Optional[ "pymongo.MongoClient" ]:
        """
        Get the shared MongoDB client, ensuring connection is alive.
        
        Returns:
            MongoClient instance if available, None otherwise
        """
        if not cls._instance or not HAS_PYMONGO:
            return None;
        
        with cls._connection_lock:
            if not cls._ensure_connection_alive():
                return None;
            return cls._client;
    
    @classmethod  
    def get_database( cls ) -> Optional[ Any ]:
        """
        Get the shared MongoDB database, ensuring connection is alive.
        
        Returns:
            Database instance if available, None otherwise
        """
        if not cls._instance or not HAS_PYMONGO:
            return None;
            
        with cls._connection_lock:
            if not cls._ensure_connection_alive():
                return None;
            return cls._db;
    
    @classmethod
    def get_collection( cls, collection_name: str = "mementos" ) -> Optional[ Any ]:
        """
        Get a collection from the shared database.
        
        Args:
            collection_name: Name of the collection (default: mementos)
            
        Returns:
            Collection instance if available, None otherwise
        """
        db = cls.get_database();
        if db is None:
            return None;
        return db[ collection_name ];
    
    @classmethod
    def is_connected( cls ) -> bool:
        """Check if MongoDB connection is currently active."""
        if not cls._instance or not HAS_PYMONGO:
            return False;
        
        with cls._connection_lock:
            return cls._client is not None and cls._db is not None;
    
    @classmethod
    def shutdown( cls ):
        """Clean shutdown of the connection manager."""
        with cls._connection_lock:
            cls._is_shutting_down = True;
            
            # Stop heartbeat monitor
            if cls._heartbeat_thread and cls._heartbeat_thread.is_alive():
                cls._heartbeat_thread.join( timeout=2.0 );
            
            # Close MongoDB connection
            if cls._client:
                try:
                    cls._client.close();
                    logger.info( "MongoDB connection closed" );
                except Exception as e:
                    logger.warning( f"Error closing MongoDB connection: {e}" );
                finally:
                    cls._client = None;
                    cls._db = None;
    
    @classmethod
    def _establish_connection( cls ) -> bool:
        """
        Establish MongoDB connection with configured timeout settings.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not HAS_PYMONGO or not cls._uri:
            return False;
        
        try:
            # Create client with 1-hour idle timeout and other settings
            cls._client = pymongo.MongoClient(
                cls._uri,
                serverSelectionTimeoutMS=cls.SERVER_SELECTION_TIMEOUT_MS,
                connectTimeoutMS=cls.CONNECTION_TIMEOUT_MS,
                maxIdleTimeMS=cls.IDLE_TIMEOUT_MS,
                # Additional reliability settings
                retryWrites=True,
                retryReads=True,
                heartbeatFrequencyMS=30000,  # 30 seconds
                socketTimeoutMS=None,        # No socket timeout
                waitQueueTimeoutMS=10000     # 10 seconds queue timeout
            );
            
            # Test connection and get database
            cls._client.server_info();  # This will raise exception if connection fails
            cls._db = cls._client[ cls._db_name ];
            
            # Perform test read/write to verify database access
            test_doc = { "_test": True, "timestamp": time.time() };
            collection = cls._db.mementos;
            result = collection.insert_one( test_doc );
            collection.delete_one( { "_id": result.inserted_id } );
            
            cls._last_ping_time = time.time();
            return True;
            
        except Exception as e:
            logger.error( f"Failed to establish MongoDB connection: {e}" );
            cls._client = None;
            cls._db = None;
            return False;
    
    @classmethod
    def _ensure_connection_alive( cls ) -> bool:
        """
        Ensure the connection is alive, reconnect if necessary.
        
        Returns:
            True if connection is alive or successfully reconnected, False otherwise
        """
        if cls._is_shutting_down:
            return False;
        
        # Quick check if we have a client
        if cls._client is None or cls._db is None:
            logger.info( "No active connection - attempting to reconnect" );
            return cls._reconnect_with_backoff();
        
        # Check if we need to ping (every 30 seconds max)
        current_time = time.time();
        if ( cls._last_ping_time is None or 
             current_time - cls._last_ping_time > 30 ):
            
            try:
                # Quick ping to check connection
                cls._client.admin.command( 'ping' );
                cls._last_ping_time = current_time;
                return True;
            except Exception as e:
                logger.warning( f"Connection ping failed: {e} - reconnecting" );
                return cls._reconnect_with_backoff();
        
        return True;  # Recent successful ping, assume connection is good
    
    @classmethod
    def _reconnect_with_backoff( cls ) -> bool:
        """
        Attempt to reconnect with exponential backoff.
        
        Returns:
            True if reconnection successful, False if all attempts failed
        """
        for attempt in range( cls.MAX_RECONNECT_ATTEMPTS ):
            if cls._is_shutting_down:
                return False;
            
            if attempt > 0:
                # Exponential backoff delay
                delay = cls.BACKOFF_BASE_DELAY_SEC * ( 2 ** ( attempt - 1 ) );
                logger.info( f"Reconnect attempt {attempt + 1}/{cls.MAX_RECONNECT_ATTEMPTS} after {delay}s delay" );
                time.sleep( delay );
            else:
                logger.info( f"Reconnect attempt {attempt + 1}/{cls.MAX_RECONNECT_ATTEMPTS}" );
            
            # Clean up old connection
            if cls._client:
                try:
                    cls._client.close();
                except Exception:
                    pass;  # Ignore cleanup errors
                cls._client = None;
                cls._db = None;
            
            # Attempt new connection
            if cls._establish_connection():
                logger.info( f"Reconnection successful on attempt {attempt + 1}" );
                return True;
        
        logger.error( f"Reconnection failed after {cls.MAX_RECONNECT_ATTEMPTS} attempts" );
        return False;
    
    @classmethod
    def _start_heartbeat_monitor( cls ):
        """Start background thread to monitor connection health."""
        if cls._heartbeat_thread and cls._heartbeat_thread.is_alive():
            return;  # Already running
        
        def heartbeat_loop():
            """Background thread function for connection monitoring."""
            while not cls._is_shutting_down:
                try:
                    time.sleep( cls.HEARTBEAT_INTERVAL_SEC );
                    
                    if cls._is_shutting_down:
                        break;
                    
                    with cls._connection_lock:
                        if cls._client and cls._db:
                            try:
                                # Ping the database
                                cls._client.admin.command( 'ping' );
                                cls._last_ping_time = time.time();
                            except Exception as e:
                                logger.warning( f"Heartbeat ping failed: {e}" );
                                # Connection will be re-established on next use
                                
                except Exception as e:
                    logger.error( f"Error in heartbeat monitor: {e}" );
        
        cls._heartbeat_thread = threading.Thread( target=heartbeat_loop, daemon=True );
        cls._heartbeat_thread.start();
        logger.debug( "Heartbeat monitor started" );


# Utility functions for backward compatibility and convenience

def get_mongodb_client() -> Optional[ "pymongo.MongoClient" ]:
    """Get the shared MongoDB client (convenience function)."""
    return MongoDBConnectionManager.get_client();


def get_mongodb_database() -> Optional[ Any ]:
    """Get the shared MongoDB database (convenience function)."""
    return MongoDBConnectionManager.get_database();


def get_mongodb_collection( collection_name: str = "mementos" ) -> Optional[ Any ]:
    """Get a MongoDB collection (convenience function)."""
    return MongoDBConnectionManager.get_collection( collection_name );


def is_mongodb_available() -> bool:
    """Check if MongoDB connection is available (convenience function)."""
    return MongoDBConnectionManager.is_connected();


def init_mongodb_connection( mongodb_uri: str = None, database_name: str = "memento_storage" ) -> bool:
    """
    Initialize MongoDB connection (convenience function).
    
    Args:
        mongodb_uri: MongoDB URI (if None, uses MONGODB_URI env var)
        database_name: Database name
        
    Returns:
        True if connection established, False otherwise
    """
    if mongodb_uri is None:
        mongodb_uri = os.getenv( 'MONGODB_URI' ) or os.getenv( 'mongodb_uri' );
    
    if not mongodb_uri:
        return False;
    
    return MongoDBConnectionManager.init( mongodb_uri, database_name );
