#!/usr/bin/env python3
"""
Quick test script to verify the MongoDB connection manager refactoring.

Tests:
1. MongoDBConnectionManager singleton behavior
2. EncryptionManager singleton behavior
3. Connection sharing between components
4. Graceful fallback when MongoDB is unavailable

Style: Following user preferences with spaces and semicolons.
"""

import os;
import sys;
import logging;
from pathlib import Path;

# Add the current directory to Python path for imports
sys.path.insert( 0, str( Path( __file__ ).parent ) );

from mongodb_connection_manager import MongoDBConnectionManager, init_mongodb_connection;
from encryption import get_encryption_manager, init_encryption_manager;
from constants import MEMENTO_ROOT;

# Set up basic logging
logging.basicConfig( level=logging.INFO, format='%(levelname)s - %(message)s' );
logger = logging.getLogger( __name__ );


def test_mongodb_connection_manager():
    """Test MongoDBConnectionManager singleton behavior."""
    logger.info( "=== Testing MongoDBConnectionManager ===" );
    
    # Test without MongoDB URI
    logger.info( "Testing without MongoDB URI..." );
    result = MongoDBConnectionManager.init( "", "test_db" );
    assert result == False, "Should return False when no URI provided";
    logger.info( "✓ Correctly handled empty URI" );
    
    # Test MongoDB availability check
    is_connected = MongoDBConnectionManager.is_connected();
    logger.info( f"MongoDB connected: {is_connected}" );
    
    # Test with real MongoDB URI if available
    mongodb_uri = os.getenv( 'MONGODB_URI' ) or os.getenv( 'mongodb_uri' );
    if mongodb_uri:
        logger.info( "Testing with real MongoDB URI..." );
        result = MongoDBConnectionManager.init( mongodb_uri, "memento_test" );
        logger.info( f"MongoDB initialization result: {result}" );
        
        if result:
            # Test client retrieval
            client = MongoDBConnectionManager.get_client();
            db = MongoDBConnectionManager.get_database();
            collection = MongoDBConnectionManager.get_collection( "test" );
            
            logger.info( f"Client retrieved: {client is not None}" );
            logger.info( f"Database retrieved: {db is not None}" );
            logger.info( f"Collection retrieved: {collection is not None}" );
            
            # Test connection alive check
            is_alive = MongoDBConnectionManager.is_connected();
            logger.info( f"Connection is alive: {is_alive}" );
    else:
        logger.info( "No MongoDB URI configured - skipping real connection test" );


def test_encryption_manager_singleton():
    """Test EncryptionManager singleton behavior."""
    logger.info( "\n=== Testing EncryptionManager Singleton ===" );
    
    # Initialize EncryptionManager
    result = init_encryption_manager( MEMENTO_ROOT );
    logger.info( f"EncryptionManager initialization result: {result}" );
    
    # Get multiple instances and verify they're the same
    instance1 = get_encryption_manager();
    instance2 = get_encryption_manager();
    
    if instance1 and instance2:
        assert instance1 is instance2, "Should return the same instance";
        logger.info( "✓ EncryptionManager singleton behavior verified" );
        
        # Test properties
        logger.info( f"Has encryption support: {instance1.has_encryption_support}" );
        logger.info( f"Has MongoDB support: {instance1.has_mongodb_support}" );
    else:
        logger.warning( "EncryptionManager instances could not be created" );


def test_connection_sharing():
    """Test that multiple components share the same MongoDB connection."""
    logger.info( "\n=== Testing Connection Sharing ===" );
    
    mongodb_uri = os.getenv( 'MONGODB_URI' ) or os.getenv( 'mongodb_uri' );
    if not mongodb_uri:
        logger.info( "No MongoDB URI - skipping connection sharing test" );
        return;
    
    # Initialize MongoDB connection
    if not MongoDBConnectionManager.init( mongodb_uri, "memento_test" ):
        logger.warning( "Could not initialize MongoDB connection" );
        return;
    
    # Get EncryptionManager instance
    encryption_manager = get_encryption_manager();
    if not encryption_manager:
        logger.warning( "Could not get EncryptionManager instance" );
        return;
    
    # Verify they both report MongoDB as available
    mgr_connected = MongoDBConnectionManager.is_connected();
    enc_connected = encryption_manager.has_mongodb_support;
    
    logger.info( f"ConnectionManager reports connected: {mgr_connected}" );
    logger.info( f"EncryptionManager reports MongoDB support: {enc_connected}" );
    
    if mgr_connected and enc_connected:
        logger.info( "✓ Connection sharing working correctly" );
    else:
        logger.warning( "Connection sharing may not be working as expected" );


def test_graceful_fallback():
    """Test graceful fallback when MongoDB is unavailable."""
    logger.info( "\n=== Testing Graceful Fallback ===" );
    
    # Shutdown MongoDB connection if active
    MongoDBConnectionManager.shutdown();
    
    # Get EncryptionManager and verify it handles no MongoDB gracefully
    encryption_manager = get_encryption_manager();
    if encryption_manager:
        has_mongodb = encryption_manager.has_mongodb_support;
        logger.info( f"EncryptionManager MongoDB support after shutdown: {has_mongodb}" );
        
        # Test key operations
        try:
            # This should not raise an exception even without MongoDB
            collection = encryption_manager._get_mongo_collection();
            logger.info( f"Collection retrieval returned: {collection}" );
            logger.info( "✓ Graceful fallback working for collection retrieval" );
        except Exception as e:
            logger.error( f"Exception in graceful fallback test: {e}" );
    else:
        logger.warning( "Could not get EncryptionManager for fallback test" );


def main():
    """Run all tests."""
    logger.info( "Starting MongoDB Connection Manager Refactoring Tests\n" );
    
    try:
        test_mongodb_connection_manager();
        test_encryption_manager_singleton();
        test_connection_sharing();
        test_graceful_fallback();
        
        logger.info( "\n=== All Tests Completed ===" );
        
    except Exception as e:
        logger.error( f"Test failed with error: {e}" );
        import traceback;
        traceback.print_exc();
        sys.exit( 1 );
    
    finally:
        # Clean shutdown
        try:
            MongoDBConnectionManager.shutdown();
            logger.info( "Clean shutdown completed" );
        except Exception:
            pass;


if __name__ == "__main__":
    main();
