CAPTURE EXPERIMENT ARCHIVE - September 7, 2025

This directory contains artifacts from a failed attempt to implement automatic text capture 
functionality for the memento editor application.

WHAT WAS ATTEMPTED:
- Auto-capture system to monitor active windows and capture text content
- Integration with memento editor to capture text from external applications (e.g., Facebook)
- OCR-based text extraction from screenshots using OpenAI Vision API and fallback methods
- Character count verification for captured text (target was ~137 characters)

WHY IT FAILED:
- OpenAI API rate limiting (HTTP 429 errors) caused repeated failures
- OCR accuracy and reliability issues
- Complex integration challenges between screenshot capture and text extraction
- Unnecessary complexity for simple text capture use case

LESSONS LEARNED:
- Direct clipboard/selection capture is more reliable than OCR
- API-dependent features create fragile dependencies
- Sometimes the simple solution (manual copy-paste) is better
- Rate limiting can render automated systems unusable

CONTENTS:
- auto_capture.log: [REMOVED - 296MB file too large for git repository]
- *.png files: Screenshot artifacts from capture attempts  
- This README.txt: Documentation of the experiment

OUTCOME:
Feature disabled and removed from main application flow.
Capture integration commented out in editor.py.
System reverted to basic editor functionality.

"I learned like seven ways not to do it." - Thomas Edison (probably)
