"""
Indian Crop Market Price Engine — LIVE + Fallback.
Fetches real-time mandi prices from mandibhav.in (Agmarknet data).
Falls back to embedded MSP 2025-26 + historical averages if live fetch fails.
Prices in INR per Quintal (100 kg).
"""

import re
import time
import threading
import subprocess

# ── Crop name → mandibhav.in URL slug mapping ─────────────────────
CROP_SLUG_MAP = {
    'Rice': 'rice',
    'Wheat': 'wheat',
    'Maize': 'maize',
    'Cotton': 'cotton',
    'Banana': 'banana',
    'Coffee': 'coffee',
    'Coconut': 'coconut',
    'Grapes': 'grapes',
    'Mango': 'mango',
    'Watermelon': 'water-melon',
    'Muskmelon': 'karbuja-musk-melon',
    'Orange': 'orange',
    'Papaya': 'papaya',
    'Pomegranate': 'pomegranate',
    'Apple': 'apple',
    'ChickPea': 'bengal-gram-gram-whole',
    'Lentil': 'lentil-masur-whole',
    'KidneyBeans': 'kidney-beans-rajma',
    'PigeonPeas': 'arhar-tur-red-gram-whole',
    'MothBeans': 'moath-dal',
    'MungBean': 'green-gram-moong-whole',
    'Blackgram': 'black-gram-urd-beans-whole',
    'Jute': 'jute',
}

STATE_SLUG_TO_NAME = {
    'andhra-pradesh': 'Andhra Pradesh',
    'arunachal-pradesh': 'Arunachal Pradesh',
    'assam': 'Assam',
    'bihar': 'Bihar',
    'chattisgarh': 'Chattisgarh',
    'chhattisgarh': 'Chattisgarh',
    'goa': 'Goa',
    'gujarat': 'Gujarat',
    'haryana': 'Haryana',
    'himachal-pradesh': 'Himachal Pradesh',
    'jharkhand': 'Jharkhand',
    'karnataka': 'Karnataka',
    'kerala': 'Kerala',
    'madhya-pradesh': 'Madhya Pradesh',
    'maharashtra': 'Maharashtra',
    'manipur': 'Manipur',
    'meghalaya': 'Meghalaya',
    'mizoram': 'Mizoram',
    'nagaland': 'Nagaland',
    'odisha': 'Odisha',
    'punjab': 'Punjab',
    'rajasthan': 'Rajasthan',
    'sikkim': 'Sikkim',
    'tamil-nadu': 'Tamil Nadu',
    'telangana': 'Telangana',
    'tripura': 'Tripura',
    'uttar-pradesh': 'Uttar Pradesh',
    'uttarakhand': 'Uttarakhand',
    'west-bengal': 'West Bengal',
    'delhi': 'Delhi',
}

# ── In-memory cache: {crop_slug: {data, timestamp}} ───────────────
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 3600  # 1 hour


# ── Official MSP 2025-26 (Government of India, CACP) ──────────────
MSP_DATA = {
    'Rice': 2320, 'Wheat': 2425, 'Maize': 2225, 'Cotton': 7121,
    'Coconut': 2800, 'ChickPea': 5650, 'Lentil': 6700,
    'PigeonPeas': 7550, 'MothBeans': 6225, 'MungBean': 8682,
    'Blackgram': 7400, 'Jute': 5335,
}

# ── Static fallback data (used when live fetch fails) ─────────────
STATIC_PRICES = {
    'Rice': {'avg': 2500, 'min': 1900, 'max': 3200, 'season': 'Kharif'},
    'Wheat': {'avg': 2550, 'min': 2100, 'max': 3000, 'season': 'Rabi'},
    'Maize': {'avg': 2100, 'min': 1600, 'max': 2800, 'season': 'Kharif'},
    'Cotton': {'avg': 7000, 'min': 5500, 'max': 8500, 'season': 'Kharif'},
    'Banana': {'avg': 1800, 'min': 800, 'max': 3500, 'season': 'Year-round'},
    'Coffee': {'avg': 25000, 'min': 8000, 'max': 45000, 'season': 'Rabi'},
    'Coconut': {'avg': 2700, 'min': 1500, 'max': 4000, 'season': 'Year-round'},
    'Grapes': {'avg': 5000, 'min': 2000, 'max': 12000, 'season': 'Rabi'},
    'Mango': {'avg': 4000, 'min': 1500, 'max': 10000, 'season': 'Zaid'},
    'Watermelon': {'avg': 800, 'min': 300, 'max': 2000, 'season': 'Zaid'},
    'Muskmelon': {'avg': 1200, 'min': 500, 'max': 3000, 'season': 'Zaid'},
    'Orange': {'avg': 4000, 'min': 2000, 'max': 8000, 'season': 'Rabi'},
    'Papaya': {'avg': 1500, 'min': 500, 'max': 3000, 'season': 'Year-round'},
    'Pomegranate': {'avg': 7000, 'min': 3000, 'max': 15000, 'season': 'Year-round'},
    'Apple': {'avg': 8000, 'min': 4000, 'max': 18000, 'season': 'Kharif'},
    'ChickPea': {'avg': 5800, 'min': 4500, 'max': 7500, 'season': 'Rabi'},
    'Lentil': {'avg': 6500, 'min': 5000, 'max': 8000, 'season': 'Rabi'},
    'KidneyBeans': {'avg': 8000, 'min': 5000, 'max': 12000, 'season': 'Kharif'},
    'PigeonPeas': {'avg': 7800, 'min': 6000, 'max': 10000, 'season': 'Kharif'},
    'MothBeans': {'avg': 6500, 'min': 5000, 'max': 9000, 'season': 'Kharif'},
    'MungBean': {'avg': 8500, 'min': 6500, 'max': 11000, 'season': 'Kharif'},
    'Blackgram': {'avg': 7200, 'min': 5500, 'max': 9500, 'season': 'Kharif'},
    'Jute': {'avg': 5500, 'min': 4500, 'max': 7000, 'season': 'Kharif'},
}


