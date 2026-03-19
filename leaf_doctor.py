"""
Leaf/Crop Image Analysis for Nutrient Deficiency Detection.
Uses color distribution, pattern analysis, and symptom mapping
based on established plant pathology principles.
"""

import io
import numpy as np
from PIL import Image


DEFICIENCY_PROFILES = {
    'Nitrogen': {
        'symptoms': 'Overall yellowing starting from older/lower leaves',
        'visual': 'Uniform pale yellow-green color',
        'severity_thresholds': {'mild': 0.3, 'moderate': 0.5, 'severe': 0.7},
        'treatment': 'Urea: 150-200 Kg/Ha or DAP: 80-100 Kg/Ha',
    },
    'Phosphorus': {
        'symptoms': 'Purple or reddish coloration on leaves and stems',
        'visual': 'Dark green with purple/red tints, especially on undersides',
        'severity_thresholds': {'mild': 0.3, 'moderate': 0.5, 'severe': 0.7},
        'treatment': 'SSP: 200-250 Kg/Ha or DAP: 80-100 Kg/Ha',
    },
    'Potassium': {
        'symptoms': 'Brown/burnt leaf margins and tips (marginal scorch)',
        'visual': 'Browning at leaf edges progressing inward',
        'severity_thresholds': {'mild': 0.3, 'moderate': 0.5, 'severe': 0.7},
        'treatment': 'MOP: 80-120 Kg/Ha',
    },
    'Iron': {
        'symptoms': 'Interveinal chlorosis on young/new leaves',
        'visual': 'Yellow between veins while veins stay green',
        'severity_thresholds': {'mild': 0.25, 'moderate': 0.45, 'severe': 0.65},
        'treatment': 'Ferrous Sulphate: 20-25 Kg/Ha (foliar spray 0.5%)',
    },
    'Zinc': {
        'symptoms': 'Small, narrow leaves with interveinal chlorosis',
        'visual': 'Stunted growth, mottled yellow-green pattern',
        'severity_thresholds': {'mild': 0.25, 'moderate': 0.45, 'severe': 0.65},
        'treatment': 'Zinc Sulphate: 20-25 Kg/Ha (foliar spray 0.2%)',
    },
    'Manganese': {
        'symptoms': 'Interveinal chlorosis with grayish spots on older leaves',
        'visual': 'Checkered yellow-green pattern with dead spots',
        'severity_thresholds': {'mild': 0.25, 'moderate': 0.45, 'severe': 0.65},
        'treatment': 'Manganese Sulphate: 10-15 Kg/Ha',
    },
    'Sulphur': {
        'symptoms': 'Uniform yellowing of new/young leaves',
        'visual': 'Light yellow-green, similar to nitrogen but on NEW leaves',
        'severity_thresholds': {'mild': 0.3, 'moderate': 0.5, 'severe': 0.7},
        'treatment': 'Bentonite Sulphur: 10-15 Kg/Ha or Gypsum: 200 Kg/Ha',
    },
    'Boron': {
        'symptoms': 'Deformed, thickened, brittle leaves; hollow stems',
        'visual': 'Distorted leaf shape, corky patches',
        'severity_thresholds': {'mild': 0.3, 'moderate': 0.5, 'severe': 0.7},
        'treatment': 'Borax: 5-10 Kg/Ha (foliar spray 0.2%)',
    },
}

DISEASE_INDICATORS = {
    'Leaf Spot': {
        'description': 'Dark circular spots on leaves — may be fungal or bacterial',
        'treatment': 'Apply copper-based fungicide (Copper Oxychloride 3g/L)',
    },
    'Leaf Blight': {
        'description': 'Large brown/tan dead areas spreading from edges or tips',
        'treatment': 'Apply Mancozeb (2.5g/L) or Carbendazim (1g/L)',
    },
    'Rust': {
        'description': 'Orange-brown powdery pustules on leaf undersides',
        'treatment': 'Apply Propiconazole (1ml/L) or Hexaconazole (2ml/L)',
    },
    'Powdery Mildew': {
        'description': 'White powdery coating on leaf surfaces',
        'treatment': 'Apply Sulphur dust or Karathane (1ml/L)',
    },
}


