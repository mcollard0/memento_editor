#!/usr/bin/env python3
"""
Basic unit tests for the Memento storage module.
Run with: python3 test_storage.py
"""

import tempfile
import shutil
import json
from pathlib import Path

# Set up test environment
import sys
sys.path.insert(0, '.')

from storage import FileManager
from constants import CONTROL_FILE, calculate_buffer_size


def test_buffer_size_calculation():
    """Test the buffer size calculation logic."""
    print("Testing buffer size calculation...")
    
    # Small files should get more buffer slots
    small_size = calculate_buffer_size(1024)  # 1KB
    large_size = calculate_buffer_size(10 * 1024 * 1024)  # 10MB
    
    assert small_size >= large_size, f"Small files should have >= buffer size than large files: {small_size} vs {large_size}"
    assert 3 <= small_size <= 50, f"Buffer size out of range: {small_size}"
    assert 3 <= large_size <= 50, f"Buffer size out of range: {large_size}"
    
    print(f"✅ Small file (1KB) gets {small_size} buffers")
    print(f"✅ Large file (10MB) gets {large_size} buffers")


def test_ring_buffer_logic():
    """Test the ring buffer wrap-around logic."""
    print("\nTesting ring buffer logic...")
    
    # Create a temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create a test memento directory
        memento_dir = temp_dir / "test_memento"
        memento_dir.mkdir()
        
        # Mock the FileManager to use our test directory
        manager = FileManager.__new__(FileManager)
        manager.memento_id = 999
        manager.memento_dir = memento_dir
        manager.control_file = memento_dir / CONTROL_FILE
        manager.current_index = 0
        manager.max_buffers = 5  # Small buffer for testing
        manager.created_timestamp = 1234567890
        manager.last_modified = 1234567890
        
        # Override the buffer adjustment method for testing
        manager._adjust_buffer_size = lambda x: None  # Don't adjust during test
        
        # Test ring buffer wrapping
        test_data = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"]
        
        for i, data in enumerate(test_data):
            manager.write_snapshot(data)
            print(f"  Wrote '{data}' at index {manager.current_index}")
        
        # Verify wrap-around occurred
        assert manager.current_index == 2, f"Expected index 2 after wrap-around, got {manager.current_index}"
        
        # Verify we can read the current snapshot
        current = manager.load_current_snapshot()
        assert current == "Seventh", f"Expected 'Seventh', got '{current}'"
        
        # Verify older snapshots are available
        previous = manager.load_snapshot(-1)  # Previous version
        assert previous == "Sixth", f"Expected 'Sixth', got '{previous}'"
        
        # Count actual files created (should be 5, the buffer size)
        txt_files = list(memento_dir.glob("*.txt"))
        assert len(txt_files) == 5, f"Expected 5 txt files, found {len(txt_files)}"
        
        print("✅ Ring buffer wrap-around working correctly")
        print(f"✅ Current snapshot: '{current}'")
        print(f"✅ Previous snapshot: '{previous}'")
        print(f"✅ Total files created: {len(txt_files)}")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_control_file():
    """Test control file save/load functionality."""
    print("\nTesting control file functionality...")
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create a test memento directory
        memento_dir = temp_dir / "test_control"
        memento_dir.mkdir()
        
        # Create first manager instance
        manager1 = FileManager.__new__(FileManager)
        manager1.memento_id = 998
        manager1.memento_dir = memento_dir
        manager1.control_file = memento_dir / CONTROL_FILE
        manager1.current_index = 3
        manager1.max_buffers = 10
        manager1.created_timestamp = 1234567890
        manager1.last_modified = 1234567891
        
        # Save control file
        manager1._save_control_file()
        
        # Create second manager instance and load
        manager2 = FileManager.__new__(FileManager)
        manager2.memento_id = 998
        manager2.memento_dir = memento_dir
        manager2.control_file = memento_dir / CONTROL_FILE
        manager2.current_index = 0
        manager2.max_buffers = 5
        manager2.created_timestamp = 0
        manager2.last_modified = 0
        
        # Load control file
        manager2._load_control_file()
        
        # Verify loaded values match saved values
        assert manager2.current_index == 3, f"Expected current_index=3, got {manager2.current_index}"
        assert manager2.max_buffers == 10, f"Expected max_buffers=10, got {manager2.max_buffers}"
        assert manager2.created_timestamp == 1234567890, f"Expected created_timestamp=1234567890, got {manager2.created_timestamp}"
        assert manager2.last_modified == 1234567891, f"Expected last_modified=1234567891, got {manager2.last_modified}"
        
        print("✅ Control file save/load working correctly")
        print(f"✅ Loaded index: {manager2.current_index}")
        print(f"✅ Loaded buffer size: {manager2.max_buffers}")
        
    finally:
        shutil.rmtree(temp_dir)


def run_tests():
    """Run all tests."""
    print("🧪 Running Memento Storage Tests")
    print("=" * 50)
    
    try:
        test_buffer_size_calculation()
        test_ring_buffer_logic()
        test_control_file()
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
