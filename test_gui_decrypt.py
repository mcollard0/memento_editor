#!/usr/bin/env python3

import sys
import logging
import tkinter as tk

def test_gui_decrypt():
    print( "Testing GUI decryption with memento 2..." );
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    );
    
    try:
        from storage import FileManager
        from editor import EditorWindow
        
        # Load our test memento
        manager = FileManager.load_memento( 2 );
        if not manager:
            print( "✗ Could not load memento 2" );
            return;
            
        print( f"✓ Loaded memento {manager.memento_id}" );
        
        # Create editor window
        editor = EditorWindow( manager );
        print( "✓ Created editor window" );
        print( "🔒 Memento should show encrypted placeholder" );
        print( "💡 Try pressing Ctrl+D and enter 'testpass123' to decrypt" );
        print( "🚪 Close window when done testing" );
        
        # Run the GUI
        editor.run();
        print( "✓ GUI session completed" );
        
    except Exception as e:
        import traceback
        print( f"✗ Error during GUI test: {e}" );
        print( f"Traceback:\n{traceback.format_exc()}" );

if __name__ == "__main__":
    test_gui_decrypt();
