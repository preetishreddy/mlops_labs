import joblib, pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

PROC = Path(__file__).resolve().parents[1] / "data" / "processed.parquet"
ART  = Path(__file__).resolve().parents[1] / "model"; ART.mkdir(parents=True, exist_ok=True)

def main():
    df = pd.read_parquet(PROC)
    X, y = df["text"], df["label"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(min_df=2, ngram_range=(1,2))),
        ("clf", LogisticRegression(max_iter=300))
    ])
    pipe.fit(Xtr, ytr)
    joblib.dump(pipe, ART / "sms_model.joblib")
    pd.DataFrame({"text": Xte, "label": yte}).to_parquet(ART / "test.parquet")
    print("model saved")

if __name__ == "__main__":
    main()
