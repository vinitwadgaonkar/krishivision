"""
KrishiVision — AI Farm Intelligence Platform
One photo + zero typing = complete soil & crop analysis.
"""

import os
import numpy as np
import joblib
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from soil_vision import analyze_soil_image
from leaf_doctor import analyze_leaf_image
from geo_intelligence import get_full_context, get_weather, detect_season, get_soil_data_for_location
from train_model import compute_soil_health_index, classify_health, generate_fertilizer_recommendations
from market_prices import get_prices_for_recommendations

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

MODELS_DIR = "models"


def load_models():
    models = {}
    try:
        models['sqi_regressor'] = joblib.load(os.path.join(MODELS_DIR, "sqi_regressor.pkl"))
        models['health_classifier'] = joblib.load(os.path.join(MODELS_DIR, "health_classifier.pkl"))
        models['soil_scaler'] = joblib.load(os.path.join(MODELS_DIR, "soil_scaler.pkl"))
        models['health_le'] = joblib.load(os.path.join(MODELS_DIR, "health_label_encoder.pkl"))
        models['soil_features'] = joblib.load(os.path.join(MODELS_DIR, "soil_features.pkl"))
        models['crop_classifier'] = joblib.load(os.path.join(MODELS_DIR, "crop_classifier.pkl"))
        models['crop_scaler'] = joblib.load(os.path.join(MODELS_DIR, "crop_scaler.pkl"))
        models['crop_le'] = joblib.load(os.path.join(MODELS_DIR, "crop_label_encoder.pkl"))
        models['crop_features'] = joblib.load(os.path.join(MODELS_DIR, "crop_features.pkl"))
        print("[OK] All models loaded.")
    except FileNotFoundError as e:
        print(f"[WARN] Model not found: {e}")
    return models


MODELS = load_models()


@app.route('/')
def index():
    return render_template('index.html')


# ── Soil Photo Analysis ──────────────────────────────────────────
@app.route('/api/scan-soil', methods=['POST'])
def scan_soil():
    """Analyze a soil photo + auto GPS context."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_bytes = request.files['image'].read()
    lat = request.form.get('lat', type=float)
    lon = request.form.get('lon', type=float)

    soil_analysis = analyze_soil_image(image_bytes)
    params = soil_analysis['predicted_params']

    geo_context = None
    if lat is not None and lon is not None:
        geo_context = get_full_context(lat, lon)
        if geo_context['weather'].get('success'):
            params['temperature'] = geo_context['weather']['temperature']
            params['humidity'] = geo_context['weather']['humidity']
            params['rainfall'] = geo_context['weather'].get('rainfall_3day', 100)

    sqi = compute_soil_health_index(params)
    rating = classify_health(sqi)
    fert = generate_fertilizer_recommendations(params)

    ml_result = _run_ml_prediction(params)
    crop_recs = _get_crop_recommendations(params)

    state = None
    if geo_context and geo_context.get('regional_soil', {}).get('success'):
        state = geo_context['regional_soil'].get('state')
    market_prices = get_prices_for_recommendations(crop_recs, state)

    return jsonify({
        'soil_analysis': soil_analysis,
        'soil_health': {
            'sqi': round(ml_result.get('sqi', sqi), 3),
            'sqi_formula': round(sqi, 3),
            'rating': ml_result.get('rating', rating),
        },
        'nutrient_status': _get_nutrient_status(params),
        'crop_recommendations': crop_recs,
        'market_prices': market_prices,
        'fertilizer_recommendations': fert,
        'geo_context': geo_context,
    })


# ── Leaf Photo Analysis ──────────────────────────────────────────
@app.route('/api/scan-leaf', methods=['POST'])
def scan_leaf():
    """Analyze a crop leaf photo for deficiencies and diseases."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_bytes = request.files['image'].read()
    lat = request.form.get('lat', type=float)
    lon = request.form.get('lon', type=float)

    leaf_result = analyze_leaf_image(image_bytes)

    geo_context = None
    if lat is not None and lon is not None:
        geo_context = get_full_context(lat, lon)

    return jsonify({
        'leaf_analysis': leaf_result,
        'geo_context': geo_context,
    })


