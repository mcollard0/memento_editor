#!/usr/bin/env python3
"""
Enhanced OCR System with Multiple AI Services
Focuses on capturing text from text input boxes with high accuracy
"""

import os
import sys
import json
import base64
import time
import tempfile
import subprocess
import logging
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
import requests
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class EnhancedOCR:
    def __init__(self, config_file: str = "ocr_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.available_services = self._check_available_services()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        # Get API keys from environment variables first
        default_config = {
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "xai_api_key": os.environ.get("XAI_API_KEY", ""),
            "preferred_service": "auto",  # Try all services automatically
            "capture_delay": 3,  # 3 second delay before capture
            "tesseract_config": "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?@#$%^&*()_+-=[]{}|;':\"<>?/~` ",
            "image_preprocessing": {
                "enhance_contrast": True,
                "sharpen": True,
                "denoise": True,
                "upscale_factor": 2.0
            },
            "text_box_detection": {
                "enabled": True,
                "min_box_area": 100,
                "max_box_area": 50000,
                "aspect_ratio_range": [0.1, 10.0]
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults, but prioritize environment variables for API keys
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    # Always override with environment variables for API keys
                    elif key.endswith('_api_key') and default_config[key]:
                        config[key] = default_config[key]
                return config
            else:
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def _check_available_services(self) -> Dict[str, bool]:
        """Check which OCR services are available."""
        services = {
            "tesseract": self._check_tesseract(),
            "openai": bool(self.config.get("openai_api_key", "").strip()),
            "anthropic": bool(self.config.get("anthropic_api_key", "").strip()),
            "xai": bool(self.config.get("xai_api_key", "").strip())
        }
        
        logger.info(f"Available OCR services: {[k for k, v in services.items() if v]}")
        return services
    
    def _check_tesseract(self) -> bool:
        """Check if tesseract is available."""
        try:
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def detect_text_input_boxes(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """Detect text input boxes in the image using OpenCV."""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Failed to load image: {image_path}")
                return []
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply adaptive threshold
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY_INV, 11, 2)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_boxes = []
            min_area = self.config["text_box_detection"]["min_box_area"]
            max_area = self.config["text_box_detection"]["max_box_area"]
            aspect_range = self.config["text_box_detection"]["aspect_ratio_range"]
            
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # Filter by area
                if area < min_area or area > max_area:
                    continue
                
                # Filter by aspect ratio
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio < aspect_range[0] or aspect_ratio > aspect_range[1]:
                    continue
                
                # Check if it looks like a text input box
                # (rectangular shape, reasonable dimensions)
                if w > 50 and h > 15:  # Minimum text box dimensions
                    text_boxes.append((x, y, w, h))
            
            logger.debug(f"Detected {len(text_boxes)} potential text input boxes")
            return text_boxes
            
        except Exception as e:
            logger.error(f"Text box detection failed: {e}")
            return []
    
    def preprocess_image(self, image_path: str, output_path: str = None) -> str:
        """Preprocess image for better OCR accuracy."""
        try:
            if not output_path:
                output_path = image_path.replace('.png', '_processed.png')
            
            # Open image with PIL
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Upscale for better OCR
                if self.config["image_preprocessing"]["upscale_factor"] > 1.0:
                    factor = self.config["image_preprocessing"]["upscale_factor"]
                    new_size = (int(img.width * factor), int(img.height * factor))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Enhance contrast
                if self.config["image_preprocessing"]["enhance_contrast"]:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.5)
                
                # Sharpen
                if self.config["image_preprocessing"]["sharpen"]:
                    img = img.filter(ImageFilter.SHARPEN)
                
                # Denoise
                if self.config["image_preprocessing"]["denoise"]:
                    img = img.filter(ImageFilter.MedianFilter())
                
                # Save processed image
                img.save(output_path, 'PNG', quality=95)
                
            logger.debug(f"Image preprocessed: {image_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image_path  # Return original if preprocessing fails
    
    def extract_text_boxes(self, image_path: str) -> List[str]:
        """Extract text from detected text input boxes."""
        try:
            if not self.config["text_box_detection"]["enabled"]:
                return [self.ocr_full_image(image_path)]
            
            text_boxes = self.detect_text_input_boxes(image_path)
            if not text_boxes:
                logger.debug("No text boxes detected, processing full image")
                return [self.ocr_full_image(image_path)]
            
            extracted_texts = []
            
            # Process each detected text box
            with Image.open(image_path) as img:
                for i, (x, y, w, h) in enumerate(text_boxes):
                    # Crop text box with some padding
                    padding = 5
                    x1 = max(0, x - padding)
                    y1 = max(0, y - padding)
                    x2 = min(img.width, x + w + padding)
                    y2 = min(img.height, y + h + padding)
                    
                    cropped = img.crop((x1, y1, x2, y2))
                    
                    # Save cropped box temporarily
                    with tempfile.NamedTemporaryFile(suffix=f'_box_{i}.png', delete=False) as temp_file:
                        cropped_path = temp_file.name
                        cropped.save(cropped_path, 'PNG')
                    
                    try:
                        # Preprocess the cropped box
                        processed_path = self.preprocess_image(cropped_path)
                        
                        # OCR the text box
                        text = self.ocr_full_image(processed_path)
                        if text and text.strip():
                            extracted_texts.append(text.strip())
                        
                    finally:
                        # Cleanup temp files
                        for path in [cropped_path, processed_path]:
                            try:
                                if os.path.exists(path):
                                    os.unlink(path)
                            except:
                                pass
            
            return extracted_texts if extracted_texts else [self.ocr_full_image(image_path)]
            
        except Exception as e:
            logger.error(f"Text box extraction failed: {e}")
            return [self.ocr_full_image(image_path)]
    
    def ocr_full_image(self, image_path: str, service: str = None) -> str:
        """Perform OCR on full image using specified service with intelligent fallback."""
        return self._ocr_with_fallback(image_path, service)
    
    def _ocr_with_fallback(self, image_path: str, preferred_service: str = None) -> str:
        """Perform OCR with intelligent fallback handling quota limits and errors."""
        
        # Define service priority order (fastest/best to slowest/fallback)
        priority_order = [
            "anthropic",    # Usually fastest and most accurate
            "openai",       # Very good, but quota issues
            "xai",          # Good alternative
            "tesseract"     # Slowest, CPU-only fallback
        ]
        
        # If specific service requested, try it first
        if preferred_service and preferred_service != "auto" and preferred_service in priority_order:
            priority_order.remove(preferred_service)
            priority_order.insert(0, preferred_service)
        
        logger.debug(f"OCR fallback order: {priority_order}")
        
        for svc in priority_order:
            if not self.available_services.get(svc, False):
                logger.debug(f"Service {svc} not available, skipping")
                continue
            
            try:
                logger.info(f"Trying OCR with {svc}...")
                
                if svc == "tesseract":
                    result = self._ocr_tesseract(image_path)
                elif svc == "openai":
                    result = self._ocr_openai(image_path)
                elif svc == "anthropic":
                    result = self._ocr_anthropic(image_path)
                elif svc == "xai":
                    result = self._ocr_xai(image_path)
                else:
                    continue
                
                if result and len(result.strip()) > 3:
                    logger.info(f"✅ OCR successful with {svc}: {len(result)} characters")
                    return result
                else:
                    logger.debug(f"Service {svc} returned empty or very short result")
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Log detailed error for investigation
                logger.debug(f"Service {svc} detailed error: {type(e).__name__}: {str(e)[:200]}")
                
                # Check for quota/rate limit errors
                if any(keyword in error_msg for keyword in ['quota', 'rate limit', '429', 'insufficient_quota']):
                    logger.warning(f"⚠️  {svc} over quota/rate limited, trying next service...")
                    continue
                    
                # Check for image size errors (file size)
                elif any(keyword in error_msg for keyword in ['exceeds', 'maximum', 'too large', 'size']) and 'mb' in error_msg:
                    logger.warning(f"⚠️  {svc} image file size error, trying next service...")
                    continue
                    
                # Check for dimension errors (pixel dimensions)
                elif any(keyword in error_msg for keyword in ['dimension', 'pixel', '8000']):
                    logger.warning(f"⚠️  {svc} image dimension error, trying next service...")
                    continue
                    
                # Check for API key/auth errors
                elif any(keyword in error_msg for keyword in ['unauthorized', 'api key', 'authentication', '401', '403']):
                    logger.warning(f"⚠️  {svc} authentication error, trying next service...")
                    continue
                    
                # Check for model not found errors
                elif any(keyword in error_msg for keyword in ['model', 'not found', '404', 'does not exist']):
                    logger.warning(f"⚠️  {svc} model error, trying next service...")
                    continue
                    
                # Check for timeout errors
                elif any(keyword in error_msg for keyword in ['timeout', 'timed out', 'connection']):
                    logger.warning(f"⚠️  {svc} connection/timeout error, trying next service...")
                    continue
                    
                else:
                    logger.error(f"❌ {svc} failed with unexpected error: {type(e).__name__}: {str(e)[:200]}")
                    continue
        
        logger.error("❌ All OCR services failed")
        return ""
    
    def _ocr_single_service(self, image_path: str, service: str) -> str:
        """Test a single OCR service without fallback (for comparison)."""
        try:
            if service == "tesseract":
                return self._ocr_tesseract(image_path)
            elif service == "openai":
                return self._ocr_openai(image_path)
            elif service == "anthropic":
                return self._ocr_anthropic(image_path)
            elif service == "xai":
                return self._ocr_xai(image_path)
            else:
                return ""
        except Exception as e:
            logger.debug(f"Single service {service} failed: {e}")
            return ""
    
    def _ocr_tesseract(self, image_path: str) -> str:
        """Perform OCR using local Tesseract (CPU-only, slower fallback)."""
        try:
            logger.info("🐌 Using Tesseract (CPU-only fallback) - this may be slower...")
            
            # Preprocess image first
            processed_path = self.preprocess_image(image_path)
            
            # Build Tesseract command with CPU-only optimizations
            cmd = ['tesseract', processed_path, 'stdout']
            
            # Add CPU-optimized configuration
            tesseract_opts = [
                '--oem', '3',  # Use LSTM OCR Engine Mode (most accurate)
                '--psm', '6',  # Assume uniform block of text
                '-c', 'tessedit_do_invert=0',  # Don't auto-invert
                '-c', 'load_system_dawg=0',    # Don't load system dictionary (faster)
                '-c', 'load_freq_dawg=0',      # Don't load frequency dictionary
                '-c', 'load_punc_dawg=0',      # Don't load punctuation dictionary
                '-c', 'load_number_dawg=0',    # Don't load number dictionary
                '-c', 'load_unambig_dawg=0',   # Don't load unambiguous dictionary
                '-c', 'load_bigram_dawg=0',    # Don't load bigram dictionary
                '-c', 'load_fixed_length_dawgs=0',  # Don't load fixed length dictionaries
                '-l', 'eng'  # English language
            ]
            
            # Use configured options if available, otherwise use CPU-optimized defaults
            if self.config.get("tesseract_config"):
                # Parse user config but ensure CPU-only
                user_opts = self.config["tesseract_config"].split()
                # Filter out any GPU-related options and add our CPU-only opts
                filtered_opts = [opt for opt in user_opts if 'gpu' not in opt.lower() and 'cuda' not in opt.lower()]
                cmd.extend(filtered_opts)
            else:
                cmd.extend(tesseract_opts)
            
            # Set environment variables to ensure CPU-only operation
            env = os.environ.copy()
            env['OMP_NUM_THREADS'] = '1'  # Single-threaded for consistency
            env['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable CUDA
            
            logger.debug(f"Tesseract command: {' '.join(cmd)}")
            
            # Run with longer timeout since it's slower
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=60, env=env)  # Longer timeout for CPU processing
            
            if result.returncode == 0:
                text = result.stdout.strip()
                if text and len(text) > 3:
                    logger.info(f"✅ Tesseract OCR completed: {len(text)} characters extracted")
                    return text
                else:
                    logger.debug("Tesseract returned empty or very short result")
                    return ""
            else:
                logger.error(f"Tesseract error (return code {result.returncode}): {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Tesseract OCR timed out (CPU processing can be slow)")
            return ""
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return ""
    
    def _compress_image_for_api(self, image_path: str, max_size_mb: float = 5.0) -> str:
        """Compress image to meet API size limits with aggressive PNG optimization."""
        try:
            import tempfile
            
            max_size_bytes = max_size_mb * 1024 * 1024
            
            # Check current file size
            current_size = os.path.getsize(image_path)
            logger.debug(f"Original image: {current_size / 1024 / 1024:.2f}MB")
            
            # Always compress for API calls to ensure optimal size and smaller than input
            compressed_path = image_path.replace('.png', '_api_compressed.png')
            
            # If input is already small enough, still compress to ensure it's smaller
            target_size = min(max_size_bytes * 0.8, current_size * 0.9)  # 80% of limit OR 90% of input, whichever is smaller
            
            with Image.open(image_path) as img:
                logger.debug(f"Original dimensions: {img.width}x{img.height}, mode: {img.mode}")
                
                # Convert to RGB if RGBA (remove alpha channel for better compression)
                if img.mode in ('RGBA', 'LA'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])  # Use alpha as mask
                    else:
                        background.paste(img)
                    img = background
                    logger.debug("Converted RGBA to RGB for better compression")
                
                # Check dimension limits for Anthropic (8000 pixels max)
                max_dimension = 8000  # Anthropic limit
                needs_dimension_resize = max(img.width, img.height) > max_dimension
                
                # Use the target size calculated above (smaller of 80% limit or 90% of input)
                needs_size_resize = current_size > target_size
                
                if needs_dimension_resize or needs_size_resize:
                    # Calculate scaling factors
                    dimension_scale = 1.0
                    size_scale = 1.0
                    
                    if needs_dimension_resize:
                        dimension_scale = max_dimension / max(img.width, img.height)
                        logger.debug(f"Dimension scaling needed: {dimension_scale:.2f} (max dimension: {max_dimension})")
                    
                    if needs_size_resize:
                        ratio = target_size / current_size
                        size_scale = ratio ** 0.5  # Square root for width/height scaling
                        logger.debug(f"Size scaling needed: {size_scale:.2f} (target: {target_size / 1024 / 1024:.1f}MB)")
                    
                    # Use the more aggressive scaling
                    scale_factor = min(dimension_scale, size_scale)
                    
                    # Ensure minimum reasonable size but respect dimension limits
                    min_dimension = 400  # Reduced minimum
                    new_width = max(min_dimension, int(img.width * scale_factor))
                    new_height = max(min_dimension, int(img.height * scale_factor))
                    
                    # Double-check dimension limits
                    if max(new_width, new_height) > max_dimension:
                        scale_factor = max_dimension / max(new_width, new_height)
                        new_width = int(new_width * scale_factor)
                        new_height = int(new_height * scale_factor)
                    
                    logger.debug(f"Resizing to: {new_width}x{new_height} (scale: {scale_factor:.2f})")
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Try different compression levels
                compression_attempts = [
                    {'format': 'PNG', 'options': {'optimize': True, 'compress_level': 9}},
                    {'format': 'JPEG', 'options': {'quality': 95, 'optimize': True}},
                    {'format': 'JPEG', 'options': {'quality': 85, 'optimize': True}},
                    {'format': 'JPEG', 'options': {'quality': 75, 'optimize': True}},
                ]
                
                for attempt in compression_attempts:
                    try:
                        temp_path = compressed_path.replace('.png', f'_temp.{attempt["format"].lower()}')
                        img.save(temp_path, attempt['format'], **attempt['options'])
                        
                        temp_size = os.path.getsize(temp_path)
                        logger.debug(f"Compression attempt ({attempt['format']}): {temp_size / 1024 / 1024:.2f}MB")
                        
                        if temp_size <= max_size_bytes:
                            # Success! Move temp file to final compressed path
                            final_path = compressed_path.replace('.png', f'_final.{attempt["format"].lower()}')
                            os.rename(temp_path, final_path)
                            
                            logger.info(f"✅ Compressed {current_size / 1024 / 1024:.2f}MB → {temp_size / 1024 / 1024:.2f}MB ({attempt['format']})")
                            return final_path
                        else:
                            # Try next compression level
                            os.unlink(temp_path)
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Compression attempt failed: {e}")
                        continue
                
                # If all attempts failed, do aggressive resizing
                logger.warning("Standard compression failed, using aggressive resizing...")
                
                # Resize to fit within limit by reducing quality significantly
                target_pixels = 1024 * 768  # Target resolution
                current_pixels = img.width * img.height
                
                if current_pixels > target_pixels:
                    scale_factor = (target_pixels / current_pixels) ** 0.5
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    logger.debug(f"Aggressively resized to: {new_width}x{new_height}")
                
                # Final save with maximum compression
                img.save(compressed_path, 'JPEG', quality=70, optimize=True)
                
                final_size = os.path.getsize(compressed_path)
                logger.info(f"⚠️ Aggressive compression: {current_size / 1024 / 1024:.2f}MB → {final_size / 1024 / 1024:.2f}MB")
                
                return compressed_path
                
        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return image_path  # Return original if compression fails
    
    def _encode_image_base64(self, image_path: str) -> tuple[str, str]:
        """Encode image as base64 for API calls and return (base64_data, mime_type)."""
        try:
            # Detect MIME type from file extension
            if image_path.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif image_path.lower().endswith('.png'):
                mime_type = 'image/png'
            elif image_path.lower().endswith('.webp'):
                mime_type = 'image/webp'
            else:
                mime_type = 'image/png'  # Default fallback
            
            with open(image_path, "rb") as image_file:
                base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                
            logger.debug(f"Encoded image: {len(base64_data)} chars, type: {mime_type}")
            return base64_data, mime_type
            
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return "", "image/png"
    
    def _ocr_openai(self, image_path: str) -> str:
        """Perform OCR using OpenAI Vision API."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.config["openai_api_key"])
            
            # Preprocess and encode image (compress for API limits)
            processed_path = self.preprocess_image(image_path)
            compressed_path = self._compress_image_for_api(processed_path, max_size_mb=5)
            base64_image, mime_type = self._encode_image_base64(compressed_path)
            
            if not base64_image:
                return ""
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Updated model name
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image, focusing especially on text input boxes, form fields, and editable text areas. Return only the extracted text, no descriptions or explanations."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0
            )
            
            text = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI Vision OCR: {len(text)} characters extracted")
            return text
            
        except Exception as e:
            logger.error(f"OpenAI Vision OCR failed: {e}")
            return ""
    
    def _ocr_anthropic(self, image_path: str) -> str:
        """Perform OCR using Anthropic Claude Vision API."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.config["anthropic_api_key"])
            
            # Preprocess and encode image (Anthropic has 5MB limit)
            processed_path = self.preprocess_image(image_path)
            compressed_path = self._compress_image_for_api(processed_path, max_size_mb=4)
            base64_image, mime_type = self._encode_image_base64(compressed_path)
            
            if not base64_image:
                return ""
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Updated model
                max_tokens=1000,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": "Extract all text from this image, with special focus on text input boxes, form fields, and any editable text areas. Return only the extracted text without any descriptions or commentary."
                            }
                        ]
                    }
                ]
            )
            
            text = message.content[0].text.strip()
            logger.debug(f"Anthropic Vision OCR: {len(text)} characters extracted")
            return text
            
        except Exception as e:
            logger.error(f"Anthropic Vision OCR failed: {e}")
            return ""
    
    def _ocr_xai(self, image_path: str) -> str:
        """Perform OCR using XAI Vision API."""
        try:
            # Preprocess and encode image
            processed_path = self.preprocess_image(image_path)
            compressed_path = self._compress_image_for_api(processed_path, max_size_mb=10)
            base64_image, mime_type = self._encode_image_base64(compressed_path)
            
            if not base64_image:
                return ""
            
            headers = {
                "Authorization": f"Bearer {self.config['xai_api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "grok-2-vision-1212",  # Updated model name
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all visible text from this image, especially focusing on text input fields, form boxes, and any editable text areas. Provide only the extracted text without explanations."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0
            }
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                logger.debug(f"XAI Vision OCR: {len(text)} characters extracted")
                return text
            else:
                logger.error(f"XAI API error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"XAI Vision OCR failed: {e}")
            return ""
    
    def capture_and_ocr_window(self, window_id: str) -> Dict[str, str]:
        """Capture window screenshot and perform OCR with all available services."""
        results = {}
        
        try:
            # Add capture delay to allow window to settle
            capture_delay = self.config.get("capture_delay", 3)
            logger.info(f"Waiting {capture_delay} seconds before capturing...")
            time.sleep(capture_delay)
            
            # Use Wayland-compatible screenshot method
            from wayland_screenshot import WaylandScreenshot
            
            screenshot_util = WaylandScreenshot()
            
            # Try window-specific screenshot first
            screenshot_path = None
            if window_id:
                logger.info(f"Attempting to capture window {window_id}")
                screenshot_path = screenshot_util.take_window_screenshot(window_id)
            
            # Fallback to full screenshot if window capture fails
            if not screenshot_path:
                logger.info("Window capture failed or no window ID provided, taking full screenshot")
                logger.info("📸 Please ensure the target window is visible and active")
                screenshot_path = screenshot_util.take_full_screenshot()
            
            if not screenshot_path:
                logger.error("All screenshot methods failed")
                results["error"] = "Screenshot capture failed - check permissions and display setup"
                return results
            
            logger.info(f"Screenshot captured: {screenshot_path}")
            
            # Use intelligent fallback system for primary OCR
            logger.info("Starting intelligent OCR with fallback system...")
            
            # Try to get the best result using fallback system
            primary_result = self._ocr_with_fallback(screenshot_path)
            
            if primary_result:
                results["primary"] = primary_result
                logger.info(f"✅ Primary OCR successful: {len(primary_result)} characters")
            else:
                results["primary"] = "All services failed"
                logger.error("❌ Primary OCR failed with all services")
            
            # Also try individual services for comparison (but with shorter timeouts)
            logger.info("Testing individual services for comparison...")
            
            for service in self.available_services:
                if self.available_services[service] and service != "tesseract":  # Skip tesseract for individual tests (too slow)
                    try:
                        logger.debug(f"Testing individual {service} service...")
                        text = self._ocr_single_service(screenshot_path, service)
                        if text:
                            results[service] = text
                        else:
                            results[service] = f"No text extracted by {service}"
                    except Exception as e:
                        logger.debug(f"Individual {service} test failed: {e}")
                        results[service] = f"Error: {str(e)[:100]}"  # Truncate long error messages
            
            # Always include tesseract as reference if no other services worked
            if "primary" not in results or results["primary"] == "All services failed":
                logger.info("🐌 Running Tesseract as last resort...")
                try:
                    tesseract_result = self._ocr_tesseract(screenshot_path)
                    if tesseract_result:
                        results["tesseract"] = tesseract_result
                        if "primary" not in results or results["primary"] == "All services failed":
                            results["primary"] = tesseract_result
                    else:
                        results["tesseract"] = "Tesseract failed to extract text"
                except Exception as e:
                    results["tesseract"] = f"Tesseract error: {str(e)[:100]}"
            
            # Try text box extraction (but disable OCR fallback to prevent loops)
            try:
                logger.info("Extracting text from detected input boxes...")
                
                # Temporarily disable text box detection to prevent infinite recursion
                original_setting = self.config["text_box_detection"]["enabled"]
                self.config["text_box_detection"]["enabled"] = False
                
                text_boxes = self.extract_text_boxes(screenshot_path)
                
                # Restore original setting
                self.config["text_box_detection"]["enabled"] = original_setting
                
                if text_boxes:
                    results["text_boxes"] = " | ".join(text_boxes)
                    logger.info(f"Text box extraction found {len(text_boxes)} boxes")
                else:
                    results["text_boxes"] = "No text boxes detected"
                    
            except Exception as e:
                logger.error(f"Text box extraction failed: {e}")
                results["text_boxes"] = f"Error: {str(e)[:100]}"
                # Restore original setting in case of error
                self.config["text_box_detection"]["enabled"] = True
            
        finally:
            # Cleanup
            try:
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
            except:
                pass
        
        return results
    
    def _command_available(self, command: str) -> bool:
        """Check if a command is available in the system."""
        try:
            result = subprocess.run(['which', command], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False


if __name__ == "__main__":
    # Test the enhanced OCR system
    ocr = EnhancedOCR()
    
    if len(sys.argv) > 1:
        window_id = sys.argv[1]
        results = ocr.capture_and_ocr_window(window_id)
        
        print("=== OCR Results ===")
        for service, text in results.items():
            print(f"\n--- {service.upper()} ---")
            print(text[:500] + "..." if len(text) > 500 else text)
    else:
        print("Usage: python enhanced_ocr.py <window_id>")
