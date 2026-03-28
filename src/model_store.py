import os
import joblib

ARTIFACT_DIR = "artifacts"
MODEL_PATH = os.path.join(ARTIFACT_DIR, "arima_model.pkl")

def ensure_artifact_dir():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

def save_model(model):
    ensure_artifact_dir()
    joblib.dump(model, MODEL_PATH)

def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)