def _fetch_live_price(crop_name):
    """Scrape live mandi price from mandibhav.in for a single crop."""
    slug = CROP_SLUG_MAP.get(crop_name)
    if not slug:
        return None

    with _cache_lock:
        cached = _cache.get(slug)
        if cached and (time.time() - cached['ts']) < CACHE_TTL:
            return cached['data']

    url = f'https://mandibhav.in/crop/{slug}'
    try:
        proc = subprocess.run(
            ['curl', '-sL', '--max-time', '6', url],
            capture_output=True, timeout=8,
        )
        if proc.returncode != 0:
            return None
        html = proc.stdout.decode('utf-8', errors='ignore')
        if not html or len(html) < 500:
            return None
    except Exception:
        return None

    result = _parse_price_html(html, crop_name, slug)
    if result:
        with _cache_lock:
            _cache[slug] = {'data': result, 'ts': time.time()}
    return result


def _parse_price_html(html, crop_name, slug):
    """Extract price data from mandibhav.in crop page HTML."""
    avg_m = re.search(r'Average Price.*?₹([\d,]+\.?\d*)', html, re.DOTALL)
    range_m = re.search(r'Price Range.*?₹([\d,]+).*?₹([\d,]+)', html, re.DOTALL)
    mandis_m = re.search(r'across\s+([\d,]+)\s+mandis', html)

    if not avg_m:
        return None

    def to_num(s):
        return float(s.replace(',', ''))

    national_avg = to_num(avg_m.group(1))
    price_min = to_num(range_m.group(1)) if range_m else national_avg * 0.7
    price_max = to_num(range_m.group(2)) if range_m else national_avg * 1.5
    num_mandis = int(mandis_m.group(1).replace(',', '')) if mandis_m else 0

    # 7-day trend from price history table
    history_prices = re.findall(r'₹([\d,]+\.?\d*)\s*</td>', html)
    trend = 'stable'
    if len(history_prices) >= 2:
        try:
            recent = to_num(history_prices[-1])
            older = to_num(history_prices[0])
            pct = ((recent - older) / older) * 100
            if pct > 1.5:
                trend = 'up'
            elif pct < -1.5:
                trend = 'down'
        except (ValueError, ZeroDivisionError):
            pass

    # State-level prices
    state_prices = {}
    state_pattern = re.findall(
        rf'/crop/{re.escape(slug)}/([a-z-]+).*?₹([\d,]+\.?\d*)', html
    )
    for state_slug, price_str in state_pattern:
        state_name = STATE_SLUG_TO_NAME.get(state_slug, state_slug.replace('-', ' ').title())
        try:
            state_prices[state_name] = to_num(price_str)
        except ValueError:
            pass

    return {
        'national_avg': round(national_avg, 2),
        'price_min': round(price_min, 2),
        'price_max': round(price_max, 2),
        'num_mandis': num_mandis,
        'trend': trend,
        'state_prices': state_prices,
        'live': True,
    }


def get_crop_price(crop_name, state=None):
    """Get market price info for a crop. Tries live data first, falls back to static."""
    live = _fetch_live_price(crop_name)

    if live:
        result = {
            'crop': crop_name,
            'msp': MSP_DATA.get(crop_name),
            'national_avg': live['national_avg'],
            'price_range': f"₹{int(live['price_min']):,} - ₹{int(live['price_max']):,}",
            'unit': '₹/Quintal',
            'season': STATIC_PRICES.get(crop_name, {}).get('season', ''),
            'num_mandis': live['num_mandis'],
            'live': True,
        }

        if state and state in live['state_prices']:
            result['state_price'] = live['state_prices'][state]
            result['state'] = state
        else:
            result['state_price'] = live['national_avg']
            result['state'] = 'National'

        result['trend'] = live['trend']
        return result

    # Fallback to static
    static = STATIC_PRICES.get(crop_name)
    if not static:
        return None

    result = {
        'crop': crop_name,
        'msp': MSP_DATA.get(crop_name),
        'national_avg': static['avg'],
        'price_range': f"₹{static['min']:,} - ₹{static['max']:,}",
        'unit': '₹/Quintal',
        'season': static['season'],
        'live': False,
    }
    result['state_price'] = static['avg']
    result['state'] = 'National'
    result['trend'] = 'stable'
    return result


def get_prices_for_recommendations(crop_list, state=None):
    """Get prices for recommended crops. Fetches live prices in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    crop_names = []
    confidence_map = {}
    for item in crop_list:
        name = item.get('crop', item) if isinstance(item, dict) else item
        crop_names.append(name)
        confidence_map[name] = item.get('confidence', 0) if isinstance(item, dict) else 0

    # Parallel live fetch (max 6 concurrent to be polite)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_live_price, name): name for name in crop_names}
        for f in as_completed(futures):
            pass  # results are cached

    prices = []
    for name in crop_names:
        price = get_crop_price(name, state)
        if price:
            price['recommendation_confidence'] = confidence_map.get(name, 0)
            prices.append(price)

    prices.sort(key=lambda x: -(x.get('state_price', 0) or x.get('national_avg', 0)))
    return prices