def analyze_leaf_image(image_bytes):
    """Full leaf health analysis from a photo."""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img_array = np.array(img)

    leaf_mask = _segment_leaf(img_array)
    if leaf_mask.sum() < 100:
        leaf_pixels = img_array.reshape(-1, 3)
    else:
        leaf_pixels = img_array[leaf_mask]

    color_analysis = _analyze_leaf_colors(leaf_pixels, img_array, leaf_mask)
    deficiencies = _detect_deficiencies(color_analysis, img_array, leaf_mask)
    diseases = _detect_diseases(color_analysis, img_array, leaf_mask)
    health_score = _compute_health_score(color_analysis, deficiencies, diseases)

    overall = 'Healthy' if health_score > 0.7 else 'Moderate Stress' if health_score > 0.4 else 'Severe Stress'

    return {
        'health_score': round(health_score, 2),
        'overall_status': overall,
        'color_analysis': color_analysis,
        'deficiencies': deficiencies,
        'diseases': diseases,
        'recommendations': _generate_recommendations(deficiencies, diseases),
    }


def _segment_leaf(img_array):
    """Simple green-based leaf segmentation."""
    r, g, b = img_array[..., 0].astype(float), img_array[..., 1].astype(float), img_array[..., 2].astype(float)
    green_dominance = g - (r + b) / 2
    excess_green = 2 * g - r - b
    mask = (excess_green > 10) | (green_dominance > 5)
    yellow_green = (r > 100) & (g > 100) & (b < 100) & (g > b)
    mask = mask | yellow_green
    return mask


def _analyze_leaf_colors(leaf_pixels, full_img, mask):
    """Analyze color distribution of leaf area."""
    r = leaf_pixels[:, 0].astype(float)
    g = leaf_pixels[:, 1].astype(float)
    b = leaf_pixels[:, 2].astype(float)

    total = len(leaf_pixels)
    green_pct = np.sum((g > r) & (g > b)) / total * 100
    yellow_pct = np.sum((r > 150) & (g > 150) & (b < 100)) / total * 100
    brown_pct = np.sum((r > 100) & (g < 100) & (b < 80)) / total * 100
    purple_pct = np.sum((r > g) & (b > g) & (r > 80)) / total * 100
    white_pct = np.sum((r > 200) & (g > 200) & (b > 200)) / total * 100
    dark_pct = np.sum((r < 60) & (g < 60) & (b < 60)) / total * 100

    brightness = float(np.mean(r * 0.299 + g * 0.587 + b * 0.114))
    greenness = float(np.mean(g) - (np.mean(r) + np.mean(b)) / 2)
    redness = float(np.mean(r) - np.mean(g))

    return {
        'green_percent': round(green_pct, 1),
        'yellow_percent': round(yellow_pct, 1),
        'brown_percent': round(brown_pct, 1),
        'purple_percent': round(purple_pct, 1),
        'white_percent': round(white_pct, 1),
        'dark_percent': round(dark_pct, 1),
        'brightness': round(brightness, 1),
        'greenness_index': round(greenness, 1),
        'redness_index': round(redness, 1),
        'mean_rgb': [int(np.mean(r)), int(np.mean(g)), int(np.mean(b))],
    }


