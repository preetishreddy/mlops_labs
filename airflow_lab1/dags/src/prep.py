import pandas as pd
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "file.csv"
PROC = Path(__file__).resolve().parents[1] / "data" / "processed.parquet"

def main():
    df = pd.read_csv(RAW)
    df["label"] = (df["label"] == "spam").astype(int)
    df["text"] = df["text"].fillna("")
    df.to_parquet(PROC)
    print(f"saved {PROC} rows={len(df)}")

if __name__ == "__main__":
    main()
