# 🖥️ Wayland Screenshot Setup Guide

## 🔍 Current Issue
Screen capture is failing due to Wayland security restrictions. Here are several solutions:

## 🚀 Quick Solutions

### Option 1: Use Interactive Screenshot Mode
The system will now fall back to interactive screenshot mode when window capture fails:

```bash
python3 test_enhanced_ocr.py
```

**What happens:**
1. System tries to capture the specific window
2. If that fails, it requests a **full screenshot**
3. You may need to approve the screenshot permission in a dialog
4. OCR will then process the full screenshot

### Option 2: GNOME Screenshot Permissions
For GNOME on Wayland, you may need to grant screenshot permissions:

```bash
# Check current permissions
gsettings get org.gnome.desktop.screensaver lock-enabled

# If you get permission dialogs, approve them for the terminal/Python
```

### Option 3: Switch to X11 Session (Temporary)
If you need precise window targeting:

1. **Log out** of your current session
2. At the login screen, click the **gear icon** ⚙️ 
3. Select **"Ubuntu on Xorg"** instead of **"Ubuntu"**
4. Log in and test the OCR system

### Option 4: Use Wayland with User Interaction
The system now supports interactive capture modes:

- **grim + slurp**: You'll be asked to select the screen area
- **gnome-screenshot**: May show permission dialogs
- **Full screen mode**: Captures entire screen, then processes it

## 🧪 Test the Screenshot System

### Test Basic Screenshots:
```bash
python3 wayland_screenshot.py
```

### Test the Enhanced OCR:
```bash
# This will use full screenshot mode if window capture fails
python3 test_enhanced_ocr.py
```

### Test with GUI:
```bash
python3 ocr_accuracy_tester.py
```

## 🔧 Available Screenshot Methods

The system now tries multiple methods in order:

1. **Wayland Native** (`grim`, `slurp`)
2. **X11 Compatibility** (`xwd` via XWayland)  
3. **Desktop Specific** (`gnome-screenshot`)
4. **Interactive** (`scrot`, `spectacle`)
5. **Full Screen Fallback**

## 🎯 Recommended Workflow for Wayland

1. **Start the OCR tester**: `python3 ocr_accuracy_tester.py`
2. **Use "Get Active Window"** to get window ID
3. **Click "Capture & Test All"**
4. **Approve any permission dialogs** that appear
5. **System will capture full screen** if window capture fails
6. **OCR processes the screenshot** and extracts text
7. **Rate the accuracy** of each AI service

## 📝 Notes

- **Full screen capture** works more reliably than window-specific capture on Wayland
- **Permission dialogs** may appear the first time you run screenshot tools
- **AI OCR services** can still extract text from form fields even in full screenshots
- **Text input box detection** works on both full screenshots and window captures

## 🐛 Still Having Issues?

If screenshots still fail:

1. **Check available tools**:
   ```bash
   which grim gnome-screenshot scrot
   ```

2. **Test manual screenshot**:
   ```bash
   grim screenshot.png
   # or
   gnome-screenshot --file=screenshot.png
   ```

3. **Check Wayland environment**:
   ```bash
   echo $XDG_SESSION_TYPE
   echo $XDG_CURRENT_DESKTOP
   ```

The enhanced OCR system is now designed to work with Wayland's security model while still providing high-quality text extraction from multiple AI services.