def _detect_deficiencies(colors, img_array, mask):
    """Detect nutrient deficiencies from leaf color patterns."""
    detected = []

    # Nitrogen: overall yellowing
    if colors['yellow_percent'] > 15 or (colors['greenness_index'] < 10 and colors['brightness'] > 120):
        score = min(1.0, colors['yellow_percent'] / 40 + max(0, 15 - colors['greenness_index']) / 30)
        severity = _get_severity(score, 'Nitrogen')
        detected.append({
            'nutrient': 'Nitrogen',
            'confidence': round(min(0.95, score), 2),
            'severity': severity,
            'symptoms': DEFICIENCY_PROFILES['Nitrogen']['symptoms'],
            'evidence': f"{colors['yellow_percent']:.0f}% yellow, greenness={colors['greenness_index']:.0f}",
            'treatment': DEFICIENCY_PROFILES['Nitrogen']['treatment'],
        })

    # Phosphorus: purple/red tint
    if colors['purple_percent'] > 5 or (colors['redness_index'] > 15 and colors['green_percent'] > 30):
        score = min(1.0, colors['purple_percent'] / 20 + max(0, colors['redness_index'] - 10) / 40)
        severity = _get_severity(score, 'Phosphorus')
        detected.append({
            'nutrient': 'Phosphorus',
            'confidence': round(min(0.95, score), 2),
            'severity': severity,
            'symptoms': DEFICIENCY_PROFILES['Phosphorus']['symptoms'],
            'evidence': f"{colors['purple_percent']:.0f}% purple, redness={colors['redness_index']:.0f}",
            'treatment': DEFICIENCY_PROFILES['Phosphorus']['treatment'],
        })

    # Potassium: brown edges (marginal necrosis)
    edge_brown = _detect_edge_browning(img_array, mask)
    if edge_brown > 0.2 or colors['brown_percent'] > 10:
        score = min(1.0, edge_brown + colors['brown_percent'] / 30)
        severity = _get_severity(score, 'Potassium')
        detected.append({
            'nutrient': 'Potassium',
            'confidence': round(min(0.95, score), 2),
            'severity': severity,
            'symptoms': DEFICIENCY_PROFILES['Potassium']['symptoms'],
            'evidence': f"{colors['brown_percent']:.0f}% brown, edge_score={edge_brown:.2f}",
            'treatment': DEFICIENCY_PROFILES['Potassium']['treatment'],
        })

    # Iron/Zinc/Manganese: interveinal chlorosis
    chlorosis = _detect_interveinal_chlorosis(img_array, mask)
    if chlorosis > 0.25:
        score = min(1.0, chlorosis)
        for nutrient in ['Iron', 'Zinc', 'Manganese']:
            detected.append({
                'nutrient': nutrient,
                'confidence': round(min(0.85, score * 0.7), 2),
                'severity': _get_severity(score * 0.7, nutrient),
                'symptoms': DEFICIENCY_PROFILES[nutrient]['symptoms'],
                'evidence': f"interveinal_chlorosis={chlorosis:.2f}",
                'treatment': DEFICIENCY_PROFILES[nutrient]['treatment'],
            })

    # Sulphur: pale new growth
    if colors['brightness'] > 140 and colors['greenness_index'] < 5 and colors['yellow_percent'] > 10:
        score = min(1.0, (colors['brightness'] - 120) / 80 + colors['yellow_percent'] / 50)
        detected.append({
            'nutrient': 'Sulphur',
            'confidence': round(min(0.8, score * 0.6), 2),
            'severity': _get_severity(score * 0.6, 'Sulphur'),
            'symptoms': DEFICIENCY_PROFILES['Sulphur']['symptoms'],
            'evidence': f"bright={colors['brightness']:.0f}, greenness={colors['greenness_index']:.0f}",
            'treatment': DEFICIENCY_PROFILES['Sulphur']['treatment'],
        })

    return sorted(detected, key=lambda x: -x['confidence'])


def _detect_diseases(colors, img_array, mask):
    """Detect potential diseases from leaf appearance."""
    detected = []

    spots = _detect_spots(img_array, mask)
    if spots > 0.15:
        detected.append({
            'disease': 'Leaf Spot',
            'confidence': round(min(0.9, spots), 2),
            'description': DISEASE_INDICATORS['Leaf Spot']['description'],
            'treatment': DISEASE_INDICATORS['Leaf Spot']['treatment'],
        })

    if colors['brown_percent'] > 20 and colors['dark_percent'] > 10:
        score = min(0.9, (colors['brown_percent'] - 15) / 30 + colors['dark_percent'] / 25)
        detected.append({
            'disease': 'Leaf Blight',
            'confidence': round(score, 2),
            'description': DISEASE_INDICATORS['Leaf Blight']['description'],
            'treatment': DISEASE_INDICATORS['Leaf Blight']['treatment'],
        })

    if colors['white_percent'] > 10:
        detected.append({
            'disease': 'Powdery Mildew',
            'confidence': round(min(0.85, colors['white_percent'] / 25), 2),
            'description': DISEASE_INDICATORS['Powdery Mildew']['description'],
            'treatment': DISEASE_INDICATORS['Powdery Mildew']['treatment'],
        })

    return sorted(detected, key=lambda x: -x['confidence'])


