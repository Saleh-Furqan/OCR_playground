#!/usr/bin/env python3
"""Enhanced OCR processor with multiple engines and advanced preprocessing"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image
import io
import logging
import re

# Import OCR engines
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedOCRProcessor:
    """Enhanced OCR processor with multiple engines and advanced preprocessing"""
    
    def __init__(self):
        self.engines = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available OCR engines"""
        
        # For now, just use Tesseract with advanced preprocessing
        # (PaddleOCR/EasyOCR can be added when packages are installed)
        
        # Tesseract is always available
        if TESSERACT_AVAILABLE:
            self.engines['tesseract'] = 'tesseract'
            logger.info("✅ Tesseract available")
        else:
            logger.error("❌ Tesseract not available - OCR will fail")
        
        # Try to initialize PaddleOCR if available with OPTIMAL settings for receipts
        if PADDLEOCR_AVAILABLE:
            try:
                # Best practices from PaddleOCR 2025 research
                # Using PaddleX 3.x API with proper parameter names
                self.engines['paddle'] = PaddleOCR(
                    use_textline_orientation=True,  # Enable text angle classification (new param name)
                    lang='en'  # English language
                )
                logger.info("✅ PaddleOCR initialized successfully with receipt-optimized settings")
            except Exception as e:
                logger.warning(f"❌ PaddleOCR initialization failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Try to initialize EasyOCR if available  
        if EASYOCR_AVAILABLE:
            try:
                self.engines['easy'] = easyocr.Reader(['en'], gpu=False)
                logger.info("✅ EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"❌ EasyOCR initialization failed: {e}")
        
        logger.info(f"🚀 Initialized {len(self.engines)} OCR engines: {list(self.engines.keys())}")
        
        if not self.engines:
            raise RuntimeError("❌ No OCR engines available!")
    
    def advanced_preprocessing(self, image_path: str) -> List[Tuple[str, np.ndarray]]:
        """Advanced preprocessing pipeline with cutting-edge techniques"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        processed_images = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Analyze image characteristics first
        image_stats = self._analyze_image_quality(gray)
        logger.info(f"📊 Image analysis: contrast={image_stats['contrast']:.2f}, "
                   f"blur={image_stats['blur']:.2f}, noise={image_stats['noise']:.2f}")
        
        # 1. Super-resolution enhancement (NEW!)
        if image_stats['blur'] > 0.3 or min(gray.shape) < 800:
            super_res = self._apply_super_resolution(gray.copy())
            processed_images.append(('super_resolution', super_res))
        
        # 2. Advanced deblurring (NEW!)
        if image_stats['blur'] > 0.4:
            deblurred = self._deblur_image(gray.copy())
            processed_images.append(('deblurred', deblurred))
        
        # 3. Resolution optimization (enhanced)
        height, width = gray.shape
        target_height = 2000 if image_stats['quality_score'] < 0.5 else 1500
        if height < target_height:
            scale_factor = target_height / height
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 4. Deskewing (improved)
        deskewed = self._deskew_image(gray.copy())
        processed_images.append(('deskewed', deskewed))
        
        # 5. Adaptive contrast enhancement
        contrast_enhanced = self._adaptive_contrast_enhancement(gray.copy(), image_stats)
        processed_images.append(('adaptive_contrast', contrast_enhanced))
        
        # 6. Advanced noise reduction
        if image_stats['noise'] > 0.3:
            advanced_denoised = self._advanced_denoise(gray.copy())
            processed_images.append(('advanced_denoised', advanced_denoised))
        else:
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            processed_images.append(('denoised', denoised))
        
        # 7. Intelligent thresholding
        smart_thresh = self._intelligent_thresholding(contrast_enhanced, image_stats)
        processed_images.append(('smart_threshold', smart_thresh))
        
        # 8. Text-optimized morphology
        text_enhanced = self._text_morphology_enhancement(smart_thresh.copy())
        processed_images.append(('text_enhanced', text_enhanced))
        
        # 9. Combined best techniques
        combined = self._create_optimal_combination(deskewed, contrast_enhanced, image_stats)
        processed_images.append(('optimal_combined', combined))
        
        return processed_images
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Advanced automatic deskewing for rotated receipts"""
        try:
            # Method 1: Hough Line Transform
            angle = self._detect_rotation_angle_hough(image)
            if angle is not None:
                logger.info(f"🔄 Detected rotation angle: {angle:.2f}°")
                return self._rotate_image(image, angle)
            
            # Method 2: Projection Profile (fallback)
            angle = self._detect_rotation_angle_projection(image)
            if angle is not None:
                logger.info(f"🔄 Detected rotation angle (projection): {angle:.2f}°")
                return self._rotate_image(image, angle)
                
        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
        
        return image
    
    def _detect_rotation_angle_hough(self, image: np.ndarray) -> Optional[float]:
        """Detect rotation angle using Hough Line Transform"""
        try:
            # Edge detection with adjusted parameters for receipts
            edges = cv2.Canny(image, 30, 100, apertureSize=3)
            
            # Hough line detection with lower threshold for receipts
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=50)
            
            if lines is not None and len(lines) > 5:  # Need at least 5 lines
                angles = []
                
                for line in lines:
                    rho, theta = line[0]
                    # Convert to degrees
                    angle_deg = np.degrees(theta) - 90
                    
                    # Focus on near-horizontal and near-vertical lines
                    if abs(angle_deg) < 45 or abs(angle_deg - 90) < 45:
                        # Normalize to -45 to +45 range
                        if angle_deg > 45:
                            angle_deg -= 90
                        elif angle_deg < -45:
                            angle_deg += 90
                        angles.append(angle_deg)
                
                if len(angles) >= 3:  # Need enough samples
                    # Use median to avoid outliers
                    median_angle = np.median(angles)
                    
                    # Only correct significant rotations
                    if abs(median_angle) > 0.5:
                        return median_angle
                        
        except Exception as e:
            logger.warning(f"Hough angle detection failed: {e}")
        
        return None
    
    def _detect_rotation_angle_projection(self, image: np.ndarray) -> Optional[float]:
        """Detect rotation angle using projection profile method"""
        try:
            # Try angles from -20 to +20 degrees
            best_angle = 0
            max_variance = 0
            
            for angle in np.arange(-20, 21, 0.5):  # 0.5 degree steps
                rotated = self._rotate_image(image, angle)
                
                # Calculate horizontal projection variance
                horizontal_projection = np.sum(rotated, axis=1)
                variance = np.var(horizontal_projection)
                
                if variance > max_variance:
                    max_variance = variance
                    best_angle = angle
            
            # Only use if angle is significant
            if abs(best_angle) > 0.5:
                return best_angle
                
        except Exception as e:
            logger.warning(f"Projection angle detection failed: {e}")
        
        return None
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by given angle"""
        try:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            
            # Create rotation matrix
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Calculate new image dimensions to avoid clipping
            cos = np.abs(rotation_matrix[0, 0])
            sin = np.abs(rotation_matrix[0, 1])
            new_w = int((h * sin) + (w * cos))
            new_h = int((h * cos) + (w * sin))
            
            # Adjust the rotation matrix to take into account translation
            rotation_matrix[0, 2] += (new_w / 2) - center[0]
            rotation_matrix[1, 2] += (new_h / 2) - center[1]
            
            # Perform rotation with white background
            rotated = cv2.warpAffine(
                image, rotation_matrix, (new_w, new_h),
                flags=cv2.INTER_CUBIC, 
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=255  # White background for receipts
            )
            
            return rotated
            
        except Exception as e:
            logger.warning(f"Image rotation failed: {e}")
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)"""
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            return enhanced
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}")
            return image
    
    def _analyze_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """Analyze image quality characteristics"""
        try:
            # Calculate contrast using standard deviation
            contrast = np.std(image) / 255.0
            
            # Calculate blur using Laplacian variance
            laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
            blur_score = 1.0 / (1.0 + laplacian_var / 1000.0)  # Normalize
            
            # Estimate noise level
            noise_score = np.mean(cv2.absdiff(image, cv2.medianBlur(image, 3))) / 255.0
            
            # Overall quality score
            quality_score = (contrast + (1 - blur_score) + (1 - noise_score)) / 3
            
            return {
                'contrast': contrast,
                'blur': blur_score,
                'noise': noise_score,
                'quality_score': quality_score,
                'mean_intensity': np.mean(image) / 255.0,
                'histogram_spread': (np.max(image) - np.min(image)) / 255.0
            }
            
        except Exception as e:
            logger.warning(f"Image quality analysis failed: {e}")
            return {
                'contrast': 0.5, 'blur': 0.5, 'noise': 0.5, 
                'quality_score': 0.5, 'mean_intensity': 0.5, 
                'histogram_spread': 0.5
            }
    
    def _apply_super_resolution(self, image: np.ndarray) -> np.ndarray:
        """Apply super-resolution using OpenCV's DNN Super Resolution"""
        try:
            # Simple super-resolution using INTER_LANCZOS4 with sharpening
            height, width = image.shape
            
            # Scale up by 2x
            upscaled = cv2.resize(image, (width * 2, height * 2), interpolation=cv2.INTER_LANCZOS4)
            
            # Apply unsharp masking for sharpening
            blurred = cv2.GaussianBlur(upscaled, (0, 0), 2.0)
            sharpened = cv2.addWeighted(upscaled, 2.0, blurred, -1.0, 0)
            
            return sharpened
            
        except Exception as e:
            logger.warning(f"Super-resolution failed: {e}")
            return image
    
    def _deblur_image(self, image: np.ndarray) -> np.ndarray:
        """Advanced deblurring using Wiener filtering approximation"""
        try:
            # Convert to float
            image_float = image.astype(np.float32) / 255.0
            
            # Apply Fourier domain deblurring
            f_transform = np.fft.fft2(image_float)
            
            # Create a simple deblurring kernel (motion blur compensation)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
            kernel_fft = np.fft.fft2(kernel, s=image.shape)
            
            # Apply Wiener filter approximation
            deblurred_fft = f_transform * np.conj(kernel_fft) / (np.abs(kernel_fft)**2 + 0.01)
            deblurred = np.real(np.fft.ifft2(deblurred_fft))
            
            # Convert back and clip
            result = np.clip(deblurred * 255, 0, 255).astype(np.uint8)
            return result
            
        except Exception as e:
            logger.warning(f"Deblurring failed: {e}")
            # Fallback to simple sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            return cv2.filter2D(image, -1, kernel)
    
    def _adaptive_contrast_enhancement(self, image: np.ndarray, stats: Dict[str, float]) -> np.ndarray:
        """Adaptive contrast enhancement based on image characteristics"""
        try:
            if stats['contrast'] < 0.3:  # Low contrast
                # Use CLAHE with aggressive settings
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(image)
            elif stats['contrast'] > 0.7:  # High contrast
                # Use gentle histogram equalization
                enhanced = cv2.equalizeHist(image)
            else:  # Medium contrast
                # Use standard CLAHE
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(image)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Adaptive contrast enhancement failed: {e}")
            return image
    
    def _advanced_denoise(self, image: np.ndarray) -> np.ndarray:
        """Advanced denoising using Non-Local Means"""
        try:
            # Use Non-Local Means Denoising
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            return denoised
            
        except Exception as e:
            logger.warning(f"Advanced denoising failed: {e}")
            # Fallback to bilateral filter
            return cv2.bilateralFilter(image, 9, 75, 75)
    
    def _intelligent_thresholding(self, image: np.ndarray, stats: Dict[str, float]) -> np.ndarray:
        """Intelligent thresholding based on image characteristics"""
        try:
            if stats['mean_intensity'] < 0.3:  # Dark image
                # Use inverse threshold
                _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                # Invert back
                thresh = cv2.bitwise_not(thresh)
            elif stats['histogram_spread'] < 0.4:  # Low dynamic range
                # Use adaptive threshold with larger neighborhood
                thresh = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                             cv2.THRESH_BINARY, 31, 15)
            else:  # Normal image
                # Use Otsu with preprocessing
                blurred = cv2.GaussianBlur(image, (5, 5), 0)
                _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
            
        except Exception as e:
            logger.warning(f"Intelligent thresholding failed: {e}")
            return image
    
    def _text_morphology_enhancement(self, image: np.ndarray) -> np.ndarray:
        """Text-specific morphological operations"""
        try:
            # Remove small noise
            noise_removal_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            cleaned = cv2.morphologyEx(image, cv2.MORPH_OPEN, noise_removal_kernel)
            
            # Connect broken characters
            connect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
            connected = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, connect_kernel)
            
            # Fill gaps in characters
            fill_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            filled = cv2.morphologyEx(connected, cv2.MORPH_CLOSE, fill_kernel)
            
            return filled
            
        except Exception as e:
            logger.warning(f"Text morphology enhancement failed: {e}")
            return image
    
    def _create_optimal_combination(self, deskewed: np.ndarray, contrast_enhanced: np.ndarray, 
                                   stats: Dict[str, float]) -> np.ndarray:
        """Create optimal combination of preprocessing techniques"""
        try:
            # Start with deskewed image
            result = deskewed.copy()
            
            # Apply contrast enhancement if needed
            if stats['contrast'] < 0.4:
                result = self._adaptive_contrast_enhancement(result, stats)
            
            # Apply denoising if needed
            if stats['noise'] > 0.3:
                result = cv2.fastNlMeansDenoising(result, None, 8, 7, 21)
            
            # Apply intelligent thresholding
            result = self._intelligent_thresholding(result, stats)
            
            # Final morphological cleanup
            result = self._text_morphology_enhancement(result)
            
            return result
            
        except Exception as e:
            logger.warning(f"Optimal combination failed: {e}")
            return deskewed
    
    def extract_text_paddle(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using PaddleOCR with proper predict() method (PaddleX 3.x API)"""
        try:
            # PaddleX 3.x uses predict() method
            # Accepts numpy array or image path
            # Returns: [OCRResult dict with 'rec_texts' and 'rec_scores']

            # Save numpy array to temp file (PaddleX 3.x predict works better with file paths)
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                pil_img = Image.fromarray(image)
                pil_img.save(tmp.name)
                tmp_path = tmp.name

            try:
                # Call predict() method with textline orientation
                results = self.engines['paddle'].predict(tmp_path, use_textline_orientation=True)

                if results and len(results) > 0:
                    # results[0] is OCRResult dict
                    result = results[0]

                    # Extract text and scores from new API
                    text_lines = result.get('rec_texts', [])
                    confidences = result.get('rec_scores', [])

                    if text_lines and confidences:
                        # Filter low confidence
                        filtered_lines = []
                        filtered_confs = []
                        for text, conf in zip(text_lines, confidences):
                            if conf > 0.5:  # Filter low confidence
                                filtered_lines.append(text)
                                filtered_confs.append(conf)

                        if filtered_lines:
                            # Join with newlines to preserve structure
                            full_text = '\n'.join(filtered_lines)
                            avg_confidence = sum(filtered_confs) / len(filtered_confs) if filtered_confs else 0

                            logger.info(f"  PaddleOCR extracted {len(filtered_lines)} lines, avg confidence: {avg_confidence:.2f}")
                            return full_text, avg_confidence

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.warning(f"PaddleOCR extraction failed: {e}")
            import traceback
            traceback.print_exc()

        return "", 0.0
    
    def extract_text_easy(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using EasyOCR"""
        try:
            result = self.engines['easy'].readtext(image)
            
            if result:
                text_lines = []
                total_confidence = 0
                
                for (bbox, text, confidence) in result:
                    text_lines.append(text)
                    total_confidence += confidence
                
                full_text = '\n'.join(text_lines)
                avg_confidence = total_confidence / len(result) if result else 0
                
                return full_text, avg_confidence
            
        except Exception as e:
            logger.warning(f"EasyOCR extraction failed: {e}")
        
        return "", 0.0
    
    def extract_text_tesseract(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using Tesseract with advanced configurations"""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)
            
            # Try multiple Tesseract configurations optimized for receipts
            configs = [
                '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$.,:/()- ',
                '--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$.,:/()- ',
                '--oem 3 --psm 7',
                '--oem 3 --psm 8',
                '--oem 3 --psm 11',
                '--oem 3 --psm 12',
                '--oem 3 --psm 6',
                '--oem 3 --psm 4'
            ]
            
            best_text = ""
            best_confidence = 0
            
            for config in configs:
                try:
                    # Get text with confidence
                    data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
                    
                    text_lines = []
                    confidences = []
                    
                    for i, conf in enumerate(data['conf']):
                        if int(conf) > 30:  # Only consider reasonably confident detections
                            text = data['text'][i].strip()
                            if text and len(text) > 1:  # Ignore single characters
                                text_lines.append(text)
                                confidences.append(int(conf))
                    
                    if text_lines:
                        full_text = ' '.join(text_lines)
                        avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0
                        
                        # Use receipt-specific confidence scoring
                        receipt_confidence = self._calculate_receipt_confidence(full_text)
                        combined_confidence = (avg_confidence + receipt_confidence) / 2
                        
                        if combined_confidence > best_confidence:
                            best_confidence = combined_confidence
                            best_text = full_text
                            
                except Exception:
                    continue
            
            return best_text, best_confidence
            
        except Exception as e:
            logger.warning(f"Tesseract extraction failed: {e}")
        
        return "", 0.0
    
    def _calculate_receipt_confidence(self, text: str) -> float:
        """Calculate receipt-specific confidence score"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # Check for price patterns
        price_matches = len(re.findall(r'\$?\d+\.\d{2}', text))
        score += min(price_matches * 0.2, 0.6)
        
        # Check for receipt keywords
        receipt_words = ['total', 'subtotal', 'tax', 'amount', 'receipt', 'store', 'date', 'time']
        word_matches = sum(1 for word in receipt_words if word in text_lower)
        score += min(word_matches * 0.05, 0.3)
        
        # Check for reasonable text length
        if 50 < len(text) < 2000:
            score += 0.1
        
        return min(score, 1.0)
    
    def extract_text_multi_engine(self, image_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text using multiple OCR engines and return best result"""
        
        # Get preprocessed images
        processed_images = self.advanced_preprocessing(image_path)
        
        best_result = {"text": "", "confidence": 0.0, "engine": "", "preprocessing": ""}
        all_results = []
        
        # Try each preprocessing method with each OCR engine
        for prep_name, processed_img in processed_images:
            
            # Try PaddleOCR
            if 'paddle' in self.engines:
                text, conf = self.extract_text_paddle(processed_img)
                result = {
                    "text": text,
                    "confidence": conf,
                    "engine": "paddle",
                    "preprocessing": prep_name,
                    "length": len(text.strip())
                }
                all_results.append(result)
                
                # Use better confidence OR longer text
                if (conf > best_result["confidence"] and len(text.strip()) > 5) or \
                   (len(text.strip()) > len(best_result["text"].strip()) and conf > 0.1):
                    best_result = result
            
            # Try EasyOCR
            if 'easy' in self.engines:
                text, conf = self.extract_text_easy(processed_img)
                result = {
                    "text": text,
                    "confidence": conf,
                    "engine": "easy",
                    "preprocessing": prep_name,
                    "length": len(text.strip())
                }
                all_results.append(result)
                
                # Use better confidence OR longer text
                if (conf > best_result["confidence"] and len(text.strip()) > 5) or \
                   (len(text.strip()) > len(best_result["text"].strip()) and conf > 0.1):
                    best_result = result
            
            # Try Tesseract
            if 'tesseract' in self.engines:
                text, conf = self.extract_text_tesseract(processed_img)
                result = {
                    "text": text,
                    "confidence": conf,
                    "engine": "tesseract", 
                    "preprocessing": prep_name,
                    "length": len(text.strip())
                }
                all_results.append(result)
                
                # Use better confidence OR longer text
                if (conf > best_result["confidence"] and len(text.strip()) > 5) or \
                   (len(text.strip()) > len(best_result["text"].strip()) and conf > 0.1):
                    best_result = result
        
        # Log results with more detail
        logger.info(f"🎯 Best result: {best_result['engine']} + {best_result['preprocessing']} "
                   f"(confidence: {best_result['confidence']:.3f}, length: {best_result.get('length', 0)})")
        logger.info(f"📊 Total attempts: {len(all_results)}, Best text length: {len(best_result['text'])}")
        
        # Return best text and metadata
        metadata = {
            "best_result": best_result,
            "all_results": all_results,
            "engines_used": list(self.engines.keys()),
            "total_attempts": len(all_results)
        }
        
        return best_result["text"], metadata