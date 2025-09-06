#!/usr/bin/env python3

import tkinter as tk
from tkinter import simpledialog
from storage import FileManager
import sys
from pathlib import Path

def main():
    print( 'Testing passphrase verification and decryption...' );

    # Get user passphrase
    root = tk.Tk();
    root.withdraw();
    passphrase = simpledialog.askstring( 'Debug Test', 'Enter your passphrase:', show='*' );
    if not passphrase:
        print( 'No passphrase entered.' );
        sys.exit( 1 );

    # Find encrypted memos
    print( f'Loading memo list...' );
    try:
        mementos = FileManager.list_mementos();
        print( f'Found {len( mementos )} total mementos' );
        
        # Look for encrypted mementos
        encrypted_mementos = [];
        for memento_info in mementos:
            temp_manager = FileManager.load_memento( memento_info.memento_id );
            if temp_manager and temp_manager.is_encrypted():
                encrypted_mementos.append( memento_info );
        
        print( f'Found {len( encrypted_mementos )} encrypted mementos' );
        
        if not encrypted_mementos:
            print( 'No encrypted mementos found to test.' );
            return;
        
        # Test with first encrypted memo
        memento_info = encrypted_mementos[0];
        memento_id = memento_info.memento_id;
        print( f'Testing decryption on memento ID {memento_id}: {memento_info.first_line}' );
        
        # Create FileManager for this memento
        file_manager = FileManager( memento_id );
        
        if not file_manager.is_encrypted():
            print( f'Warning: Memo {memento_id} does not appear to be encrypted on disk' );
            return;
        
        # Test passphrase verification
        print( f'Testing passphrase verification...' );
        is_valid = file_manager.verify_passphrase( passphrase );
        print( f'Passphrase valid: {is_valid}' );
        
        if not is_valid:
            print( 'Invalid passphrase - cannot decrypt.' );
            return;
        
        # Try to load decrypted content
        print( f'Loading decrypted content...' );
        content = file_manager.load_current_snapshot();
        if content:
            print( f'Decryption successful. Content length: {len( content )}' );
            print( f'First 100 chars: {content[:100]}' );
        else:
            print( 'Decryption failed - no content returned' );
            
    except Exception as e:
        print( f'Error during memo loading/decryption: {e}' );
        import traceback;
        traceback.print_exc();

    print( 'Debug test complete.' );

if __name__ == "__main__":
    main();
