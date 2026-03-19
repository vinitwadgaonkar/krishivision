"""
OCR processor for Indian Soil Health Cards.
Extracts nutrient values from card images using Tesseract OCR + regex parsing.
"""

import re
import io
from PIL import Image, ImageFilter, ImageEnhance

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def preprocess_image(image_bytes):
    """Enhance image for better OCR accuracy."""
    img = Image.open(io.BytesIO(image_bytes))

    if img.mode != 'RGB':
        img = img.convert('RGB')

    img = img.convert('L')

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)

    width, height = img.size
    if width < 1500:
        scale = 1500 / width
        img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

    img = img.point(lambda x: 0 if x < 140 else 255)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    return img


def extract_text_from_image(image_bytes):
    """Run Tesseract OCR on the image."""
    if not TESSERACT_AVAILABLE:
        return None, "Tesseract not installed"

    try:
        img = preprocess_image(image_bytes)
        custom_config = r'--oem 3 --psm 6 -l eng'
        text = pytesseract.image_to_string(img, config=custom_config)
        return text, None
    except Exception as e:
        return None, str(e)


FIELD_PATTERNS = {
    'nitrogen': [
        r'(?:available\s*)?nitrogen[:\s]*(\d+\.?\d*)\s*(?:kg|Kg)',
        r'nitrogen[:\s]*(\d+\.?\d*)',
        r'N[:\s]*(\d+\.?\d*)\s*(?:kg|Kg)',
    ],
    'phosphorus': [
        r'(?:available\s*)?phosphorus[:\s]*(\d+\.?\d*)\s*(?:kg|Kg)',
        r'phosphorus[:\s]*(\d+\.?\d*)',
        r'P[:\s]*(\d+\.?\d*)\s*(?:kg|Kg)',
    ],
    'potassium': [
        r'(?:available\s*)?potassium[:\s]*(\d+\.?\d*)\s*(?:kg|Kg)',
        r'potassium[:\s]*(\d+\.?\d*)',
        r'K[:\s]*(\d+\.?\d*)\s*(?:kg|Kg)',
    ],
    'pH': [
        r'(?:soil\s*)?pH[:\s]*(\d+\.?\d*)',
        r'pH\s*(?:value)?[:\s]*(\d+\.?\d*)',
    ],
    'EC': [
        r'EC[:\s]*(\d+\.?\d*)\s*(?:dS|ds)',
        r'(?:electrical\s*)?conductivity[:\s]*(\d+\.?\d*)',
    ],
    'OC': [
        r'(?:organic\s*)?carbon[:\s]*(\d+\.?\d*)\s*(?:w|%)',
        r'organic\s*(?:carbon|matter)[:\s]*(\d+\.?\d*)',
        r'OC[:\s]*(\d+\.?\d*)',
    ],
    'sulphur': [
        r'(?:available\s*)?sulphur[:\s]*(\d+\.?\d*)',
        r'(?:available\s*)?sulfur[:\s]*(\d+\.?\d*)',
        r'S[:\s]*(\d+\.?\d*)\s*(?:mg|ppm)',
    ],
    'zinc': [
        r'(?:available\s*)?zinc[:\s]*(\d+\.?\d*)',
        r'Zn[:\s]*(\d+\.?\d*)',
    ],
    'boron': [
        r'(?:available\s*)?boron[:\s]*(\d+\.?\d*)',
        r'B[:\s]*(\d+\.?\d*)\s*(?:mg|ppm)',
    ],
    'iron': [
        r'(?:available\s*)?iron[:\s]*(\d+\.?\d*)',
        r'Fe[:\s]*(\d+\.?\d*)',
    ],
    'copper': [
        r'(?:available\s*)?copper[:\s]*(\d+\.?\d*)',
        r'Cu[:\s]*(\d+\.?\d*)',
    ],
    'manganese': [
        r'(?:available\s*)?manganese[:\s]*(\d+\.?\d*)',
        r'Mn[:\s]*(\d+\.?\d*)',
    ],
}

FIELD_TO_KEY = {
    'nitrogen': 'N', 'phosphorus': 'P', 'potassium': 'K',
    'pH': 'pH', 'EC': 'EC', 'OC': 'OC',
    'sulphur': 'S', 'zinc': 'Zn', 'boron': 'B',
    'iron': 'Fe', 'copper': 'Cu', 'manganese': 'Mn',
}


def parse_soil_values(text):
    """Extract soil parameter values from OCR text using regex patterns."""
    results = {}
    confidence = {}

    text_lower = text.lower()

    for field, patterns in FIELD_PATTERNS.items():
        key = FIELD_TO_KEY[field]
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text if field == 'pH' else text_lower, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if _validate_range(key, value):
                        results[key] = value
                        confidence[key] = round(1.0 - i * 0.2, 2)
                        break
                except (ValueError, IndexError):
                    continue

    crop_patterns = [
        r'(?:selected\s*)?crop[:\s]*([A-Za-z\s\(\)]+?)(?:\n|$)',
        r'(?:crop\s*)?(?:1|name)[:\s]*([A-Za-z\s]+?)(?:\n|$)',
    ]
    for pattern in crop_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            crop = match.group(1).strip()
            if len(crop) > 2:
                results['crop'] = crop
                break

    soil_health_patterns = [
        r'(?:soil\s*health\s*index|SQI)[:\s]*(\d+\.?\d*)',
        r'SQI[:\s]*(\d+\.?\d*)',
    ]
    for pattern in soil_health_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            results['original_SQI'] = float(match.group(1))
            break

    return results, confidence


def _validate_range(key, value):
    """Sanity check extracted values against plausible ranges."""
    ranges = {
        'pH': (2.0, 12.0), 'EC': (0.0, 10.0), 'OC': (0.0, 5.0),
        'N': (0, 1000), 'P': (0, 500), 'K': (0, 1000),
        'S': (0, 200), 'Zn': (0, 50), 'B': (0, 20),
        'Fe': (0, 200), 'Cu': (0, 50), 'Mn': (0, 100),
    }
    low, high = ranges.get(key, (0, 10000))
    return low <= value <= high


def process_soil_card_image(image_bytes):
    """Full pipeline: image → OCR → parsed values."""
    text, error = extract_text_from_image(image_bytes)
    if error:
        return None, None, error

    values, confidence = parse_soil_values(text)
    return values, confidence, None
