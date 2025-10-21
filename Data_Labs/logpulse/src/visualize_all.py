# src/visualize_all.py
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

REQUIRED_COLS = {"endpoint","total_hits","unique_users","p95_latency_ms","success_rate"}

def _validate(df: pd.DataFrame):
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

def _save_bar(df: pd.DataFrame, xcol: str, ycol: str, title: str, ylab: str, out_png: str, ylim=None):
    plt.figure()
    plt.bar(df[xcol], df[ycol])
    plt.title(title)
    plt.xlabel(xcol.replace("_", " ").title())
    plt.ylabel(ylab)
    if ylim is not None:
        plt.ylim(*ylim)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

def visualize_all(csv_path: str = "out/step5_metrics.csv",
                  out_dir: str = "out/plots",
                  sort_by: str | None = "total_hits",
                  make_pdf: bool = True,
                  pdf_name: str = "logpulse_dashboard.pdf"):
    os.makedirs(out_dir, exist_ok=True)

    # Load & validate
    df = pd.read_csv(csv_path)
    _validate(df)

    # Optional sorting for nicer visuals
    if sort_by and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False).reset_index(drop=True)

    # 1) PNGs
    png_hits   = os.path.join(out_dir, "total_hits_per_endpoint.png")
    png_users  = os.path.join(out_dir, "unique_users_per_endpoint.png")
    png_p95    = os.path.join(out_dir, "p95_latency_per_endpoint.png")
    png_succ   = os.path.join(out_dir, "success_rate_per_endpoint.png")

    _save_bar(df, "endpoint", "total_hits",
              "Total Hits per Endpoint", "Total Hits", png_hits)
    _save_bar(df, "endpoint", "unique_users",
              "Unique Users per Endpoint", "Unique Users", png_users)
    _save_bar(df, "endpoint", "p95_latency_ms",
              "P95 Latency per Endpoint (ms)", "Latency (ms)", png_p95)
    # success rate in %
    df_pct = df.copy()
    df_pct["success_rate_pct"] = df_pct["success_rate"] * 100.0
    _save_bar(df_pct, "endpoint", "success_rate_pct",
              "Success Rate per Endpoint (%)", "Success Rate (%)", png_succ, ylim=(0, 100))

    # 2) Single PDF with all 4 pages
    pdf_path = os.path.join(out_dir, pdf_name)
    if make_pdf:
        with PdfPages(pdf_path) as pdf:
            for img in [png_hits, png_users, png_p95, png_succ]:
                fig = plt.figure()
                # Insert the PNG into a figure page
                arr = plt.imread(img)
                plt.imshow(arr)
                plt.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

    print("Saved:")
    print(f" - {png_hits}")
    print(f" - {png_users}")
    print(f" - {png_p95}")
    print(f" - {png_succ}")
    if make_pdf:
        print(f" - {pdf_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="out/step5_metrics.csv", help="Path to metrics CSV")
    parser.add_argument("--out_dir", default="out/plots", help="Where to save PNGs/PDF")
    parser.add_argument("--sort_by", default="total_hits", help="Column to sort bars by (or '' for none)")
    parser.add_argument("--no_pdf", action="store_true", help="If set, do not create PDF")
    parser.add_argument("--pdf_name", default="logpulse_dashboard.pdf", help="PDF filename")
    args = parser.parse_args()

    visualize_all(
        csv_path=args.csv,
        out_dir=args.out_dir,
        sort_by=(args.sort_by or None),
        make_pdf=(not args.no_pdf),
        pdf_name=args.pdf_name
    )
