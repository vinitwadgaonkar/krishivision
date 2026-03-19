"""
Geo-Intelligence Module: Weather, Season, Location-based soil data.
Auto-context from GPS coordinates — zero typing required.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date


def get_weather(lat, lon):
    """Fetch live weather from wttr.in (free, no API key needed)."""
    try:
        url = f"https://wttr.in/{lat},{lon}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'KrishiVision/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        current = data.get('current_condition', [{}])[0]
        weather = data.get('weather', [{}])

        temp = float(current.get('temp_C', 25))
        humidity = float(current.get('humidity', 70))
        precip = float(current.get('precipMM', 0))
        weather_desc = current.get('weatherDesc', [{}])[0].get('value', 'Unknown')
        feels_like = float(current.get('FeelsLikeC', temp))
        wind_speed = float(current.get('windspeedKmph', 0))
        uv_index = int(current.get('uvIndex', 5))

        avg_rainfall = 0
        for w in weather[:3]:
            avg_rainfall += float(w.get('totalSnow_cm', 0)) * 10
            hourly = w.get('hourly', [])
            for h in hourly:
                avg_rainfall += float(h.get('precipMM', 0))

        nearest = data.get('nearest_area', [{}])[0]
        area_name = nearest.get('areaName', [{}])[0].get('value', 'Unknown')
        region = nearest.get('region', [{}])[0].get('value', 'Unknown')
        country = nearest.get('country', [{}])[0].get('value', 'Unknown')

        return {
            'success': True,
            'temperature': temp,
            'humidity': humidity,
            'precipitation_mm': precip,
            'feels_like': feels_like,
            'wind_speed_kmph': wind_speed,
            'uv_index': uv_index,
            'weather_description': weather_desc,
            'rainfall_3day': round(avg_rainfall, 1),
            'location': {
                'area': area_name,
                'region': region,
                'country': country,
                'lat': lat,
                'lon': lon,
            },
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'temperature': 25, 'humidity': 70,
            'precipitation_mm': 0, 'rainfall_3day': 100,
            'location': {'lat': lat, 'lon': lon, 'area': 'Unknown'},
        }


def detect_season(lat, lon, date_obj=None):
    """
    Detect Indian agricultural season from date and latitude.
    Kharif (monsoon): June-October — rice, maize, cotton, groundnut
    Rabi (winter): November-March — wheat, mustard, gram, barley
    Zaid (summer): April-May — watermelon, muskmelon, cucumber
    """
    if date_obj is None:
        date_obj = date.today()

    month = date_obj.month
    is_india = 8 <= lat <= 35 and 68 <= lon <= 97

    if month in (6, 7, 8, 9, 10):
        season = 'Kharif'
        season_name = 'Kharif (Monsoon Season)'
        typical_crops = ['Rice', 'Maize', 'Cotton', 'Groundnut', 'Soybean',
                         'Jute', 'Sugarcane', 'Bajra', 'Jowar']
        planting_window = 'June - July'
        harvest_window = 'October - November'
    elif month in (11, 12, 1, 2, 3):
        season = 'Rabi'
        season_name = 'Rabi (Winter Season)'
        typical_crops = ['Wheat', 'Mustard', 'Chickpea', 'Barley', 'Lentil',
                         'Peas', 'Linseed', 'Sunflower']
        planting_window = 'October - December'
        harvest_window = 'March - April'
    else:
        season = 'Zaid'
        season_name = 'Zaid (Summer Season)'
        typical_crops = ['Watermelon', 'Muskmelon', 'Cucumber', 'Moong',
                         'Fodder Crops', 'Vegetables']
        planting_window = 'March - April'
        harvest_window = 'May - June'

    return {
        'season': season,
        'season_name': season_name,
        'typical_crops': typical_crops,
        'planting_window': planting_window,
        'harvest_window': harvest_window,
        'month': month,
        'is_india': is_india,
    }


# Indian soil database by state — compiled from Soil Survey of India data
INDIA_SOIL_DB = {
    'Maharashtra': {
        'dominant_soil': 'Black Soil (Vertisol)',
        'typical_ph': 7.5, 'typical_oc': 0.45, 'typical_ec': 0.35,
        'typical_N': 220, 'typical_P': 15, 'typical_K': 300,
        'typical_Zn': 0.5, 'typical_Fe': 6.0, 'typical_Mn': 3.5,
        'typical_Cu': 0.4, 'typical_B': 0.4, 'typical_S': 9,
        'major_crops': ['Cotton', 'Soybean', 'Sugarcane', 'Jowar', 'Wheat'],
        'climate': 'Semi-arid to sub-humid',
    },
    'Punjab': {
        'dominant_soil': 'Alluvial Soil',
        'typical_ph': 7.8, 'typical_oc': 0.38, 'typical_ec': 0.45,
        'typical_N': 240, 'typical_P': 18, 'typical_K': 180,
        'typical_Zn': 0.7, 'typical_Fe': 5.5, 'typical_Mn': 3.0,
        'typical_Cu': 0.3, 'typical_B': 0.5, 'typical_S': 12,
        'major_crops': ['Wheat', 'Rice', 'Cotton', 'Sugarcane', 'Maize'],
        'climate': 'Semi-arid',
    },
    'Uttar Pradesh': {
        'dominant_soil': 'Alluvial Soil',
        'typical_ph': 7.5, 'typical_oc': 0.42, 'typical_ec': 0.3,
        'typical_N': 230, 'typical_P': 20, 'typical_K': 200,
        'typical_Zn': 0.6, 'typical_Fe': 7.0, 'typical_Mn': 3.2,
        'typical_Cu': 0.35, 'typical_B': 0.45, 'typical_S': 10,
        'major_crops': ['Wheat', 'Rice', 'Sugarcane', 'Potato', 'Mustard'],
        'climate': 'Sub-tropical',
    },
    'Karnataka': {
        'dominant_soil': 'Red Soil (Laterite)',
        'typical_ph': 6.2, 'typical_oc': 0.55, 'typical_ec': 0.25,
        'typical_N': 250, 'typical_P': 22, 'typical_K': 160,
        'typical_Zn': 0.5, 'typical_Fe': 12.0, 'typical_Mn': 4.0,
        'typical_Cu': 0.4, 'typical_B': 0.3, 'typical_S': 8,
        'major_crops': ['Rice', 'Ragi', 'Coffee', 'Coconut', 'Sugarcane'],
        'climate': 'Tropical wet/semi-arid',
    },
    'Kerala': {
        'dominant_soil': 'Laterite Soil',
        'typical_ph': 5.5, 'typical_oc': 1.2, 'typical_ec': 0.3,
        'typical_N': 280, 'typical_P': 25, 'typical_K': 180,
        'typical_Zn': 1.0, 'typical_Fe': 15.0, 'typical_Mn': 5.0,
        'typical_Cu': 0.5, 'typical_B': 0.6, 'typical_S': 12,
        'major_crops': ['Rice', 'Coconut', 'Rubber', 'Tea', 'Spices'],
        'climate': 'Tropical wet',
    },
    'Tamil Nadu': {
        'dominant_soil': 'Red Soil / Black Soil',
        'typical_ph': 7.0, 'typical_oc': 0.50, 'typical_ec': 0.4,
        'typical_N': 235, 'typical_P': 17, 'typical_K': 210,
        'typical_Zn': 0.6, 'typical_Fe': 8.0, 'typical_Mn': 3.5,
        'typical_Cu': 0.3, 'typical_B': 0.4, 'typical_S': 9,
        'major_crops': ['Rice', 'Sugarcane', 'Cotton', 'Banana', 'Coconut'],
        'climate': 'Tropical',
    },
    'Rajasthan': {
        'dominant_soil': 'Sandy / Desert Soil',
        'typical_ph': 8.2, 'typical_oc': 0.2, 'typical_ec': 0.8,
        'typical_N': 150, 'typical_P': 10, 'typical_K': 250,
        'typical_Zn': 0.3, 'typical_Fe': 3.0, 'typical_Mn': 2.0,
        'typical_Cu': 0.2, 'typical_B': 0.2, 'typical_S': 5,
        'major_crops': ['Bajra', 'Wheat', 'Mustard', 'Groundnut', 'Cumin'],
        'climate': 'Arid to semi-arid',
    },
    'Madhya Pradesh': {
        'dominant_soil': 'Black Soil (Vertisol)',
        'typical_ph': 7.6, 'typical_oc': 0.48, 'typical_ec': 0.3,
        'typical_N': 210, 'typical_P': 14, 'typical_K': 280,
        'typical_Zn': 0.45, 'typical_Fe': 5.0, 'typical_Mn': 3.0,
        'typical_Cu': 0.35, 'typical_B': 0.35, 'typical_S': 8,
        'major_crops': ['Soybean', 'Wheat', 'Gram', 'Rice', 'Cotton'],
        'climate': 'Sub-tropical',
    },
    'Gujarat': {
        'dominant_soil': 'Black Soil / Alluvial',
        'typical_ph': 7.8, 'typical_oc': 0.40, 'typical_ec': 0.5,
        'typical_N': 200, 'typical_P': 16, 'typical_K': 260,
        'typical_Zn': 0.5, 'typical_Fe': 5.5, 'typical_Mn': 2.8,
        'typical_Cu': 0.3, 'typical_B': 0.4, 'typical_S': 10,
        'major_crops': ['Cotton', 'Groundnut', 'Wheat', 'Cumin', 'Castor'],
        'climate': 'Semi-arid',
    },
    'West Bengal': {
        'dominant_soil': 'Alluvial Soil',
        'typical_ph': 6.5, 'typical_oc': 0.65, 'typical_ec': 0.35,
        'typical_N': 260, 'typical_P': 20, 'typical_K': 170,
        'typical_Zn': 0.7, 'typical_Fe': 10.0, 'typical_Mn': 4.0,
        'typical_Cu': 0.4, 'typical_B': 0.5, 'typical_S': 11,
        'major_crops': ['Rice', 'Jute', 'Potato', 'Tea', 'Vegetables'],
        'climate': 'Tropical humid',
    },
    'Andhra Pradesh': {
        'dominant_soil': 'Red Soil / Black Soil',
        'typical_ph': 7.2, 'typical_oc': 0.45, 'typical_ec': 0.4,
        'typical_N': 225, 'typical_P': 18, 'typical_K': 220,
        'typical_Zn': 0.55, 'typical_Fe': 7.0, 'typical_Mn': 3.2,
        'typical_Cu': 0.35, 'typical_B': 0.4, 'typical_S': 9,
        'major_crops': ['Rice', 'Cotton', 'Chilli', 'Tobacco', 'Sugarcane'],
        'climate': 'Tropical',
    },
    'Telangana': {
        'dominant_soil': 'Red Soil / Black Soil',
        'typical_ph': 7.3, 'typical_oc': 0.42, 'typical_ec': 0.35,
        'typical_N': 220, 'typical_P': 16, 'typical_K': 200,
        'typical_Zn': 0.5, 'typical_Fe': 6.5, 'typical_Mn': 3.0,
        'typical_Cu': 0.3, 'typical_B': 0.35, 'typical_S': 8,
        'major_crops': ['Rice', 'Cotton', 'Maize', 'Soybean', 'Turmeric'],
        'climate': 'Semi-arid',
    },
    'Bihar': {
        'dominant_soil': 'Alluvial Soil',
        'typical_ph': 7.0, 'typical_oc': 0.50, 'typical_ec': 0.3,
        'typical_N': 240, 'typical_P': 18, 'typical_K': 160,
        'typical_Zn': 0.6, 'typical_Fe': 8.0, 'typical_Mn': 3.5,
        'typical_Cu': 0.35, 'typical_B': 0.45, 'typical_S': 10,
        'major_crops': ['Rice', 'Wheat', 'Maize', 'Lentil', 'Potato'],
        'climate': 'Sub-tropical humid',
    },
    'Odisha': {
        'dominant_soil': 'Laterite / Alluvial',
        'typical_ph': 5.8, 'typical_oc': 0.55, 'typical_ec': 0.25,
        'typical_N': 240, 'typical_P': 15, 'typical_K': 150,
        'typical_Zn': 0.5, 'typical_Fe': 12.0, 'typical_Mn': 4.5,
        'typical_Cu': 0.4, 'typical_B': 0.35, 'typical_S': 8,
        'major_crops': ['Rice', 'Groundnut', 'Sugarcane', 'Jute', 'Vegetables'],
        'climate': 'Tropical humid',
    },
    'Haryana': {
        'dominant_soil': 'Alluvial / Sandy',
        'typical_ph': 8.0, 'typical_oc': 0.35, 'typical_ec': 0.5,
        'typical_N': 200, 'typical_P': 15, 'typical_K': 220,
        'typical_Zn': 0.5, 'typical_Fe': 5.0, 'typical_Mn': 2.5,
        'typical_Cu': 0.3, 'typical_B': 0.35, 'typical_S': 9,
        'major_crops': ['Wheat', 'Rice', 'Mustard', 'Cotton', 'Sugarcane'],
        'climate': 'Semi-arid',
    },
    'Assam': {
        'dominant_soil': 'Alluvial / Laterite',
        'typical_ph': 5.2, 'typical_oc': 0.80, 'typical_ec': 0.2,
        'typical_N': 270, 'typical_P': 12, 'typical_K': 140,
        'typical_Zn': 0.6, 'typical_Fe': 15.0, 'typical_Mn': 5.0,
        'typical_Cu': 0.4, 'typical_B': 0.4, 'typical_S': 7,
        'major_crops': ['Rice', 'Tea', 'Jute', 'Sugarcane', 'Potato'],
        'climate': 'Tropical humid',
    },
}

# Approximate state boundaries (lat/lon bounding boxes) for GPS → state mapping
STATE_BOUNDS = {
    'Maharashtra':      (15.6, 22.0, 72.6, 80.9),
    'Punjab':           (29.5, 32.5, 73.8, 76.9),
    'Uttar Pradesh':    (23.8, 30.4, 77.0, 84.6),
    'Karnataka':        (11.6, 18.4, 74.0, 78.6),
    'Kerala':           (8.2, 12.8, 74.8, 77.4),
    'Tamil Nadu':       (8.0, 13.6, 76.2, 80.3),
    'Rajasthan':        (23.0, 30.2, 69.5, 78.2),
    'Madhya Pradesh':   (21.0, 26.9, 74.0, 82.8),
    'Gujarat':          (20.1, 24.7, 68.2, 74.5),
    'West Bengal':      (21.5, 27.2, 85.8, 89.9),
    'Andhra Pradesh':   (12.6, 19.9, 76.7, 84.8),
    'Telangana':        (15.8, 19.9, 77.2, 81.3),
    'Bihar':            (24.2, 27.5, 83.3, 88.2),
    'Odisha':           (17.8, 22.6, 81.3, 87.5),
    'Haryana':          (27.6, 30.9, 74.4, 77.6),
    'Assam':            (24.1, 28.0, 89.7, 96.0),
}


def get_state_from_coords(lat, lon):
    """Determine Indian state from GPS coordinates."""
    for state, (lat_min, lat_max, lon_min, lon_max) in STATE_BOUNDS.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return state
    return None


def get_soil_data_for_location(lat, lon):
    """Get historical soil data for a GPS location from the Indian soil database."""
    state = get_state_from_coords(lat, lon)
    if state and state in INDIA_SOIL_DB:
        data = INDIA_SOIL_DB[state].copy()
        data['state'] = state
        data['source'] = 'Soil Survey of India (state-level averages)'
        return {'success': True, **data}

    return {
        'success': False,
        'state': state or 'Unknown',
        'note': 'Location outside Indian soil database coverage. Using defaults.',
        'dominant_soil': 'Unknown',
        'typical_ph': 7.0, 'typical_oc': 0.5,
        'major_crops': [],
    }


def get_full_context(lat, lon):
    """One call to get everything: weather + season + soil data."""
    weather = get_weather(lat, lon)
    season = detect_season(lat, lon)
    soil_data = get_soil_data_for_location(lat, lon)

    return {
        'weather': weather,
        'season': season,
        'regional_soil': soil_data,
        'coordinates': {'lat': lat, 'lon': lon},
    }
