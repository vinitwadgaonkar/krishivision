"""
Indian Crop Market Price Engine.
MSP (Minimum Support Price) 2025-26 from Government of India + typical mandi ranges.
Prices in INR per Quintal (100 kg).
"""

# Official MSP 2025-26 + typical wholesale mandi price ranges by crop
# Sources: CACP recommendations, Agmarknet historical data
CROP_PRICES = {
    'Rice': {
        'msp': 2320,
        'mandi_min': 1900, 'mandi_max': 3200, 'mandi_avg': 2500,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Punjab': {'avg': 2350, 'trend': 'stable'},
            'Haryana': {'avg': 2300, 'trend': 'stable'},
            'Uttar Pradesh': {'avg': 2200, 'trend': 'up'},
            'West Bengal': {'avg': 2450, 'trend': 'up'},
            'Andhra Pradesh': {'avg': 2600, 'trend': 'stable'},
            'Tamil Nadu': {'avg': 2550, 'trend': 'stable'},
            'Karnataka': {'avg': 2400, 'trend': 'up'},
            'Maharashtra': {'avg': 2350, 'trend': 'stable'},
        },
    },
    'Wheat': {
        'msp': 2425,
        'mandi_min': 2100, 'mandi_max': 3000, 'mandi_avg': 2550,
        'unit': '₹/Quintal',
        'season': 'Rabi',
        'top_states': {
            'Punjab': {'avg': 2450, 'trend': 'stable'},
            'Haryana': {'avg': 2400, 'trend': 'stable'},
            'Madhya Pradesh': {'avg': 2500, 'trend': 'up'},
            'Uttar Pradesh': {'avg': 2350, 'trend': 'stable'},
            'Rajasthan': {'avg': 2380, 'trend': 'up'},
            'Maharashtra': {'avg': 2600, 'trend': 'up'},
        },
    },
    'Maize': {
        'msp': 2225,
        'mandi_min': 1600, 'mandi_max': 2800, 'mandi_avg': 2100,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Karnataka': {'avg': 2150, 'trend': 'up'},
            'Rajasthan': {'avg': 1900, 'trend': 'stable'},
            'Bihar': {'avg': 2000, 'trend': 'up'},
            'Madhya Pradesh': {'avg': 2050, 'trend': 'stable'},
            'Maharashtra': {'avg': 2100, 'trend': 'up'},
            'Telangana': {'avg': 2200, 'trend': 'up'},
        },
    },
    'Cotton': {
        'msp': 7121,
        'mandi_min': 5500, 'mandi_max': 8500, 'mandi_avg': 7000,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Gujarat': {'avg': 7200, 'trend': 'up'},
            'Maharashtra': {'avg': 6800, 'trend': 'stable'},
            'Telangana': {'avg': 7000, 'trend': 'up'},
            'Andhra Pradesh': {'avg': 7100, 'trend': 'stable'},
            'Rajasthan': {'avg': 6600, 'trend': 'stable'},
            'Madhya Pradesh': {'avg': 6900, 'trend': 'up'},
        },
    },
    'Banana': {
        'msp': None,
        'mandi_min': 800, 'mandi_max': 3500, 'mandi_avg': 1800,
        'unit': '₹/Quintal',
        'season': 'Year-round',
        'top_states': {
            'Tamil Nadu': {'avg': 1600, 'trend': 'stable'},
            'Maharashtra': {'avg': 2000, 'trend': 'up'},
            'Gujarat': {'avg': 1500, 'trend': 'stable'},
            'Karnataka': {'avg': 1800, 'trend': 'up'},
            'Kerala': {'avg': 2200, 'trend': 'up'},
            'Andhra Pradesh': {'avg': 1700, 'trend': 'stable'},
        },
    },
    'Coffee': {
        'msp': None,
        'mandi_min': 8000, 'mandi_max': 45000, 'mandi_avg': 25000,
        'unit': '₹/Quintal',
        'season': 'Rabi',
        'top_states': {
            'Karnataka': {'avg': 28000, 'trend': 'up'},
            'Kerala': {'avg': 26000, 'trend': 'up'},
            'Tamil Nadu': {'avg': 24000, 'trend': 'up'},
        },
    },
    'Coconut': {
        'msp': 2800,
        'mandi_min': 1500, 'mandi_max': 4000, 'mandi_avg': 2700,
        'unit': '₹/Quintal',
        'season': 'Year-round',
        'top_states': {
            'Kerala': {'avg': 2800, 'trend': 'stable'},
            'Karnataka': {'avg': 2600, 'trend': 'stable'},
            'Tamil Nadu': {'avg': 2500, 'trend': 'up'},
            'Andhra Pradesh': {'avg': 2400, 'trend': 'stable'},
        },
    },
    'Grapes': {
        'msp': None,
        'mandi_min': 2000, 'mandi_max': 12000, 'mandi_avg': 5000,
        'unit': '₹/Quintal',
        'season': 'Rabi',
        'top_states': {
            'Maharashtra': {'avg': 5500, 'trend': 'up'},
            'Karnataka': {'avg': 4500, 'trend': 'stable'},
        },
    },
    'Mango': {
        'msp': None,
        'mandi_min': 1500, 'mandi_max': 10000, 'mandi_avg': 4000,
        'unit': '₹/Quintal',
        'season': 'Zaid',
        'top_states': {
            'Uttar Pradesh': {'avg': 3500, 'trend': 'up'},
            'Andhra Pradesh': {'avg': 4200, 'trend': 'up'},
            'Maharashtra': {'avg': 4000, 'trend': 'stable'},
            'Karnataka': {'avg': 3800, 'trend': 'stable'},
            'Gujarat': {'avg': 5000, 'trend': 'up'},
        },
    },
    'Watermelon': {
        'msp': None,
        'mandi_min': 300, 'mandi_max': 2000, 'mandi_avg': 800,
        'unit': '₹/Quintal',
        'season': 'Zaid',
        'top_states': {
            'Rajasthan': {'avg': 600, 'trend': 'stable'},
            'Karnataka': {'avg': 900, 'trend': 'up'},
            'Uttar Pradesh': {'avg': 700, 'trend': 'stable'},
            'Maharashtra': {'avg': 850, 'trend': 'up'},
        },
    },
    'Muskmelon': {
        'msp': None,
        'mandi_min': 500, 'mandi_max': 3000, 'mandi_avg': 1200,
        'unit': '₹/Quintal',
        'season': 'Zaid',
        'top_states': {
            'Rajasthan': {'avg': 1000, 'trend': 'stable'},
            'Uttar Pradesh': {'avg': 1100, 'trend': 'up'},
            'Maharashtra': {'avg': 1300, 'trend': 'up'},
        },
    },
    'Orange': {
        'msp': None,
        'mandi_min': 2000, 'mandi_max': 8000, 'mandi_avg': 4000,
        'unit': '₹/Quintal',
        'season': 'Rabi',
        'top_states': {
            'Maharashtra': {'avg': 4500, 'trend': 'up'},
            'Madhya Pradesh': {'avg': 3500, 'trend': 'stable'},
            'Rajasthan': {'avg': 3800, 'trend': 'stable'},
        },
    },
    'Papaya': {
        'msp': None,
        'mandi_min': 500, 'mandi_max': 3000, 'mandi_avg': 1500,
        'unit': '₹/Quintal',
        'season': 'Year-round',
        'top_states': {
            'Gujarat': {'avg': 1400, 'trend': 'stable'},
            'Andhra Pradesh': {'avg': 1600, 'trend': 'up'},
            'Karnataka': {'avg': 1300, 'trend': 'stable'},
            'Maharashtra': {'avg': 1500, 'trend': 'up'},
        },
    },
    'Pomegranate': {
        'msp': None,
        'mandi_min': 3000, 'mandi_max': 15000, 'mandi_avg': 7000,
        'unit': '₹/Quintal',
        'season': 'Year-round',
        'top_states': {
            'Maharashtra': {'avg': 7500, 'trend': 'up'},
            'Karnataka': {'avg': 6500, 'trend': 'stable'},
            'Rajasthan': {'avg': 6000, 'trend': 'stable'},
        },
    },
    'Apple': {
        'msp': None,
        'mandi_min': 4000, 'mandi_max': 18000, 'mandi_avg': 8000,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {},
    },
    'ChickPea': {
        'msp': 5650,
        'mandi_min': 4500, 'mandi_max': 7500, 'mandi_avg': 5800,
        'unit': '₹/Quintal',
        'season': 'Rabi',
        'top_states': {
            'Madhya Pradesh': {'avg': 5600, 'trend': 'stable'},
            'Rajasthan': {'avg': 5700, 'trend': 'up'},
            'Maharashtra': {'avg': 5900, 'trend': 'up'},
            'Karnataka': {'avg': 5500, 'trend': 'stable'},
            'Uttar Pradesh': {'avg': 5400, 'trend': 'stable'},
        },
    },
    'Lentil': {
        'msp': 6700,
        'mandi_min': 5000, 'mandi_max': 8000, 'mandi_avg': 6500,
        'unit': '₹/Quintal',
        'season': 'Rabi',
        'top_states': {
            'Madhya Pradesh': {'avg': 6400, 'trend': 'stable'},
            'Uttar Pradesh': {'avg': 6300, 'trend': 'up'},
            'Bihar': {'avg': 6200, 'trend': 'stable'},
            'Maharashtra': {'avg': 6600, 'trend': 'up'},
        },
    },
    'KidneyBeans': {
        'msp': None,
        'mandi_min': 5000, 'mandi_max': 12000, 'mandi_avg': 8000,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Maharashtra': {'avg': 8500, 'trend': 'up'},
            'Rajasthan': {'avg': 7500, 'trend': 'stable'},
        },
    },
    'PigeonPeas': {
        'msp': 7550,
        'mandi_min': 6000, 'mandi_max': 10000, 'mandi_avg': 7800,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Maharashtra': {'avg': 7600, 'trend': 'stable'},
            'Karnataka': {'avg': 7900, 'trend': 'up'},
            'Madhya Pradesh': {'avg': 7400, 'trend': 'stable'},
        },
    },
    'MothBeans': {
        'msp': 6225,
        'mandi_min': 5000, 'mandi_max': 9000, 'mandi_avg': 6500,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Rajasthan': {'avg': 6300, 'trend': 'stable'},
            'Maharashtra': {'avg': 6800, 'trend': 'up'},
        },
    },
    'MungBean': {
        'msp': 8682,
        'mandi_min': 6500, 'mandi_max': 11000, 'mandi_avg': 8500,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Rajasthan': {'avg': 8200, 'trend': 'stable'},
            'Maharashtra': {'avg': 8800, 'trend': 'up'},
            'Madhya Pradesh': {'avg': 8000, 'trend': 'stable'},
        },
    },
    'Blackgram': {
        'msp': 7400,
        'mandi_min': 5500, 'mandi_max': 9500, 'mandi_avg': 7200,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'Madhya Pradesh': {'avg': 7000, 'trend': 'stable'},
            'Maharashtra': {'avg': 7400, 'trend': 'up'},
            'Uttar Pradesh': {'avg': 7100, 'trend': 'stable'},
            'Andhra Pradesh': {'avg': 7300, 'trend': 'up'},
        },
    },
    'Jute': {
        'msp': 5335,
        'mandi_min': 4500, 'mandi_max': 7000, 'mandi_avg': 5500,
        'unit': '₹/Quintal',
        'season': 'Kharif',
        'top_states': {
            'West Bengal': {'avg': 5400, 'trend': 'stable'},
            'Bihar': {'avg': 5200, 'trend': 'stable'},
            'Assam': {'avg': 5100, 'trend': 'stable'},
        },
    },
}


