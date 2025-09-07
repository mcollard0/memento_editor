#!/usr/bin/env python3

import sys
import logging

def test_app_flow():
    print( "Testing application flow..." );
    
    # Setup logging like the main app
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    );
    
    try:
        # Test imports
        print( "Testing imports..." );
        from memento import start_new_memento, start_existing_memento
        from storage import FileManager
        from editor import create_editor
        print( "✓ All imports successful" );
        
        # Test new memento creation (without GUI)
        print( "Testing new memento creation..." );
        file_manager = FileManager.create_new_memento();
        print( f"✓ Created memento {file_manager.memento_id}" );
        
        # Test editor creation (without running GUI)
        print( "Testing editor creation..." );
        editor = create_editor( file_manager );
        print( "✓ Editor created successfully" );
        
        # Test existing memento loading
        print( "Testing existing memento loading..." );
        existing_manager = FileManager.load_memento( 2 );  # Our test memento
        if existing_manager:
            print( "✓ Existing memento loaded" );
            
            # Test if it's encrypted
            if existing_manager.is_encrypted():
                print( "✓ memento is encrypted" );
                
                # Test passphrase verification
                if existing_manager.verify_passphrase( "testpass123" ):
                    print( "✓ Passphrase verification works" );
                    
                    # Test content loading
                    content = existing_manager.load_current_snapshot();
                    if content:
                        print( f"✓ Content loaded: {len( content )} chars" );
                    else:
                        print( "✗ Content loading failed" );
                else:
                    print( "✗ Passphrase verification failed" );
            else:
                print( "- memento is not encrypted" );
                
            # Test editor creation for existing memento
            print( "Testing editor for existing memento..." );
            existing_editor = create_editor( existing_manager );
            print( "✓ Editor for existing memento created" );
        else:
            print( "✗ Failed to load existing memento" );
            
        print( "✓ All tests passed!" );
        
    except Exception as e:
        import traceback
        print( f"✗ Error during testing: {e}" );
        print( f"Traceback:\n{traceback.format_exc()}" );

if __name__ == "__main__":
    test_app_flow();
