#!/usr/bin/env python3

from storage import FileManager
import sys

def main():
    print( "Creating new test memento..." );
    
    # Create a new memento
    manager = FileManager.create_new_memento();
    print( f"Created memento ID: {manager.memento_id}" );
    
    # Add some test content
    test_content = "This is a test memento.\n\nIt has multiple lines of text to verify that decryption works properly.\n\nCreated for debugging purposes.";
    manager.write_snapshot( test_content );
    print( f"Added content: {len( test_content )} characters" );
    
    # Enable encryption with test passphrase
    test_passphrase = "testpass123";
    try:
        manager.enable_encryption( test_passphrase );
        print( f"Enabled encryption with passphrase: {test_passphrase}" );
    except Exception as e:
        print( f"Error enabling encryption: {e}" );
        return;
    
    # Verify the passphrase works
    print( f"Testing passphrase verification..." );
    if manager.verify_passphrase( test_passphrase ):
        print( "✓ Passphrase verification successful" );
        
        # Test content loading
        content = manager.load_current_snapshot();
        if content:
            print( f"✓ Content loaded successfully: {len( content )} characters" );
            print( f"First 50 chars: {content[:50]}" );
        else:
            print( "✗ Content loading failed" );
    else:
        print( "✗ Passphrase verification failed" );
    
    print( f"Test memento {manager.memento_id} created successfully!" );
    return manager.memento_id;

if __name__ == "__main__":
    main();
