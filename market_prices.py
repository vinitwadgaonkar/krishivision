"""
Indian Crop Market Price Engine — LIVE + Fallback.
Fetches real-time mandi prices from mandibhav.in (Agmarknet data).
Falls back to embedded MSP 2025-26 + historical averages if live fetch fails.
Prices in INR per Quintal (100 kg).
"""

import re
import json
import time
import threading
import http.client
import ssl
import logging

log = logging.getLogger(__name__)

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

# ── Load build-time cached prices if available ─────────────────────
_build_cache = {}
try:
    import os
    _cache_path = os.path.join(os.path.dirname(__file__), 'cached_prices.json')
    if os.path.exists(_cache_path):
        with open(_cache_path) as _f:
            _build_data = json.load(_f)
            _build_cache = _build_data.get('prices', {})
            log.info('Loaded %d build-time cached prices from %s',
                     len(_build_cache), _build_data.get('fetched_at', '?'))
except Exception:
    pass


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


def _fetch_json(slug):
    """Fetch structured price data from mandibhav.in SvelteKit __data.json endpoint."""
    path = f'/crop/{slug}/__data.json'
    try:
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection('mandibhav.in', timeout=8, context=ctx)
        conn.request('GET', path, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Connection': 'close',
        })
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        if resp.status == 200 and len(body) > 100:
            return json.loads(body.decode('utf-8', errors='ignore'))
    except Exception as e:
        log.warning('Failed to fetch %s: %s', path, e)
    return None


def _parse_sveltekit_data(raw, slug):
    """Parse SvelteKit devalue format into structured price data.

    Devalue format: flat array where dict entries map key names to indices
    of their values in the same array. e.g. {name: 5, price: 6} means
    the name is at entries[5] and price at entries[6].
    """
    try:
        nodes = raw.get('nodes', [])
        if len(nodes) < 2:
            return None
        entries = nodes[1].get('data', [])
        if len(entries) < 12:
            return None

        def val(idx):
            return entries[idx] if isinstance(idx, int) and 0 <= idx < len(entries) else idx

        schema = entries[0]
        cp_idx = schema.get('currentPrice')
        if cp_idx is None:
            return None

        cp = entries[cp_idx]
        national_avg = val(cp['average'])
        price_min = val(cp['min'])
        price_max = val(cp['max'])
        num_mandis = val(cp.get('locations', 0))

        if not isinstance(national_avg, (int, float)):
            return None

        # State averages
        state_prices = {}
        sa_idx = schema.get('stateAverages')
        if sa_idx is not None:
            state_ref_list = entries[sa_idx]
            if isinstance(state_ref_list, list):
                for si in state_ref_list:
                    st = entries[si] if isinstance(si, int) else None
                    if isinstance(st, dict) and 'name' in st and 'average' in st:
                        name = val(st['name'])
                        avg = val(st['average'])
                        slug_val = val(st['slug']) if 'slug' in st else ''
                        real_name = STATE_SLUG_TO_NAME.get(slug_val, name) if slug_val else name
                        if isinstance(avg, (int, float)):
                            state_prices[real_name] = avg

        # 7-day trend from chart data
        trend = 'stable'
        cd_idx = schema.get('chartData')
        if cd_idx is not None:
            chart_ref_list = entries[cd_idx]
            if isinstance(chart_ref_list, list) and len(chart_ref_list) >= 2:
                first = entries[chart_ref_list[0]]
                last = entries[chart_ref_list[-1]]
                if isinstance(first, dict) and isinstance(last, dict):
                    older = val(first.get('price', first.get('average', 0)))
                    recent = val(last.get('price', last.get('average', 0)))
                    if isinstance(older, (int, float)) and isinstance(recent, (int, float)) and older > 0:
                        pct = ((recent - older) / older) * 100
                        trend = 'up' if pct > 1.5 else ('down' if pct < -1.5 else 'stable')

        return {
            'national_avg': round(float(national_avg), 2),
            'price_min': round(float(price_min), 2),
            'price_max': round(float(price_max), 2),
            'num_mandis': int(num_mandis) if isinstance(num_mandis, (int, float)) else 0,
            'trend': trend,
            'state_prices': state_prices,
            'live': True,
        }
    except Exception as e:
        log.warning('Failed to parse data for %s: %s', slug, e)
        return None


def _fetch_live_price(crop_name):
    """Fetch live mandi price from mandibhav.in for a single crop."""
    slug = CROP_SLUG_MAP.get(crop_name)
    if not slug:
        return None

    with _cache_lock:
        cached = _cache.get(slug)
        if cached and (time.time() - cached['ts']) < CACHE_TTL:
            return cached['data']

    raw = _fetch_json(slug)
    if not raw:
        return None

    result = _parse_sveltekit_data(raw, slug)
    if result:
        with _cache_lock:
            _cache[slug] = {'data': result, 'ts': time.time()}
    return result


def _format_price_result(data, crop_name, state, is_live):
    """Format a price data dict into the API response format."""
    result = {
        'crop': crop_name,
        'msp': MSP_DATA.get(crop_name),
        'national_avg': data['national_avg'],
        'price_range': f"₹{int(data['price_min']):,} - ₹{int(data['price_max']):,}",
        'unit': '₹/Quintal',
        'season': STATIC_PRICES.get(crop_name, {}).get('season', ''),
        'num_mandis': data.get('num_mandis', 0),
        'live': is_live,
        'trend': data.get('trend', 'stable'),
    }

    state_prices = data.get('state_prices', {})
    if state and state in state_prices:
        result['state_price'] = state_prices[state]
        result['state'] = state
    else:
        result['state_price'] = data['national_avg']
        result['state'] = 'National'

    return result


def get_crop_price(crop_name, state=None):
    """Get market price info for a crop. Priority: live > build-cache > static."""
    # 1. Try live fetch
    live = _fetch_live_price(crop_name)
    if live:
        return _format_price_result(live, crop_name, state, is_live=True)

    # 2. Try build-time cached data (fetched during Docker build)
    build = _build_cache.get(crop_name)
    if build:
        return _format_price_result(build, crop_name, state, is_live=True)

    # 3. Static fallback
    static = STATIC_PRICES.get(crop_name)
    if not static:
        return None

    return {
        'crop': crop_name,
        'msp': MSP_DATA.get(crop_name),
        'national_avg': static['avg'],
        'price_range': f"₹{static['min']:,} - ₹{static['max']:,}",
        'unit': '₹/Quintal',
        'season': static['season'],
        'live': False,
        'state_price': static['avg'],
        'state': 'National',
        'trend': 'stable',
    }


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
