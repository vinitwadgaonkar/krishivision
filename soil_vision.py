"""
Soil Image Analysis using Color Science.
Scientifically validated: soil color strongly correlates with organic matter,
iron content, moisture, and texture (Munsell soil color system).
"""

import io
import numpy as np
from PIL import Image
from collections import Counter


def analyze_soil_image(image_bytes):
    """Full soil analysis pipeline from a single photo."""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img_array = np.array(img)

    center_crop = _center_crop(img_array, ratio=0.6)

    dominant_colors = _extract_dominant_colors(center_crop, k=5)
    hsv_stats = _compute_hsv_stats(center_crop)
    rgb_stats = _compute_rgb_stats(center_crop)
    texture = _estimate_texture(center_crop)

    soil_type = _classify_soil_type(hsv_stats, rgb_stats, dominant_colors)
    moisture = _estimate_moisture(hsv_stats)
    organic_carbon = _estimate_organic_carbon(hsv_stats, rgb_stats)
    iron_content = _estimate_iron(hsv_stats, rgb_stats)
    ph_estimate = _estimate_ph(soil_type, organic_carbon)
    color_description = _describe_color(hsv_stats, dominant_colors)

    predicted_params = {
        'pH': ph_estimate,
        'OC': organic_carbon,
        'EC': 0.3 if moisture['level'] == 'Dry' else 0.6,
        'P': _estimate_from_type(soil_type['type'], 'P'),
        'K': _estimate_from_type(soil_type['type'], 'K'),
        'S': _estimate_from_type(soil_type['type'], 'S'),
        'Zn': _estimate_from_type(soil_type['type'], 'Zn'),
        'B': _estimate_from_type(soil_type['type'], 'B'),
        'Fe': iron_content['value'],
        'Cu': _estimate_from_type(soil_type['type'], 'Cu'),
        'Mn': _estimate_from_type(soil_type['type'], 'Mn'),
    }

    return {
        'soil_type': soil_type,
        'moisture': moisture,
        'organic_carbon': {'estimated_percent': round(organic_carbon, 2),
                           'level': _oc_level(organic_carbon)},
        'iron_content': iron_content,
        'texture': texture,
        'color': color_description,
        'ph_estimate': {'value': round(ph_estimate, 1),
                        'range': f"{ph_estimate - 0.5:.1f} - {ph_estimate + 0.5:.1f}"},
        'predicted_params': predicted_params,
        'confidence_note': 'Estimates based on soil color analysis. Lab testing recommended for precision.',
    }


def _center_crop(img_array, ratio=0.6):
    h, w = img_array.shape[:2]
    ch, cw = int(h * ratio), int(w * ratio)
    y_start, x_start = (h - ch) // 2, (w - cw) // 2
    return img_array[y_start:y_start + ch, x_start:x_start + cw]


def _extract_dominant_colors(img_array, k=5):
    """K-means-style dominant color extraction without sklearn dependency."""
    pixels = img_array.reshape(-1, 3)
    sample_size = min(5000, len(pixels))
    indices = np.random.choice(len(pixels), sample_size, replace=False)
    samples = pixels[indices]

    centers = samples[np.random.choice(len(samples), k, replace=False)].astype(float)

    for _ in range(15):
        dists = np.sqrt(((samples[:, None] - centers[None]) ** 2).sum(axis=2))
        labels = dists.argmin(axis=1)
        new_centers = np.array([samples[labels == i].mean(axis=0) if (labels == i).any()
                                else centers[i] for i in range(k)])
        if np.allclose(centers, new_centers, atol=1):
            break
        centers = new_centers

    counts = Counter(labels)
    total = len(labels)
    results = []
    for i in range(k):
        r, g, b = centers[i].astype(int)
        results.append({
            'rgb': [int(r), int(g), int(b)],
            'hex': f'#{int(r):02x}{int(g):02x}{int(b):02x}',
            'percentage': round(counts.get(i, 0) / total * 100, 1)
        })
    return sorted(results, key=lambda x: -x['percentage'])


