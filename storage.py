#!/usr/bin/env python3
"""
Storage and ring buffer management for the Memento text editor application.
Handles file persistence, version control through ring buffers, and memento metadata.
"""

import json
import pathlib
import time
import os
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from constants import (
    MEMENTO_ROOT, CONTROL_FILE, make_dirs_if_missing, 
    get_memento_dir, get_next_memento_id, calculate_buffer_size
)

# Optional encryption support
try:
    from encryption import EncryptionManager
    HAS_ENCRYPTION = True
except ImportError:
    HAS_ENCRYPTION = False


class MementoInfo:
    """Information about a memento for display in the selector."""
    def __init__(self, memento_id: int, first_line: str, last_modified: datetime):
        self.memento_id = memento_id
        self.first_line = first_line
        self.last_modified = last_modified


class FileManager:
    """Manages file storage and ring buffer for a single memento."""
    
    def __init__(self, memento_id: int):
        self.memento_id = memento_id
        self.memento_dir = get_memento_dir(memento_id)
        self.control_file = self.memento_dir / CONTROL_FILE
        
        # Control file structure
        self.current_index = 0
        self.max_buffers = 10  # Default, will be adjusted
        self.created_timestamp = time.time()
        self.last_modified = time.time()
        
        # Encryption support
        self.encryption_manager = None
        self._is_encrypted = False
        self._current_passphrase = None
        self._aes_key = None
        
        if HAS_ENCRYPTION:
            self.encryption_manager = EncryptionManager(MEMENTO_ROOT)
        
        # Load existing control file if it exists
        self._load_control_file()
    
    def _load_control_file(self):
        """Load control file data if it exists."""
        if self.control_file.exists():
            try:
                with open(self.control_file, 'r') as f:
                    data = json.load(f)
                    self.current_index = data.get('current_index', 0)
                    self.max_buffers = data.get('max_buffers', 10)
                    self.created_timestamp = data.get('created_timestamp', time.time())
                    self.last_modified = data.get('last_modified', time.time())
                    self._is_encrypted = data.get('is_encrypted', False)
            except (json.JSONDecodeError, FileNotFoundError):
                # If control file is corrupted, start fresh
                pass
        
        # If no control file, check for encrypted data to determine encryption status
        if not self.control_file.exists() and self.encryption_manager:
            self._detect_encryption_status()
    
    def _save_control_file(self):
        """Save control file with current state."""
        make_dirs_if_missing(self.memento_dir)
        
        data = {
            'current_index': self.current_index,
            'max_buffers': self.max_buffers,
            'created_timestamp': self.created_timestamp,
            'last_modified': self.last_modified,
            'is_encrypted': self._is_encrypted
        }
        
        with open(self.control_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _detect_encryption_status(self):
        """Detect if existing files are encrypted by examining snapshot files."""
        if not self.encryption_manager:
            return
        
        # Check for .enc files first
        for i in range(self.max_buffers):
            enc_path = self.memento_dir / f"{i}.enc"
            if enc_path.exists():
                self._is_encrypted = True
                return
        
        # Check .txt files for encrypted content
        for i in range(self.max_buffers):
            txt_path = self.memento_dir / f"{i}.txt"
            if txt_path.exists():
                try:
                    # Try to read as binary and check if it looks encrypted
                    data = txt_path.read_bytes()
                    if self.encryption_manager.is_encrypted_data(data):
                        self._is_encrypted = True
                        return
                except (IOError, OSError):
                    continue
    
    def _get_snapshot_path(self, index: int) -> pathlib.Path:
        """Get the file path for a snapshot at the given index."""
        if self._is_encrypted:
            return self.memento_dir / f"{index}.enc"
        else:
            return self.memento_dir / f"{index}.txt"
    
    def is_encrypted(self) -> bool:
        """Check if this memento is encrypted."""
        return self._is_encrypted
    
    def _prepare_aes_key(self, passphrase: str):
        """Prepare AES key for encryption/decryption."""
        if not self.encryption_manager:
            raise RuntimeError("Encryption not available")
        
        # Use memento_id as salt source for consistency
        salt = str(self.memento_id).encode().ljust(32, b'\0')[:32]
        self._aes_key = self.encryption_manager.derive_aes_key(passphrase, salt)
        self._current_passphrase = passphrase
    
    def verify_passphrase(self, passphrase: str) -> bool:
        """Verify if the given passphrase is correct for this encrypted memento."""
        if not self._is_encrypted or not self.encryption_manager:
            return True
        
        try:
            # Try to load and decrypt current snapshot
            self._prepare_aes_key(passphrase)
            content = self.load_current_snapshot()
            return True
        except Exception:
            self._aes_key = None
            self._current_passphrase = None
            return False
    
    def enable_encryption(self, passphrase: str):
        """Enable encryption for this memento."""
        if self._is_encrypted:
            raise ValueError("Memento is already encrypted")
        
        if not self.encryption_manager:
            raise RuntimeError("Encryption not available")
        
        # Prepare encryption key
        self._prepare_aes_key(passphrase)
        
        # Load existing content
        current_content = self.load_current_snapshot()
        
        # Remove old unencrypted files
        for i in range(self.max_buffers):
            old_path = self.memento_dir / f"{i}.txt"
            if old_path.exists():
                old_path.unlink()
        
        # Mark as encrypted
        self._is_encrypted = True
        
        # Re-save current content (will be encrypted)
        self.write_snapshot(current_content)
    
    def disable_encryption(self, passphrase: str):
        """Disable encryption for this memento."""
        if not self._is_encrypted:
            raise ValueError("Memento is not encrypted")
        
        if not self.verify_passphrase(passphrase):
            raise ValueError("Invalid passphrase")
        
        # Load current content (decrypted)
        current_content = self.load_current_snapshot()
        
        # Remove old encrypted files
        for i in range(self.max_buffers):
            old_path = self.memento_dir / f"{i}.enc"
            if old_path.exists():
                old_path.unlink()
        
        # Mark as not encrypted
        self._is_encrypted = False
        self._aes_key = None
        self._current_passphrase = None
        
        # Re-save current content (will be plaintext)
        self.write_snapshot(current_content)
    
    def change_passphrase(self, old_passphrase: str, new_passphrase: str):
        """Change the encryption passphrase."""
        if not self._is_encrypted:
            raise ValueError("Memento is not encrypted")
        
        if not self.verify_passphrase(old_passphrase):
            raise ValueError("Invalid current passphrase")
        
        # Load all existing snapshots with old key
        snapshots = {}
        for i in range(self.max_buffers):
            snapshot_path = self._get_snapshot_path(i)
            if snapshot_path.exists():
                try:
                    content = self._load_snapshot_at_index(i)
                    if content is not None:
                        snapshots[i] = content
                except Exception:
                    continue
        
        # Prepare new key
        self._prepare_aes_key(new_passphrase)
        
        # Re-encrypt all snapshots with new key
        for index, content in snapshots.items():
            self._write_snapshot_at_index(index, content)
        
        # Update control file
        self._save_control_file()
    
    def _adjust_buffer_size(self, text_size: int):
        """Adjust buffer size based on text size, protecting current position."""
        new_buffer_size = calculate_buffer_size(text_size)
        
        if new_buffer_size == self.max_buffers:
            return  # No change needed
        
        # Don't adjust if current index is near boundaries (to avoid data loss)
        if (self.current_index < 2 or 
            self.current_index >= self.max_buffers - 2):
            return
        
        if new_buffer_size > self.max_buffers:
            # Growing buffer - just update the count
            self.max_buffers = new_buffer_size
        else:
            # Shrinking buffer - remove excess files
            for i in range(new_buffer_size, self.max_buffers):
                snapshot_path = self._get_snapshot_path(i)
                if snapshot_path.exists():
                    snapshot_path.unlink()
            self.max_buffers = new_buffer_size
    
    def write_snapshot(self, text: str):
        """Write a new snapshot to the ring buffer."""
        make_dirs_if_missing(self.memento_dir)
        
        # Adjust buffer size based on text size
        text_bytes = len(text.encode('utf-8'))
        self._adjust_buffer_size(text_bytes)
        
        # Move to next position in ring buffer
        self.current_index = (self.current_index + 1) % self.max_buffers
        
        # Write the snapshot
        self._write_snapshot_at_index(self.current_index, text)
        
        # Update timestamps and save control file
        self.last_modified = time.time()
        self._save_control_file()
    
    def _write_snapshot_at_index(self, index: int, text: str):
        """Write snapshot at specific index, handling encryption."""
        snapshot_path = self._get_snapshot_path(index)
        
        if self._is_encrypted and self.encryption_manager and self._aes_key:
            # Encrypt and save
            encrypted_data = self.encryption_manager.encrypt_data(text, self._aes_key)
            with open(snapshot_path, 'wb') as f:
                f.write(encrypted_data)
        else:
            # Save as plaintext
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                f.write(text)
    
    def load_current_snapshot(self) -> str:
        """Load the current (most recent) snapshot."""
        return self._load_snapshot_at_index(self.current_index) or ""
    
    def _load_snapshot_at_index(self, index: int) -> Optional[str]:
        """Load snapshot at specific index, handling encryption."""
        snapshot_path = self._get_snapshot_path(index)
        
        if not snapshot_path.exists():
            return None
        
        try:
            if self._is_encrypted and self.encryption_manager and self._aes_key:
                # Load and decrypt
                with open(snapshot_path, 'rb') as f:
                    encrypted_data = f.read()
                return self.encryption_manager.decrypt_data(encrypted_data, self._aes_key)
            else:
                # Load as plaintext
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except (FileNotFoundError, UnicodeDecodeError, Exception):
            return None
    
    def load_snapshot(self, version_offset: int = 0) -> Optional[str]:
        """Load a snapshot at a specific version offset from current.
        
        Args:
            version_offset: 0 for current, -1 for previous, etc.
        """
        index = (self.current_index + version_offset) % self.max_buffers
        return self._load_snapshot_at_index(index)
    
    def get_first_line(self) -> str:
        """Get the first line of the current snapshot for preview."""
        if self._is_encrypted and not self._aes_key:
            return "[Encrypted memento]"
        
        content = self.load_current_snapshot()
        if not content:
            return "[Empty memento]"
        
        lines = content.split('\n')
        first_line = lines[0].strip()
        return first_line if first_line else "[Untitled]"
    
    @staticmethod
    def create_new_memento() -> 'FileManager':
        """Create a new memento and return its FileManager."""
        memento_id = get_next_memento_id()
        manager = FileManager(memento_id)
        
        # Initialize with empty content
        manager.write_snapshot("")
        return manager
    
    @staticmethod
    def load_memento(memento_id: int) -> Optional['FileManager']:
        """Load an existing memento by ID."""
        memento_dir = get_memento_dir(memento_id)
        
        if not memento_dir.exists():
            return None
        
        return FileManager(memento_id)
    
    @staticmethod
    def list_mementos(auto_migrate: bool = True) -> List[MementoInfo]:
        """List all existing mementos with metadata.
        
        Args:
            auto_migrate: If True, automatically migrates local mementos to MongoDB when available
        """
        make_dirs_if_missing(MEMENTO_ROOT)
        mementos = []
        
        # Auto-migrate local mementos to MongoDB if available
        if auto_migrate and HAS_ENCRYPTION:
            try:
                from encryption import EncryptionManager
                encryption_manager = EncryptionManager(MEMENTO_ROOT)
                
                if encryption_manager.has_mongodb_support:
                    # Check if there are any unmigrated local mementos
                    has_local_unmigrated = False
                    
                    for item in MEMENTO_ROOT.iterdir():
                        if item.is_dir() and item.name.isdigit():
                            memento_id = int(item.name)
                            
                            # Check if exists in MongoDB
                            existing = encryption_manager.mongo_collection.find_one({
                                'memento_id': memento_id,
                                'type': 'content'
                            })
                            
                            if not existing:
                                # Check if it's unencrypted (has .txt files)
                                txt_files = list(item.glob('*.txt'))
                                if txt_files:
                                    has_local_unmigrated = True
                                    break
                    
                    if has_local_unmigrated:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info("Found local mementos that can be migrated to MongoDB")
                        
                        # Attempt silent migration with a default passphrase prompt
                        try:
                            migrated_count = encryption_manager.migrate_local_mementos_to_mongodb()
                            if migrated_count > 0:
                                logger.info(f"Successfully migrated {migrated_count} mementos to MongoDB")
                        except Exception as e:
                            logger.warning(f"Auto-migration failed (user may have cancelled): {e}")
                            
            except Exception as e:
                # Don't let migration errors break the listing
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error during auto-migration check: {e}")
        
        # List local mementos
        for item in MEMENTO_ROOT.iterdir():
            if item.is_dir() and item.name.isdigit():
                memento_id = int(item.name)
                manager = FileManager.load_memento(memento_id)
                
                if manager:
                    first_line = manager.get_first_line()
                    last_modified = datetime.fromtimestamp(manager.last_modified)
                    
                    mementos.append(MementoInfo(
                        memento_id=memento_id,
                        first_line=first_line,
                        last_modified=last_modified
                    ))
        
        # Add MongoDB-only mementos if available
        if HAS_ENCRYPTION:
            try:
                from encryption import EncryptionManager
                encryption_manager = EncryptionManager(MEMENTO_ROOT)
                
                if encryption_manager.has_mongodb_support:
                    # Get all memento IDs from MongoDB
                    mongodb_ids = set()
                    local_ids = set(int(item.name) for item in MEMENTO_ROOT.iterdir() 
                                  if item.is_dir() and item.name.isdigit())
                    
                    cursor = encryption_manager.mongo_collection.find(
                        {'type': 'content'}, 
                        {'memento_id': 1, 'timestamp': 1}
                    )
                    
                    for doc in cursor:
                        memento_id = doc['memento_id']
                        mongodb_ids.add(memento_id)
                        
                        # If this memento exists only in MongoDB, create MementoInfo for it
                        if memento_id not in local_ids:
                            # Create a minimal manager to get first line
                            temp_manager = FileManager(memento_id)
                            first_line = temp_manager.get_first_line()  # Will show [Encrypted memento] without key
                            
                            # Use MongoDB timestamp
                            timestamp = doc.get('timestamp', time.time())
                            last_modified = datetime.fromtimestamp(timestamp)
                            
                            mementos.append(MementoInfo(
                                memento_id=memento_id,
                                first_line=first_line,
                                last_modified=last_modified
                            ))
                            
            except Exception as e:
                # Don't let MongoDB errors break the listing
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error loading MongoDB mementos: {e}")
        
        # Sort by last modified time, most recent first
        mementos.sort(key=lambda m: m.last_modified, reverse=True)
        return mementos
    
    @staticmethod
    def import_text_file(file_path: str, passphrase: str = None) -> Optional['FileManager']:
        """Import a text file as a new memento.
        
        Args:
            file_path: Path to the text file to import
            passphrase: Optional passphrase for encryption
            
        Returns:
            FileManager for the newly created memento, or None if import failed
        """
        try:
            import pathlib
            file_path = pathlib.Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError(f"Cannot decode file {file_path} - unsupported encoding")
            
            if not content.strip():
                raise ValueError(f"File {file_path} is empty")
            
            # Create new memento
            manager = FileManager.create_new_memento()
            
            # Add import metadata to the beginning
            import_info = f"# Imported from: {file_path.name}\n# Import date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            full_content = import_info + content
            
            # Enable encryption if passphrase provided
            if passphrase:
                manager.enable_encryption(passphrase)
            
            # Write the content
            manager.write_snapshot(full_content)
            
            return manager
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to import text file {file_path}: {e}")
            return None
    
    @staticmethod
    def import_text_file_with_dialog(passphrase: str = None) -> Optional['FileManager']:
        """Import a text file using a file dialog.
        
        Args:
            passphrase: Optional passphrase for encryption
            
        Returns:
            FileManager for the newly created memento, or None if cancelled/failed
        """
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Show file dialog
            file_path = filedialog.askopenfilename(
                title="Import Text File",
                filetypes=[
                    ("Text files", "*.txt *.md *.py *.js *.html *.css *.json *.xml *.csv"),
                    ("Markdown files", "*.md *.markdown"),
                    ("Code files", "*.py *.js *.html *.css *.java *.cpp *.c *.h"),
                    ("All files", "*.*")
                ]
            )
            
            root.destroy()
            
            if not file_path:
                return None  # User cancelled
            
            # Import the file
            manager = FileManager.import_text_file(file_path, passphrase)
            
            if manager:
                messagebox.showinfo(
                    "Import Successful",
                    f"Successfully imported '{pathlib.Path(file_path).name}' as memento {manager.memento_id}"
                )
            else:
                messagebox.showerror(
                    "Import Failed",
                    f"Failed to import '{pathlib.Path(file_path).name}'"
                )
            
            return manager
            
        except ImportError:
            # Fallback for environments without tkinter
            file_path = input("Enter path to text file to import: ").strip()
            if file_path:
                return FileManager.import_text_file(file_path, passphrase)
            return None
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in import dialog: {e}")
            return None
