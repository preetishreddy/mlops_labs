import requests, zipfile, io, pandas as pd
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "file.csv"
URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip"

def main():
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading dataset...")
    r = requests.get(URL, timeout=120)
    print("Status:", r.status_code)
    if r.status_code != 200:
        raise RuntimeError("Failed to download dataset")

    z = zipfile.ZipFile(io.BytesIO(r.content))
    print("Extracting SMSSpamCollection...")
    text = z.read("SMSSpamCollection").decode("utf-8")
    rows = [line.split("\t", 1) for line in text.splitlines() if "\t" in line]
    df = pd.DataFrame(rows, columns=["label", "text"])
    df.to_csv(RAW, index=False)
    print(f"Saved {RAW}, rows={len(df)}")

if __name__ == "__main__":
    main()
