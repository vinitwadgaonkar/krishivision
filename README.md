# Soil Health Card Analyzer

AI-powered web application that analyzes Indian Soil Health Cards using OCR and Machine Learning to predict soil quality, recommend crops, and suggest fertilizers.

## Features

- **Camera Capture**: Take photos of soil health cards directly from your mobile camera
- **Image Upload**: Upload existing soil health card images for OCR analysis
- **Manual Input**: Enter soil parameters directly for instant analysis
- **ML Prediction**: Soil Health Index (SQI) prediction using Gradient Boosting (R²=0.978)
- **Crop Recommendations**: 22-crop classification with 99.3% accuracy
- **Fertilizer Guidance**: Rule-based recommendations following Indian Soil Health Card standards

## Real-World Datasets

- **Kerala Soil Nutrient Dataset** (2000+ samples) — pH, EC, OC, P, K, Ca, Mg, S, Zn, B, Fe, Cu, Mn
- **Kaggle Crop Recommendation Dataset** (2200 samples) — N, P, K, temperature, humidity, pH, rainfall

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: install Tesseract for OCR (macOS)
brew install tesseract

# Train models
python train_model.py

# Start server
python app.py
```

Open http://localhost:8080 on your phone or desktop.

## Project Structure

```
soil-health-analyzer/
├── app.py               # Flask backend
├── train_model.py       # ML model training
├── ocr_processor.py     # OCR + regex parser
├── requirements.txt     # Dependencies
├── data/                # Real-world datasets
├── models/              # Trained ML models
├── templates/           # HTML templates
└── static/              # CSS + JS
```