# ── Auto-Context (GPS only) ─────────────────────────────────────
@app.route('/api/context', methods=['GET'])
def get_context():
    """Get full auto-context from GPS coordinates."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon required'}), 400
    return jsonify(get_full_context(lat, lon))


# ── Manual Input (kept from v1) ─────────────────────────────────
@app.route('/api/analyze-manual', methods=['POST'])
def analyze_manual():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    params = {}
    field_map = {
        'pH': 'pH', 'ec': 'EC', 'oc': 'OC',
        'nitrogen': 'N', 'phosphorus': 'P', 'potassium': 'K',
        'sulphur': 'S', 'zinc': 'Zn', 'boron': 'B',
        'iron': 'Fe', 'copper': 'Cu', 'manganese': 'Mn',
        'temperature': 'temperature', 'humidity': 'humidity',
        'rainfall': 'rainfall',
    }
    for input_key, param_key in field_map.items():
        if input_key in data and data[input_key] not in (None, '', 'null'):
            try:
                params[param_key] = float(data[input_key])
            except (ValueError, TypeError):
                pass

    if len(params) < 3:
        return jsonify({'error': 'Need at least 3 soil parameters'}), 400

    sqi = compute_soil_health_index(params)
    rating = classify_health(sqi)
    ml_result = _run_ml_prediction(params)
    crop_recs = _get_crop_recommendations(params)
    fert = generate_fertilizer_recommendations(params)
    market_prices = get_prices_for_recommendations(crop_recs)

    return jsonify({
        'soil_health': {
            'sqi': round(ml_result.get('sqi', sqi), 3),
            'sqi_formula': round(sqi, 3),
            'rating': ml_result.get('rating', rating),
            'rating_confidence': ml_result.get('confidence', {}),
        },
        'nutrient_status': _get_nutrient_status(params),
        'crop_recommendations': crop_recs,
        'market_prices': market_prices,
        'fertilizer_recommendations': fert,
        'input_values': params,
    })


# ── Internal helpers ─────────────────────────────────────────────

def _run_ml_prediction(params):
    if not MODELS or 'sqi_regressor' not in MODELS:
        return {}
    features = MODELS['soil_features']
    vals = [params.get(f, _default(f)) for f in features]
    X = np.array([vals])
    X_scaled = MODELS['soil_scaler'].transform(X)

    sqi = float(np.clip(MODELS['sqi_regressor'].predict(X_scaled)[0], 0, 1))
    idx = MODELS['health_classifier'].predict(X_scaled)[0]
    rating = MODELS['health_le'].inverse_transform([idx])[0]
    proba = MODELS['health_classifier'].predict_proba(X_scaled)[0]
    conf = {n: round(float(p), 3) for n, p in zip(MODELS['health_le'].classes_, proba)}

    sqi_formula = compute_soil_health_index(params)
    combined = round(0.4 * sqi_formula + 0.6 * sqi, 3)

    return {'sqi': combined, 'rating': classify_health(combined), 'confidence': conf}


def _get_crop_recommendations(params):
    if not MODELS or 'crop_classifier' not in MODELS:
        return []
    mapping = {
        'Nitrogen': params.get('N', 250), 'Phosphorus': params.get('P', 20),
        'Potassium': params.get('K', 150), 'Temperature': params.get('temperature', 25),
        'Humidity': params.get('humidity', 70), 'pH_Value': params.get('pH', 7.0),
        'Rainfall': params.get('rainfall', 150),
    }
    X = np.array([[mapping[f] for f in MODELS['crop_features']]])
    X_scaled = MODELS['crop_scaler'].transform(X)
    proba = MODELS['crop_classifier'].predict_proba(X_scaled)[0]
    top = proba.argsort()[-5:][::-1]
    names = MODELS['crop_le'].classes_
    return [{'crop': names[i], 'confidence': round(float(proba[i]), 3)}
            for i in top if proba[i] > 0.01]


def _get_nutrient_status(params):
    thresholds = {
        'pH':  {'ranges': [(0,5.5,'Very Acidic'),(5.5,6.5,'Acidic'),(6.5,7.5,'Optimal'),(7.5,8.5,'Alkaline'),(8.5,14,'Very Alkaline')], 'unit': ''},
        'EC':  {'ranges': [(0,1.0,'Normal'),(1.0,2.0,'Slightly Saline'),(2.0,4.0,'Saline'),(4.0,100,'Very Saline')], 'unit': 'dS/m'},
        'OC':  {'ranges': [(0,0.5,'Low'),(0.5,0.75,'Medium'),(0.75,100,'High')], 'unit': '%'},
        'N':   {'ranges': [(0,200,'Low'),(200,400,'Medium'),(400,10000,'High')], 'unit': 'kg/ha'},
        'P':   {'ranges': [(0,10,'Low'),(10,25,'Medium'),(25,10000,'High')], 'unit': 'kg/ha'},
        'K':   {'ranges': [(0,115,'Low'),(115,280,'Medium'),(280,10000,'High')], 'unit': 'kg/ha'},
        'S':   {'ranges': [(0,10,'Deficient'),(10,20,'Sufficient'),(20,1000,'High')], 'unit': 'mg/kg'},
        'Zn':  {'ranges': [(0,0.6,'Deficient'),(0.6,1.2,'Sufficient'),(1.2,100,'High')], 'unit': 'mg/kg'},
        'B':   {'ranges': [(0,0.5,'Deficient'),(0.5,1.0,'Sufficient'),(1.0,100,'High')], 'unit': 'mg/kg'},
        'Fe':  {'ranges': [(0,4.5,'Deficient'),(4.5,9.0,'Sufficient'),(9.0,1000,'High')], 'unit': 'mg/kg'},
        'Cu':  {'ranges': [(0,0.2,'Deficient'),(0.2,0.4,'Sufficient'),(0.4,100,'High')], 'unit': 'mg/kg'},
        'Mn':  {'ranges': [(0,2.0,'Deficient'),(2.0,4.0,'Sufficient'),(4.0,1000,'High')], 'unit': 'ppm'},
    }
    status = {}
    for key, info in thresholds.items():
        val = params.get(key)
        if val is None:
            continue
        level = 'Unknown'
        for low, high, label in info['ranges']:
            if low <= val < high:
                level = label
                break
        status[key] = {'value': val, 'unit': info['unit'], 'status': level}
    return status


def _default(f):
    return {'pH':7,'EC':0.5,'OC':0.5,'P':20,'K':150,'S':10,'Zn':0.6,'B':0.5,'Fe':5,'Cu':0.3,'Mn':2}.get(f, 0)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('RAILWAY_ENVIRONMENT') is None
    app.run(debug=debug, host='0.0.0.0', port=port)
