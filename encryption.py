#!/usr/bin/env python3
"""
Encryption and compression module for memento.
Provides ECC encryption, Brotli compression, and MongoDB storage support.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

# Optional dependencies - graceful degradation if not available
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False
    brotli = None

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    import pymongo
    from bson.binary import Binary
    from bson.errors import BSONError
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False
    pymongo = None

logger = logging.getLogger(__name__)

# Compression settings
BROTLI_COMPRESSION_LEVEL = 6

# Estimate: English text with Brotli compression level 6 typically achieves 70-80% compression
# With 16MB MongoDB limit and ~25% overhead for encryption/metadata, conservative estimate:
# 16MB * 0.75 (usable space) / 0.25 (compression ratio) = ~48MB uncompressed
# Being conservative for safety:
ESTIMATED_MAX_UNCOMPRESSED_SIZE_MB = 40


class EncryptionManager:
    """Manages encryption, compression, and storage for memento."""
    
    def __init__(self, memento_root: Path):
        self.memento_root = Path(memento_root)
        # Check both uppercase and lowercase environment variables
        self.mongodb_uri = os.getenv('MONGODB_URI') or os.getenv('mongodb_uri')
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_collection = None
        
        # Track warning state
        self._warning_file = self.memento_root / '.mongo_warning_shown'
        self._warning_count = self._load_warning_count()
        
        # Initialize MongoDB if available
        if self.mongodb_uri and HAS_PYMONGO:
            self._init_mongodb()
    
    def _load_warning_count(self) -> int:
        """Load the number of times MongoDB warnings have been shown."""
        try:
            if self._warning_file.exists():
                return int(self._warning_file.read_text().strip())
        except (ValueError, IOError):
            pass
        return 0
    
    def _save_warning_count(self, count: int):
        """Save the warning count."""
        try:
            self._warning_file.write_text(str(count))
        except IOError as e:
            logger.error(f"Failed to save warning count: {e}")
    
    def _init_mongodb(self):
        """Initialize MongoDB connection."""
        try:
            self.mongo_client = pymongo.MongoClient(
                self.mongodb_uri, 
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000
            )
            
            # Test connection
            self.mongo_client.server_info()
            
            # Create/get database
            self.mongo_db = self.mongo_client.memento_storage
            self.mongo_collection = self.mongo_db.mementos
            
            # Test write capability
            test_doc = {"_test": True, "data": Binary(b"test")}
            result = self.mongo_collection.insert_one(test_doc)
            self.mongo_collection.delete_one({"_id": result.inserted_id})
            
            logger.info("MongoDB connection established successfully")
            
        except Exception as e:
            logger.error(f"MongoDB initialization failed: {e}")
            self.mongo_client = None
            self.mongo_db = None
            self.mongo_collection = None
            
            # Show warning if we haven't shown too many
            if self._warning_count < 2:
                self._show_mongodb_warning(str(e))
                self._warning_count += 1
                self._save_warning_count(self._warning_count)
    
    def _show_mongodb_warning(self, error_message: str):
        """Show MongoDB connection warning."""
        try:
            from tkinter import messagebox
            messagebox.showwarning(
                "MongoDB Connection Warning",
                f"Failed to connect to MongoDB:\n{error_message}\n\n"
                f"Falling back to local file storage.\n"
                f"This warning will only be shown {2 - self._warning_count} more time(s)."
            )
        except ImportError:
            # Fallback if tkinter not available
            logger.warning(f"MongoDB connection failed: {error_message}")
    
    @property
    def has_encryption_support(self) -> bool:
        """Check if encryption is supported."""
        return HAS_CRYPTO and HAS_BROTLI
    
    @property
    def has_mongodb_support(self) -> bool:
        """Check if MongoDB is available and connected."""
        return self.mongo_collection is not None
    
    @property
    def estimated_max_size_mb(self) -> int:
        """Get estimated maximum uncompressed size for MongoDB storage."""
        return ESTIMATED_MAX_UNCOMPRESSED_SIZE_MB
    
    def generate_key_pair(self, passphrase: str) -> Tuple[bytes, bytes]:
        """Generate ECC key pair and encrypt private key with passphrase."""
        if not HAS_CRYPTO:
            raise RuntimeError("Cryptography library not available")
        
        # Generate ECC private key
        private_key = ec.generate_private_key(ec.SECP384R1())
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode())
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    def derive_aes_key(self, passphrase: str, salt: bytes) -> bytes:
        """Derive AES key from passphrase using PBKDF2."""
        if not HAS_CRYPTO:
            raise RuntimeError("Cryptography library not available")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(passphrase.encode())
    
    def encrypt_data(self, data: str, aes_key: bytes) -> bytes:
        """Encrypt and compress data."""
        if not self.has_encryption_support:
            raise RuntimeError("Encryption/compression libraries not available")
        
        # Compress first
        compressed = brotli.compress(data.encode('utf-8'), quality=BROTLI_COMPRESSION_LEVEL)
        
        # Then encrypt
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, compressed, None)
        
        # Combine nonce + ciphertext
        return nonce + ciphertext
    
    def decrypt_data(self, encrypted_data: bytes, aes_key: bytes) -> str:
        """Decrypt and decompress data."""
        if not self.has_encryption_support:
            raise RuntimeError("Encryption/compression libraries not available")
        
        # Extract nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Decrypt
        aesgcm = AESGCM(aes_key)
        compressed = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Decompress
        return brotli.decompress(compressed).decode('utf-8')
    
    def is_encrypted_data(self, data: bytes) -> bool:
        """Test if data appears to be encrypted/compressed binary data."""
        if len(data) < 16:  # Too small to be our encrypted format
            return False
        
        # Check if it looks like our format (12-byte nonce + encrypted data)
        # Encrypted data should have high entropy
        if len(set(data[:16])) < 8:  # Low entropy in first 16 bytes
            return False
        
        # Try to detect Brotli compressed data after decryption would fail
        # This is a heuristic - we can't definitively know without trying to decrypt
        return True
    
    def save_encrypted_key(self, private_key: bytes, public_key: bytes, memento_id: int):
        """Save encrypted private key to storage."""
        key_data = {
            'memento_id': memento_id,
            'private_key': private_key,
            'public_key': public_key,
            'created_at': self._get_timestamp()
        }
        
        if self.has_mongodb_support:
            # Save to MongoDB
            key_data['private_key'] = Binary(private_key)
            key_data['public_key'] = Binary(public_key)
            
            # Upsert the key
            self.mongo_collection.update_one(
                {'memento_id': memento_id, 'type': 'encryption_key'},
                {'$set': {**key_data, 'type': 'encryption_key'}},
                upsert=True
            )
        else:
            # Save to local file
            key_file = self.memento_root / f"{memento_id}.key"
            key_file.write_bytes(json.dumps({
                'private_key': private_key.hex(),
                'public_key': public_key.hex(),
                'created_at': key_data['created_at']
            }).encode())
    
    def load_encrypted_key(self, memento_id: int) -> Optional[Tuple[bytes, bytes]]:
        """Load encrypted private key from storage."""
        if self.has_mongodb_support:
            # Load from MongoDB
            doc = self.mongo_collection.find_one({
                'memento_id': memento_id,
                'type': 'encryption_key'
            })
            if doc:
                return bytes(doc['private_key']), bytes(doc['public_key'])
        else:
            # Load from local file
            key_file = self.memento_root / f"{memento_id}.key"
            if key_file.exists():
                try:
                    key_data = json.loads(key_file.read_bytes())
                    return (
                        bytes.fromhex(key_data['private_key']),
                        bytes.fromhex(key_data['public_key'])
                    )
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        
        return None
    
    def save_encrypted_content(self, memento_id: int, content: str, aes_key: bytes):
        """Save encrypted content to storage."""
        encrypted_data = self.encrypt_data(content, aes_key)
        
        content_doc = {
            'memento_id': memento_id,
            'type': 'content',
            'timestamp': self._get_timestamp(),
            'data': encrypted_data
        }
        
        if self.has_mongodb_support:
            # Check size limit
            if len(encrypted_data) > 15 * 1024 * 1024:  # 15MB safety margin
                raise ValueError(f"Encrypted data too large for MongoDB ({len(encrypted_data) / 1024 / 1024:.1f}MB)")
            
            content_doc['data'] = Binary(encrypted_data)
            self.mongo_collection.insert_one(content_doc)
        else:
            # Save to local file
            content_file = self.memento_root / f"{memento_id}.enc"
            content_file.write_bytes(encrypted_data)
    
    def load_encrypted_content(self, memento_id: int, aes_key: bytes) -> Optional[str]:
        """Load and decrypt content from storage."""
        if self.has_mongodb_support:
            # Load from MongoDB (get latest)
            doc = self.mongo_collection.find_one(
                {'memento_id': memento_id, 'type': 'content'},
                sort=[('timestamp', -1)]
            )
            if doc:
                encrypted_data = bytes(doc['data'])
                return self.decrypt_data(encrypted_data, aes_key)
        else:
            # Load from local file
            content_file = self.memento_root / f"{memento_id}.enc"
            if content_file.exists():
                encrypted_data = content_file.read_bytes()
                return self.decrypt_data(encrypted_data, aes_key)
        
        return None
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def migrate_local_mementos_to_mongodb(self, passphrase: str = None) -> int:
        """Migrate local unencrypted mementos to MongoDB with encryption.
        
        Args:
            passphrase: Passphrase for encryption. If None, prompts user.
            
        Returns:
            Number of mementos migrated
        """
        if not self.has_mongodb_support:
            logger.info("MongoDB not available - skipping migration")
            return 0
        
        if not self.has_encryption_support:
            logger.warning("Encryption not available - cannot migrate to MongoDB")
            return 0
        
        # Import here to avoid circular imports
        from storage import FileManager, MEMENTO_ROOT
        from constants import make_dirs_if_missing
        
        if not MEMENTO_ROOT.exists():
            logger.info("No local memento directory found")
            return 0
        
        migrated_count = 0
        logger.info("Starting migration of local mementos to MongoDB")
        
        # Find all local mementos
        for item in MEMENTO_ROOT.iterdir():
            if item.is_dir() and item.name.isdigit():
                memento_id = int(item.name)
                
                try:
                    # Check if already exists in MongoDB
                    existing_content = self.mongo_collection.find_one({
                        'memento_id': memento_id,
                        'type': 'content'
                    })
                    
                    if existing_content:
                        logger.info(f"memento {memento_id} already exists in MongoDB - skipping")
                        continue
                    
                    # Load the local memento
                    file_manager = FileManager(memento_id)
                    
                    # Skip if already encrypted (shouldn't happen but safety check)
                    if file_manager.is_encrypted():
                        logger.info(f"memento {memento_id} is already encrypted - skipping")
                        continue
                    
                    # Get the current content
                    content = file_manager.load_current_snapshot()
                    
                    if not content or content.strip() == "":
                        logger.info(f"memento {memento_id} is empty - skipping")
                        continue
                    
                    # Get passphrase if not provided
                    if passphrase is None:
                        passphrase = self._prompt_for_passphrase(memento_id)
                        if not passphrase:
                            logger.info(f"No passphrase provided for memento {memento_id} - skipping")
                            continue
                    
                    # Enable encryption on the memento (this will trigger MongoDB storage)
                    file_manager.enable_encryption(passphrase)
                    
                    # Force re-save to ensure MongoDB storage  
                    current_content = file_manager.load_current_snapshot()
                    file_manager.write_snapshot(current_content)
                    
                    # Verify it was saved to MongoDB (check with small delay)
                    import time
                    time.sleep(0.1)  # Small delay for async operations
                    
                    mongodb_content = self.mongo_collection.find_one({
                        'memento_id': memento_id,
                        'type': 'content'
                    })
                    
                    if mongodb_content:
                        logger.info(f"✅ Successfully migrated memento {memento_id} to MongoDB")
                        migrated_count += 1
                        
                        # Create a backup of original local files before cleanup
                        self._backup_local_memento(memento_id, item)
                    else:
                        # Check if the issue is with database name
                        logger.warning(f"Could not verify memento {memento_id} in MongoDB collection '{self.mongo_collection.name}'")
                        
                        # Try to save directly using the encryption manager
                        try:
                            # Use the EncryptionManager to save directly to MongoDB
                            aes_key = file_manager._aes_key
                            if aes_key:
                                self.save_encrypted_content(memento_id, current_content, aes_key)
                                
                                # Verify again
                                mongodb_content = self.mongo_collection.find_one({
                                    'memento_id': memento_id,
                                    'type': 'content'
                                })
                                
                                if mongodb_content:
                                    logger.info(f"✅ Successfully migrated memento {memento_id} to MongoDB (direct save)")
                                    migrated_count += 1
                                    self._backup_local_memento(memento_id, item)
                                else:
                                    logger.error(f"Failed to verify memento {memento_id} even after direct save")
                            else:
                                logger.error(f"No AES key available for memento {memento_id}")
                        except Exception as direct_save_error:
                            logger.error(f"Direct save failed for memento {memento_id}: {direct_save_error}")
                        
                except Exception as e:
                    logger.error(f"Error migrating memento {memento_id}: {e}")
                    continue
        
        logger.info(f"Migration completed: {migrated_count} mementos migrated to MongoDB")
        return migrated_count
    
    def _prompt_for_passphrase(self, memento_id: int) -> str:
        """Prompt user for encryption passphrase."""
        try:
            import tkinter as tk
            from tkinter import simpledialog, messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Show info about the memento first
            from storage import FileManager
            fm = FileManager(memento_id)
            preview = fm.get_first_line()
            
            messagebox.showinfo(
                "memento Migration",
                f"Found local memento {memento_id}:\n\n"
                f"Preview: {preview[:100]}{'...' if len(preview) > 100 else ''}\n\n"
                f"This memento will be encrypted and migrated to MongoDB."
            )
            
            passphrase = simpledialog.askstring(
                f"Encrypt memento {memento_id}",
                "Enter passphrase for encryption:",
                show='*'
            )
            
            root.destroy()
            return passphrase or ""
            
        except ImportError:
            # Fallback for environments without tkinter
            import getpass
            print(f"\nMigrating memento {memento_id} to MongoDB...")
            return getpass.getpass(f"Enter passphrase for memento {memento_id}: ")
    
    def _backup_local_memento(self, memento_id: int, memento_dir):
        """Create backup of local memento before cleanup."""
        try:
            import shutil
            backup_dir = self.memento_root / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = self._get_timestamp()
            backup_name = f"memento_{memento_id}_{int(timestamp)}_pre_migration"
            backup_path = backup_dir / backup_name
            
            shutil.copytree(memento_dir, backup_path)
            logger.info(f"Created backup of memento {memento_id} at {backup_path}")
            
        except Exception as e:
            logger.warning(f"Failed to create backup for memento {memento_id}: {e}")


def get_missing_dependencies() -> list:
    """Get list of missing optional dependencies."""
    missing = []
    if not HAS_BROTLI:
        missing.append("Brotli")
    if not HAS_CRYPTO:
        missing.append("cryptography")
    if not HAS_PYMONGO:
        missing.append("pymongo")
    return missing