def get_crop_price(crop_name, state=None):
    """Get market price info for a crop, optionally localized to a state."""
    crop = CROP_PRICES.get(crop_name)
    if not crop:
        return None

    result = {
        'crop': crop_name,
        'msp': crop['msp'],
        'national_avg': crop['mandi_avg'],
        'price_range': f"₹{crop['mandi_min']} - ₹{crop['mandi_max']}",
        'unit': crop['unit'],
        'season': crop['season'],
    }

    if state and state in crop.get('top_states', {}):
        state_data = crop['top_states'][state]
        result['state_price'] = state_data['avg']
        result['state'] = state
        result['trend'] = state_data['trend']
    else:
        result['state_price'] = crop['mandi_avg']
        result['state'] = 'National'
        result['trend'] = 'stable'

    return result


def get_prices_for_recommendations(crop_list, state=None):
    """Get prices for a list of recommended crops, sorted by profitability."""
    prices = []
    for item in crop_list:
        crop_name = item.get('crop', item) if isinstance(item, dict) else item
        price = get_crop_price(crop_name, state)
        if price:
            price['recommendation_confidence'] = item.get('confidence', 0) if isinstance(item, dict) else 0
            prices.append(price)

    prices.sort(key=lambda x: -(x.get('state_price', 0) or x.get('national_avg', 0)))
    return prices