def _rgb_to_hsv(rgb_array):
    rgb_norm = rgb_array.astype(float) / 255.0
    r, g, b = rgb_norm[..., 0], rgb_norm[..., 1], rgb_norm[..., 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    h = np.zeros_like(cmax)
    mask = delta > 0
    rm = mask & (cmax == r)
    gm = mask & (cmax == g)
    bm = mask & (cmax == b)
    h[rm] = (60 * ((g[rm] - b[rm]) / delta[rm]) % 360)
    h[gm] = (60 * ((b[gm] - r[gm]) / delta[gm]) + 120)
    h[bm] = (60 * ((r[bm] - g[bm]) / delta[bm]) + 240)
    h = h % 360

    s = np.where(cmax > 0, delta / cmax, 0)
    v = cmax

    return np.stack([h, s, v], axis=-1)


def _compute_hsv_stats(img_array):
    hsv = _rgb_to_hsv(img_array)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return {
        'h_mean': float(np.mean(h)), 'h_std': float(np.std(h)),
        's_mean': float(np.mean(s)), 's_std': float(np.std(s)),
        'v_mean': float(np.mean(v)), 'v_std': float(np.std(v)),
        'h_median': float(np.median(h)),
        's_median': float(np.median(s)),
        'v_median': float(np.median(v)),
    }


def _compute_rgb_stats(img_array):
    r, g, b = img_array[..., 0], img_array[..., 1], img_array[..., 2]
    return {
        'r_mean': float(np.mean(r)), 'g_mean': float(np.mean(g)), 'b_mean': float(np.mean(b)),
        'r_std': float(np.std(r)), 'g_std': float(np.std(g)), 'b_std': float(np.std(b)),
        'brightness': float(np.mean(r) * 0.299 + np.mean(g) * 0.587 + np.mean(b) * 0.114),
        'redness': float(np.mean(r) - np.mean(g)),
    }


def _estimate_texture(img_array):
    """Estimate texture from local variance (higher variance = coarser texture)."""
    gray = np.mean(img_array.astype(float), axis=2)
    h, w = gray.shape
    block = 16
    variances = []
    for i in range(0, h - block, block):
        for j in range(0, w - block, block):
            variances.append(np.var(gray[i:i + block, j:j + block]))
    mean_var = np.mean(variances) if variances else 0
    std_var = np.std(variances) if variances else 0

    if mean_var < 200:
        texture_type = 'Fine (Clay-like)'
        particle = 'clay'
    elif mean_var < 600:
        texture_type = 'Medium (Loamy)'
        particle = 'loam'
    elif mean_var < 1200:
        texture_type = 'Medium-Coarse (Sandy Loam)'
        particle = 'sandy_loam'
    else:
        texture_type = 'Coarse (Sandy)'
        particle = 'sand'

    return {
        'type': texture_type,
        'particle': particle,
        'uniformity': round(max(0, 1 - std_var / (mean_var + 1)), 2),
        'variance': round(mean_var, 1),
    }


def _classify_soil_type(hsv, rgb, colors):
    """Classify soil type from color features using Munsell color principles."""
    h, s, v = hsv['h_mean'], hsv['s_mean'], hsv['v_mean']
    brightness = rgb['brightness']
    redness = rgb['redness']

    scores = {
        'Black Soil (Vertisol)': 0,
        'Red Soil (Laterite)': 0,
        'Alluvial Soil': 0,
        'Sandy Soil': 0,
        'Clay Soil': 0,
        'Loamy Soil': 0,
    }

    if v < 0.35 and s < 0.3:
        scores['Black Soil (Vertisol)'] += 5
    elif v < 0.45:
        scores['Black Soil (Vertisol)'] += 3
        scores['Clay Soil'] += 2

    if redness > 30 and 0 <= h <= 30:
        scores['Red Soil (Laterite)'] += 5
    elif redness > 15:
        scores['Red Soil (Laterite)'] += 3

    if brightness > 160 and s < 0.3:
        scores['Sandy Soil'] += 4
    elif brightness > 140:
        scores['Sandy Soil'] += 2
        scores['Alluvial Soil'] += 1

    if 20 <= h <= 50 and 0.2 <= s <= 0.5 and 0.3 <= v <= 0.6:
        scores['Alluvial Soil'] += 4
        scores['Loamy Soil'] += 3

    if 0.35 <= v <= 0.55 and 0.15 <= s <= 0.4:
        scores['Loamy Soil'] += 3
        scores['Clay Soil'] += 2

    if s < 0.15 and 0.3 <= v <= 0.5:
        scores['Clay Soil'] += 3

    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = round(scores[best] / total, 2)

    return {
        'type': best,
        'confidence': confidence,
        'all_scores': {k: round(v / total, 2) for k, v in sorted(scores.items(), key=lambda x: -x[1])},
    }


def _estimate_moisture(hsv):
    v = hsv['v_mean']
    s = hsv['s_mean']
    moisture_index = (1 - v) * 0.7 + s * 0.3

    if moisture_index > 0.65:
        level = 'Wet'
        pct = min(95, int(moisture_index * 100))
    elif moisture_index > 0.45:
        level = 'Moist'
        pct = int(moisture_index * 80)
    elif moisture_index > 0.3:
        level = 'Moderate'
        pct = int(moisture_index * 70)
    else:
        level = 'Dry'
        pct = max(5, int(moisture_index * 50))

    return {'level': level, 'index': round(moisture_index, 2), 'estimated_percent': pct}


def _estimate_organic_carbon(hsv, rgb):
    """Darker soil = higher organic carbon (well-established relationship)."""
    darkness = 1 - hsv['v_mean']
    low_saturation_bonus = max(0, 0.3 - hsv['s_mean'])
    oc = darkness * 1.5 + low_saturation_bonus * 0.5
    return max(0.1, min(3.0, round(oc, 2)))


def _estimate_iron(hsv, rgb):
    redness = rgb['redness']
    hue = hsv['h_mean']
    if redness > 30 and hue < 25:
        val = min(20, 5 + redness * 0.3)
        level = 'High'
    elif redness > 10:
        val = 3 + redness * 0.15
        level = 'Medium'
    else:
        val = max(1, 2 + redness * 0.1)
        level = 'Low'
    return {'value': round(val, 1), 'level': level}


def _estimate_ph(soil_type, oc):
    base_ph = {
        'Black Soil (Vertisol)': 7.8,
        'Red Soil (Laterite)': 5.8,
        'Alluvial Soil': 7.2,
        'Sandy Soil': 6.5,
        'Clay Soil': 7.0,
        'Loamy Soil': 6.8,
    }
    ph = base_ph.get(soil_type['type'], 7.0)
    ph -= oc * 0.3
    return max(4.0, min(9.5, round(ph, 1)))


def _estimate_from_type(soil_type, nutrient):
    """Typical nutrient ranges by soil type from Indian soil survey data."""
    profiles = {
        'Black Soil (Vertisol)': {'P': 18, 'K': 320, 'S': 12, 'Zn': 0.7, 'B': 0.6, 'Cu': 0.4, 'Mn': 3.5},
        'Red Soil (Laterite)':   {'P': 12, 'K': 140, 'S': 8,  'Zn': 0.4, 'B': 0.3, 'Cu': 0.3, 'Mn': 4.0},
        'Alluvial Soil':         {'P': 22, 'K': 200, 'S': 14, 'Zn': 0.8, 'B': 0.5, 'Cu': 0.3, 'Mn': 3.0},
        'Sandy Soil':            {'P': 8,  'K': 90,  'S': 5,  'Zn': 0.3, 'B': 0.2, 'Cu': 0.2, 'Mn': 1.5},
        'Clay Soil':             {'P': 15, 'K': 250, 'S': 10, 'Zn': 0.5, 'B': 0.4, 'Cu': 0.3, 'Mn': 2.5},
        'Loamy Soil':            {'P': 20, 'K': 180, 'S': 11, 'Zn': 0.6, 'B': 0.5, 'Cu': 0.3, 'Mn': 2.8},
    }
    return profiles.get(soil_type, profiles['Loamy Soil']).get(nutrient, 1.0)


def _oc_level(oc):
    if oc >= 0.75: return 'High'
    if oc >= 0.50: return 'Medium'
    return 'Low'


def _describe_color(hsv, colors):
    v = hsv['v_mean']
    s = hsv['s_mean']
    h = hsv['h_mean']

    if v < 0.3:
        brightness_desc = 'Very Dark'
    elif v < 0.45:
        brightness_desc = 'Dark'
    elif v < 0.6:
        brightness_desc = 'Medium'
    elif v < 0.75:
        brightness_desc = 'Light'
    else:
        brightness_desc = 'Very Light'

    if s < 0.1:
        color_desc = 'Gray'
    elif h < 15 or h > 340:
        color_desc = 'Red'
    elif h < 40:
        color_desc = 'Orange-Brown'
    elif h < 65:
        color_desc = 'Yellow-Brown'
    elif h < 150:
        color_desc = 'Greenish'
    else:
        color_desc = 'Brown'

    return {
        'description': f'{brightness_desc} {color_desc}',
        'dominant_hex': colors[0]['hex'] if colors else '#000000',
        'palette': [c['hex'] for c in colors[:3]],
    }
