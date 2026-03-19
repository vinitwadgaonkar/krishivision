"""
Train soil health prediction models using real-world datasets:
1. Kerala Soil Nutrient Dataset (6000+ samples) - for soil health scoring
2. Kaggle Crop Recommendation Dataset (2200 samples) - for crop recommendation
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

MODELS_DIR = "models"
DATA_DIR = "data"
os.makedirs(MODELS_DIR, exist_ok=True)

# Indian Government soil health card rating thresholds
SOIL_THRESHOLDS = {
    'pH':         {'low': 6.5, 'high': 7.5, 'ideal': 7.0},
    'EC':         {'max': 1.0},
    'OC':         {'low': 0.50, 'medium': 0.75, 'high': 1.0},
    'P':          {'low': 10, 'medium': 25, 'high': 50},
    'K':          {'low': 115, 'medium': 280, 'high': 400},
    'S':          {'min': 10},
    'Zn':         {'min': 0.6},
    'B':          {'min': 0.5},
    'Fe':         {'min': 4.5},
    'Cu':         {'min': 0.2},
    'Mn':         {'min': 2.0},
}


def compute_soil_health_index(row):
    """
    Compute Soil Quality Index (SQI) based on Indian Soil Health Card standards.
    Each parameter scored 0-1, weighted average gives final SQI.
    """
    scores = []
    weights = []

    # pH score (bell curve around 7.0, range 6.5-7.5 ideal)
    ph = row.get('pH', 7.0)
    if 6.5 <= ph <= 7.5:
        ph_score = 1.0 - abs(ph - 7.0) / 1.5
    elif ph < 4.0 or ph > 9.5:
        ph_score = 0.0
    else:
        ph_score = max(0, 0.5 - abs(ph - 7.0) / 5.0)
    scores.append(ph_score)
    weights.append(0.10)

    # EC score (lower is better, <1 good)
    ec = row.get('EC', 0.5)
    ec_score = max(0, 1.0 - ec / 2.0) if ec < 4.0 else 0.0
    scores.append(ec_score)
    weights.append(0.05)

    # Organic Carbon (higher better up to 1.5%)
    oc = row.get('OC', 0.5)
    oc_score = min(1.0, oc / 1.0) if oc > 0 else 0.0
    scores.append(oc_score)
    weights.append(0.15)

    # Phosphorus
    p = row.get('P', 20)
    if p >= 25:
        p_score = 1.0
    elif p >= 10:
        p_score = 0.5 + 0.5 * (p - 10) / 15
    else:
        p_score = max(0, p / 20)
    scores.append(p_score)
    weights.append(0.12)

    # Potassium
    k = row.get('K', 150)
    if k >= 280:
        k_score = 1.0
    elif k >= 115:
        k_score = 0.5 + 0.5 * (k - 115) / 165
    else:
        k_score = max(0, k / 230)
    scores.append(k_score)
    weights.append(0.12)

    # Micronutrients scored against minimum thresholds
    micro_map = {'S': 0.08, 'Zn': 0.10, 'Fe': 0.08, 'Cu': 0.06, 'Mn': 0.07, 'B': 0.07}
    for nutrient, weight in micro_map.items():
        val = row.get(nutrient, 0)
        threshold = SOIL_THRESHOLDS[nutrient].get('min', 1.0)
        if val >= threshold * 1.5:
            score = 1.0
        elif val >= threshold:
            score = 0.6 + 0.4 * (val - threshold) / (threshold * 0.5)
        else:
            score = max(0, val / (threshold * 1.5))
        scores.append(score)
        weights.append(weight)

    total_weight = sum(weights)
    sqi = sum(s * w for s, w in zip(scores, weights)) / total_weight
    return round(sqi, 3)


def classify_health(sqi):
    if sqi >= 0.65:
        return 'Good'
    elif sqi >= 0.45:
        return 'Medium'
    else:
        return 'Poor'


def load_and_prepare_soil_data():
    """Load Kerala soil dataset, clean, and engineer features."""
    print("Loading Kerala soil dataset...")
    df = pd.read_csv(os.path.join(DATA_DIR, "soil_kerala.csv"), on_bad_lines='skip')
    print(f"  Raw rows: {len(df)}")

    feature_cols = {
        'Soil_pH': 'pH', 'Soil_ec': 'EC', 'Soil_OrganicC': 'OC',
        'Soil_P': 'P', 'Soil_k': 'K', 'Soil_Ca': 'Ca', 'Soil_Mg': 'Mg',
        'Soil_s': 'S', 'Soil_Zn': 'Zn', 'Soil_b': 'B',
        'Soil_Fe': 'Fe', 'Soil_Cu': 'Cu', 'Soil_Mn': 'Mn'
    }

    soil = df[list(feature_cols.keys()) + ['SoilType', 'crop1']].copy()
    soil.rename(columns=feature_cols, inplace=True)

    numeric_cols = ['pH', 'EC', 'OC', 'P', 'K', 'Ca', 'Mg', 'S', 'Zn', 'B', 'Fe', 'Cu', 'Mn']
    for col in numeric_cols:
        soil[col] = pd.to_numeric(soil[col], errors='coerce')

    soil.dropna(subset=['pH', 'OC', 'P', 'K'], inplace=True)

    for col in ['S', 'Zn', 'B', 'Fe', 'Cu', 'Mn', 'Ca', 'Mg', 'EC']:
        soil[col] = soil[col].fillna(soil[col].median())

    soil['SQI'] = soil.apply(compute_soil_health_index, axis=1)
    soil['health_rating'] = soil['SQI'].apply(classify_health)

    print(f"  Clean rows: {len(soil)}")
    print(f"  Health distribution:\n{soil['health_rating'].value_counts()}")
    print(f"  SQI stats: mean={soil['SQI'].mean():.3f}, std={soil['SQI'].std():.3f}")
    return soil


def load_crop_data():
    """Load Kaggle crop recommendation dataset."""
    print("\nLoading Crop Recommendation dataset...")
    df = pd.read_csv(os.path.join(DATA_DIR, "crop_recommendation.csv"))
    print(f"  Rows: {len(df)}, Crops: {df['Crop'].nunique()}")
    print(f"  Crops: {sorted(df['Crop'].unique())}")
    return df


def train_soil_health_model(soil_df):
    """Train model to predict SQI and health rating from soil parameters."""
    print("\n=== Training Soil Health Index (SQI) Regressor ===")
    features = ['pH', 'EC', 'OC', 'P', 'K', 'S', 'Zn', 'B', 'Fe', 'Cu', 'Mn']
    X = soil_df[features].values
    y_sqi = soil_df['SQI'].values
    y_rating = soil_df['health_rating'].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_sqi, test_size=0.2, random_state=42
    )

    reg = GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42
    )
    reg.fit(X_train, y_train)

    y_pred = reg.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"  RMSE: {rmse:.4f}, R²: {r2:.4f}")

    cv_scores = cross_val_score(reg, X_scaled, y_sqi, cv=5, scoring='r2')
    print(f"  5-Fold CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    print("\n=== Training Health Rating Classifier ===")
    le_rating = LabelEncoder()
    y_cls = le_rating.fit_transform(y_rating)

    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_scaled, y_cls, test_size=0.2, random_state=42, stratify=y_cls
    )

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=10, random_state=42, class_weight='balanced'
    )
    clf.fit(X_train_c, y_train_c)

    y_pred_c = clf.predict(X_test_c)
    print(classification_report(y_test_c, y_pred_c, target_names=le_rating.classes_))

    importances = dict(zip(features, reg.feature_importances_))
    print("  Feature importances (SQI):")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"    {feat}: {imp:.4f}")

    joblib.dump(reg, os.path.join(MODELS_DIR, "sqi_regressor.pkl"))
    joblib.dump(clf, os.path.join(MODELS_DIR, "health_classifier.pkl"))
    joblib.dump(scaler, os.path.join(MODELS_DIR, "soil_scaler.pkl"))
    joblib.dump(le_rating, os.path.join(MODELS_DIR, "health_label_encoder.pkl"))
    joblib.dump(features, os.path.join(MODELS_DIR, "soil_features.pkl"))
    print("  Soil health models saved.")


def train_crop_recommendation_model(crop_df):
    """Train crop recommendation model from Kaggle dataset."""
    print("\n=== Training Crop Recommendation Model ===")
    features = ['Nitrogen', 'Phosphorus', 'Potassium', 'Temperature', 'Humidity', 'pH_Value', 'Rainfall']
    X = crop_df[features].values
    le_crop = LabelEncoder()
    y = le_crop.fit_transform(crop_df['Crop'].values)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=300, max_depth=15, random_state=42
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = (y_pred == y_test).mean()
    print(f"  Accuracy: {accuracy:.4f}")

    cv_scores = cross_val_score(clf, X_scaled, y, cv=5, scoring='accuracy')
    print(f"  5-Fold CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    joblib.dump(clf, os.path.join(MODELS_DIR, "crop_classifier.pkl"))
    joblib.dump(scaler, os.path.join(MODELS_DIR, "crop_scaler.pkl"))
    joblib.dump(le_crop, os.path.join(MODELS_DIR, "crop_label_encoder.pkl"))
    joblib.dump(features, os.path.join(MODELS_DIR, "crop_features.pkl"))
    print("  Crop recommendation model saved.")


def generate_fertilizer_recommendations(soil_params):
    """
    Rule-based fertilizer recommendation engine following Indian Soil Health Card
    standards from State Agricultural Universities.
    """
    recs = {'deficiencies': [], 'fertilizers': [], 'amendments': []}

    ph = soil_params.get('pH', 7.0)
    if ph < 6.5:
        recs['amendments'].append(f"Apply agricultural lime at 2-4 tonnes/hectare (pH={ph}, acidic)")
    elif ph > 7.5:
        recs['amendments'].append(f"Apply gypsum at 2-5 tonnes/hectare (pH={ph}, alkaline)")

    oc = soil_params.get('OC', 0.5)
    if oc < 0.5:
        recs['deficiencies'].append('Organic Carbon (Very Low)')
        recs['amendments'].append("FYM/Compost: 6-8 tonnes/hectare")
    elif oc < 0.75:
        recs['deficiencies'].append('Organic Carbon (Low)')
        recs['amendments'].append("FYM/Compost: 4-6 tonnes/hectare")

    p = soil_params.get('P', 20)
    k = soil_params.get('K', 150)

    if p < 10:
        recs['deficiencies'].append('Phosphorus (Low)')
        recs['fertilizers'].append("DAP: 80-100 Kg/Ha OR SSP: 200-250 Kg/Ha")
    elif p < 25:
        recs['fertilizers'].append("DAP: 40-60 Kg/Ha OR SSP: 100-150 Kg/Ha")

    if k < 115:
        recs['deficiencies'].append('Potassium (Low)')
        recs['fertilizers'].append("MOP: 80-100 Kg/Ha")
    elif k < 280:
        recs['fertilizers'].append("MOP: 50-70 Kg/Ha")

    s = soil_params.get('S', 10)
    if s < 10:
        recs['deficiencies'].append('Sulphur (Low)')
        recs['fertilizers'].append("Bentonite Sulphur: 10-15 Kg/Ha")

    zn = soil_params.get('Zn', 0.6)
    if zn < 0.6:
        recs['deficiencies'].append('Zinc (Low)')
        recs['fertilizers'].append("Zinc Sulphate: 20-25 Kg/Ha")

    b = soil_params.get('B', 0.5)
    if b < 0.5:
        recs['deficiencies'].append('Boron (Low)')
        recs['fertilizers'].append("Borax: 5-10 Kg/Ha")

    fe = soil_params.get('Fe', 4.5)
    if fe < 4.5:
        recs['deficiencies'].append('Iron (Low)')
        recs['fertilizers'].append("Ferrous Sulphate: 20-25 Kg/Ha")

    cu = soil_params.get('Cu', 0.2)
    if cu < 0.2:
        recs['deficiencies'].append('Copper (Low)')
        recs['fertilizers'].append("Copper Sulphate: 5-10 Kg/Ha")

    mn = soil_params.get('Mn', 2.0)
    if mn < 2.0:
        recs['deficiencies'].append('Manganese (Low)')
        recs['fertilizers'].append("Manganese Sulphate: 10-15 Kg/Ha")

    urea_needed = max(0, (280 - soil_params.get('N', 250)) * 0.8)
    if urea_needed > 0:
        recs['fertilizers'].append(f"Urea: {urea_needed:.0f} Kg/Ha (for Nitrogen)")

    return recs


if __name__ == "__main__":
    print("=" * 60)
    print("  SOIL HEALTH ANALYZER — MODEL TRAINING")
    print("=" * 60)

    soil_df = load_and_prepare_soil_data()
    train_soil_health_model(soil_df)

    crop_df = load_crop_data()
    train_crop_recommendation_model(crop_df)

    print("\n=== Testing Fertilizer Recommendation Engine ===")
    test_params = {
        'pH': 8.27, 'EC': 0.10, 'OC': 0.21, 'N': 256,
        'P': 19.19, 'K': 174, 'S': 3.09, 'Zn': 0.46,
        'B': 0.20, 'Fe': 3.83, 'Cu': 0.15, 'Mn': 1.37
    }
    sqi = compute_soil_health_index(test_params)
    rating = classify_health(sqi)
    recs = generate_fertilizer_recommendations(test_params)

    print(f"  Test SQI: {sqi} ({rating})")
    print(f"  Deficiencies: {recs['deficiencies']}")
    print(f"  Fertilizers: {recs['fertilizers']}")
    print(f"  Amendments: {recs['amendments']}")

    print("\n" + "=" * 60)
    print("  ALL MODELS TRAINED AND SAVED SUCCESSFULLY")
    print("=" * 60)
