import joblib, pandas as pd
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "model"
TEST = Path(__file__).resolve().parents[1] / "data" / "test.csv"

def main():
    pipe = joblib.load(ART / "sms_model.joblib")
    df = pd.read_csv(TEST)   # must have a 'text' column
    df["spam_prob"] = pipe.predict_proba(df["text"])[:,1]
    df.to_csv(ART / "batch_scored.csv", index=False)
    print("wrote", ART / "batch_scored.csv")

if __name__ == "__main__":
    main()
