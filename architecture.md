# Memento Text Editor Architecture

## Overview
Memento is a text editor with automatic saving, version history through ring buffers, and optional encryption with MongoDB storage support.

## Database Schema

### Local File Storage
- **Directory Structure**: `~/.Memento/{memento_id}/`
- **Control Files**: `control.json` - contains metadata and ring buffer configuration
- **Content Files**: 
  - Plaintext: `{index}.txt` 
  - Encrypted: `{index}.enc`
- **Key Files**: `{memento_id}.key` - encrypted private keys for local storage

### MongoDB Collections

#### Collection: `memento_storage.mementos`

**Document Types:**

1. **Content Documents**
```json
{
  "_id": ObjectId,
  "memento_id": int,
  "type": "content", 
  "timestamp": float,
  "data": BinaryData  // Compressed + Encrypted content
}
```

2. **Encryption Key Documents**
```json
{
  "_id": ObjectId,
  "memento_id": int,
  "type": "encryption_key",
  "private_key": BinaryData,  // PKCS#8 encrypted private key
  "public_key": BinaryData,   // PEM public key
  "created_at": float
}
```

## API Endpoints and Core Functions

### Storage Layer (`storage.py`)
- `FileManager.create_new_memento()` - Creates new memento with unique ID
- `FileManager.load_memento(id)` - Loads existing memento by ID  
- `FileManager.write_snapshot(text)` - Saves text to ring buffer
- `FileManager.load_current_snapshot()` - Retrieves latest version
- `FileManager.list_mementos(auto_migrate=True)` - Lists all mementos with automatic migration
- `FileManager.import_text_file(path, passphrase)` - Imports text file as new memento
- `FileManager.import_text_file_with_dialog(passphrase)` - File import with GUI dialog

### Encryption Layer (`encryption.py`)
- `EncryptionManager.encrypt_data(text, key)` - Brotli compress + AES encrypt
- `EncryptionManager.decrypt_data(blob, key)` - AES decrypt + Brotli decompress
- `EncryptionManager.save_encrypted_content(id, content, key)` - Store to MongoDB/local
- `EncryptionManager.load_encrypted_content(id, key)` - Retrieve from MongoDB/local
- `EncryptionManager.migrate_local_mementos_to_mongodb(passphrase)` - Auto-migrate local to cloud

## Key Business Logic Rules

### Ring Buffer Management
- **Buffer Size**: Dynamic based on content size (3-50 snapshots)
- **Smaller files**: More snapshots (up to 50)
- **Larger files**: Fewer snapshots (minimum 3) 
- **Auto-adjustment**: Buffer size recalculates on each write

### Encryption Flow
1. **Enable Encryption**: 
   - Generate ECC key pair
   - Derive AES key from passphrase using PBKDF2
   - Encrypt existing content
   - Store encrypted keys

2. **Content Storage**:
   - Text → Brotli compression → AES-GCM encryption → MongoDB/File
   - 12-byte nonce + ciphertext format
   - Maximum ~40MB uncompressed (15MB compressed limit for MongoDB)

3. **Content Retrieval**:
   - Load encrypted data → AES decrypt → Brotli decompress → Text

### Auto-Save Behavior
- **Idle Threshold**: 1.5 seconds after typing stops
- **Character Thresholds**: Dynamic thresholds [2, 4, 8, 16, 32, 64]
- **Force Save**: Ctrl+S keyboard shortcut

### Migration Workflow (Local → MongoDB)
1. **Auto-Detection**: When `list_mementos()` is called and MongoDB is available
2. **Check for Local Mementos**: Scans for unencrypted `.txt` files not in MongoDB
3. **User Prompt**: GUI dialog shows memento preview and requests encryption passphrase
4. **Migration Process**: 
   - Enables encryption with user passphrase
   - Compresses and encrypts content
   - Stores in MongoDB with timestamp
   - Creates local backup before cleanup
5. **Verification**: Confirms successful MongoDB storage before proceeding

### Text File Import Workflow
1. **Import Dialog**: File picker supports .txt, .md, .py, code files, etc.
2. **Encoding Detection**: Auto-detects UTF-8, Latin-1, CP1252, ISO-8859-1
3. **Metadata Addition**: Prepends import source and timestamp to content
4. **Encryption Option**: Optional passphrase for MongoDB storage
5. **Memento Creation**: Creates new memento with imported content
6. **Auto-Open**: Directly opens imported memento in editor

## Current Feature Status

### ✅ Implemented Features
- Local file storage with ring buffers
- Optional MongoDB storage support  
- Brotli compression for text efficiency
- AES-GCM encryption with PBKDF2 key derivation
- ECC key pair generation for future features
- Auto-save with configurable idle detection
- Cross-platform GUI with tkinter
- Memento selector and management
- **Automatic migration from local to MongoDB** (when MongoDB available)
- **Text file import with encryption options** (via GUI dialog)
- Comprehensive test coverage

### 🚧 Partial Features  
- Encryption key management (basic implementation)
- MongoDB connection error handling with warnings
- Fallback to local storage when MongoDB unavailable

### 📋 Planned Features
- GUI integration for universal text capture
- Shared memento collaboration
- Cloud synchronization options
- Advanced search and filtering
- Export/import functionality

## Known Issues and Constraints

### Performance
- Large text files (>10MB) may have slower encryption/compression
- MongoDB 16MB document size limit requires compression
- Memory usage scales with text size during processing

### Security
- Private keys stored encrypted with passphrase
- No key recovery mechanism if passphrase forgotten
- Local key files not protected by OS-level encryption

### Dependencies
- **Required**: Python 3.8+, tkinter
- **Optional**: cryptography, brotli, pymongo
- **Graceful degradation** when optional dependencies missing

### MongoDB Limitations
- Connection timeout: 5 seconds
- Maximum retries: Built into pymongo driver
- No automatic failover to replica sets configured
- Test database cleanup required between test runs

## Migrations

### Version 1.0.0 → Current
- Added encryption support with optional dependencies
- Added MongoDB storage option
- Added compression with Brotli
- Extended ring buffer with dynamic sizing
- Added comprehensive test suite
- **NEW (2025-09-07)**: Refactored to persistent MongoDB connection architecture
- **NEW**: Added MongoDBConnectionManager singleton with 1-hour session timeout
- **NEW**: Converted EncryptionManager to singleton pattern
- **IMPROVED**: Eliminated multiple MongoDB connection creation overhead

**No database migrations required** - new features are additive and backward compatible.
**No API breaking changes** - existing code continues to work with improved performance.

## Test Coverage

### Test Suite: `tests/test_memento_mongodb_encryption.py`
- **MongoDB Connection**: Basic operations and error handling
- **Encryption/Decryption**: Round-trip with correct passphrases
- **Compression**: Effectiveness verification for repetitive text  
- **Error Handling**: Wrong passphrase, missing mementos
- **Integration**: Full create→encrypt→store→retrieve→decrypt cycle
- **Performance**: Compression ratio validation
- **Security**: Encrypted data verification

### Test Environment
- **Isolated MongoDB**: Uses `mongodb_uri` environment variable
- **Temporary directories**: Clean state for each test
- **Dependency detection**: Graceful skipping when libraries unavailable
- **Coverage reporting**: Success rate and detailed failure information

Last Updated: 2025-09-07 (MongoDB Connection Refactoring)
