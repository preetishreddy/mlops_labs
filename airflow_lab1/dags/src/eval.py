import joblib, pandas as pd
from pathlib import Path
from sklearn.metrics import classification_report, roc_auc_score

ART = Path(__file__).resolve().parents[1] / "model"

def main():
    pipe = joblib.load(ART / "sms_model.joblib")
    te = pd.read_parquet(ART / "test.parquet")
    proba = pipe.predict_proba(te["text"])[:,1]
    pred = (proba >= 0.5).astype(int)
    print(classification_report(te["label"], pred, digits=4))
    print("ROC AUC:", roc_auc_score(te["label"], proba))

if __name__ == "__main__":
    main()
