# Memento Text Editor

A simple, elegant text editor with automatic saving and version history through ring buffers.

## Background -- The Why

So I was overclocking the ram on my pc, and I went a bit too far. I booted and was writing a lengthy response in LinkedIn, and the Chrome window crashed. After a quick error 
check, I refreshed the window.

And my hard earned, much considered, too lengthy and probably annoying message was gone. 

So. Here we are. A text editor that saves constantly to a ring buffer. 

## Future Features

The next logical step is to integrate it into the GUI so that whatever window you're working on, it captures the text, and saves it. 

At this point, I thought it would be creepy, requires encryption, privacy concerns, and so forth. 

But as a mental exercise, I enjoyed this. 

## Features

- **Automatic Saving**: Saves your work automatically when you stop typing (configurable idle time)
- **Ring Buffer Versioning**: Maintains multiple versions of your text with intelligent buffer sizing
- **Multiple Mementos**: Organize your writing into separate mementos (documents)
- **Clean Interface**: Minimalist text editor focused on writing
- **Cross-Platform**: Works on Linux, macOS, and Windows with Python 3.8+

## Installation

### Prerequisites

- Python 3.8 or higher
- tkinter (usually included with Python, but may need separate installation on Linux)

### Linux (Ubuntu/Debian)

```bash
# Install tkinter if not available
sudo apt install python3-tk

# Clone or download the memento directory
# Then run:
cd memento
python3 memento.py
```

### macOS

```bash
# tkinter is usually included with Python on macOS
cd memento
python3 memento.py
```

### Windows

```bash
# tkinter is usually included with Python on Windows
cd memento
python memento.py
```

## Usage

### Starting the Application

Run the main application:

```bash
python3 memento.py
```

### First Launch

On first launch, you'll see the memento selector with no existing mementos. Click "Create New" to start your first memento.

### Working with Mementos

- **Create New**: Start a new memento (document)
- **Open Existing**: Select from your existing mementos
- **Auto-Save**: Your work is automatically saved when you stop typing
- **Keyboard Shortcuts**:
  - `Ctrl+S`: Force save
  - `Ctrl+N`: Create new memento
  - `Ctrl+O`: Open memento selector

### Data Storage

All data is stored in `~/.Memento/` directory:

```
~/.Memento/
├── 0/                    # First memento
│   ├── control.json     # Metadata and ring buffer info
│   ├── 0.txt           # Snapshot files
│   ├── 1.txt
│   └── ...
├── 1/                   # Second memento
│   └── ...
└── memento.log         # Application logs
```

### Ring Buffer System

Each memento uses a ring buffer to store multiple versions:

- **Smaller files**: More save points (up to 50)
- **Larger files**: Fewer save points (minimum 3)
- **Automatic adjustment**: Buffer size adjusts based on content size
- **No manual cleanup needed**: Old versions are automatically managed

## Architecture

The application consists of several modules:

- `memento.py`: Main application entry point and workflow management
- `storage.py`: File management and ring buffer logic
- `editor.py`: Main text editor window
- `selector.py`: Memento selection interface
- `autosave.py`: Automatic saving logic based on idle detection
- `constants.py`: Configuration and utility functions

## Configuration

Edit `constants.py` to customize:

- `IDLE_THRESHOLD_SECONDS`: Time to wait before auto-saving (default: 1.5s)
- `MIN_BUFFER_SIZE`: Minimum ring buffer size (default: 3)
- `MAX_BUFFER_SIZE`: Maximum ring buffer size (default: 50)

## Troubleshooting

### "No module named 'tkinter'"

On Linux, install tkinter:

```bash
sudo apt install python3-tk
```

### Permission Errors

Ensure you have write permissions to your home directory for the `~/.Memento/` folder.

### Application Crashes

Check the log file at `~/.Memento/memento.log` for error details.

## Development

### Running Tests

```bash
# Install pytest if needed
pip install pytest

# Run tests (when available)
pytest tests/
```

### Code Structure

The application follows a modular design with clear separation of concerns:

- GUI components are in separate modules
- Storage logic is isolated and testable
- Auto-save functionality is independent and reusable

## License

This project is open source. Feel free to modify and distribute.

## Version History

- **v1.0.0**: Initial release with core functionality
  - Auto-save with idle detection
  - Ring buffer version management
  - Multi-memento support
  - Cross-platform compatibility