def _detect_edge_browning(img_array, mask):
    """Detect browning at leaf edges (potassium deficiency indicator)."""
    h, w = img_array.shape[:2]
    edge_band = max(1, min(h, w) // 15)

    edges = np.zeros((h, w), dtype=bool)
    if mask.any():
        for i in range(h):
            row_mask = mask[i]
            if row_mask.any():
                left = np.argmax(row_mask)
                right = w - 1 - np.argmax(row_mask[::-1])
                edges[i, left:left + edge_band] = True
                edges[i, max(0, right - edge_band):right + 1] = True
    else:
        edges[:edge_band, :] = True
        edges[-edge_band:, :] = True
        edges[:, :edge_band] = True
        edges[:, -edge_band:] = True

    edge_pixels = img_array[edges]
    if len(edge_pixels) == 0:
        return 0.0

    r, g, b = edge_pixels[:, 0].astype(float), edge_pixels[:, 1].astype(float), edge_pixels[:, 2].astype(float)
    brown = np.sum((r > 100) & (g < 100) & (b < 80)) / len(edge_pixels)
    return float(brown)


def _detect_interveinal_chlorosis(img_array, mask):
    """Detect yellow between green veins pattern."""
    if not mask.any():
        return 0.0

    leaf_pixels = img_array[mask].astype(float)
    r, g, b = leaf_pixels[:, 0], leaf_pixels[:, 1], leaf_pixels[:, 2]

    is_green_vein = (g > r + 10) & (g > b + 10) & (g > 80)
    is_yellow = (r > 120) & (g > 120) & (b < 100) & (np.abs(r - g) < 40)

    total = len(leaf_pixels)
    if total == 0:
        return 0.0

    green_frac = np.sum(is_green_vein) / total
    yellow_frac = np.sum(is_yellow) / total

    if green_frac > 0.1 and yellow_frac > 0.1:
        return min(1.0, (green_frac + yellow_frac) * 1.5)
    return 0.0


def _detect_spots(img_array, mask):
    """Detect dark spots (potential disease)."""
    if not mask.any():
        gray = np.mean(img_array.astype(float), axis=2)
        leaf_gray = gray
    else:
        gray = np.mean(img_array.astype(float), axis=2)
        leaf_gray = gray[mask]

    if len(leaf_gray) == 0:
        return 0.0

    mean_val = np.mean(leaf_gray)
    dark_threshold = mean_val * 0.5
    dark_spots = np.sum(leaf_gray < dark_threshold) / len(leaf_gray)

    return float(dark_spots)


def _get_severity(score, nutrient):
    thresholds = DEFICIENCY_PROFILES[nutrient]['severity_thresholds']
    if score >= thresholds['severe']:
        return 'Severe'
    elif score >= thresholds['moderate']:
        return 'Moderate'
    elif score >= thresholds['mild']:
        return 'Mild'
    return 'Possible'


def _compute_health_score(colors, deficiencies, diseases):
    base = 1.0
    green_ratio = min(1.0, colors['green_percent'] / 60)
    base *= (0.3 + 0.7 * green_ratio)

    for d in deficiencies:
        penalty = d['confidence'] * 0.15
        base -= penalty

    for d in diseases:
        penalty = d['confidence'] * 0.2
        base -= penalty

    return max(0.0, min(1.0, base))


def _generate_recommendations(deficiencies, diseases):
    recs = []
    if not deficiencies and not diseases:
        recs.append({
            'type': 'info',
            'message': 'Leaf appears healthy! Continue current nutrient management.',
        })
        return recs

    for d in deficiencies:
        recs.append({
            'type': 'deficiency',
            'nutrient': d['nutrient'],
            'severity': d['severity'],
            'action': d['treatment'],
        })

    for d in diseases:
        recs.append({
            'type': 'disease',
            'disease': d['disease'],
            'action': d['treatment'],
        })

    return recs
