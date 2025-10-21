import json
import re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from typing import Iterable, Set, List
import pyarrow as pa
from apache_beam.io.parquetio import WriteToParquet

# ---------- constants ----------
BOT_RE = re.compile(r"(bot|crawler|spider)", re.IGNORECASE)

# ---------- parsing / cleaning ----------
class ParseJson(beam.DoFn):
    """Parse JSONL lines into dicts, skipping malformed or incomplete ones."""
    def process(self, line: str):
        try:
            rec = json.loads(line)
            must = {"ts", "user_id", "endpoint", "status", "latency_ms", "ua"}
            if must.issubset(rec.keys()):
                yield rec
        except Exception:
            return

def is_not_bot(rec: dict) -> bool:
    """Filter out requests made by bots."""
    return not BOT_RE.search(rec.get("ua", ""))

def add_flags(rec: dict) -> dict:
    """Add is_success and endpoint_group fields."""
    r = dict(rec)
    r["is_success"] = 200 <= int(r["status"]) < 300
    r["endpoint_group"] = r["endpoint"].split("?")[0]
    return r

# ---------- KV converters ----------
def to_hit(rec: dict):     return rec["endpoint_group"], 1
def to_user(rec: dict):    return rec["endpoint_group"], rec["user_id"]
def to_latency(rec: dict): return rec["endpoint_group"], int(rec["latency_ms"])
def to_success(rec: dict): return rec["endpoint_group"], 1 if rec["is_success"] else 0

# ---------- custom combiners ----------
class UniqueUsersCombineFn(beam.CombineFn):
    """CombineFn to count unique users per key."""
    def create_accumulator(self) -> Set[str]: return set()
    def add_input(self, acc: Set[str], user_id: str) -> Set[str]:
        acc.add(user_id); return acc
    def merge_accumulators(self, accs: Iterable[Set[str]]) -> Set[str]:
        out = set()
        for a in accs: out |= a
        return out
    def extract_output(self, acc: Set[str]) -> int:
        return len(acc)

class PercentileCombineFn(beam.CombineFn):
    """Compute percentile (default p95) for latency values."""
    def __init__(self, pct=95): self.pct = pct
    def create_accumulator(self) -> List[float]: return []
    def add_input(self, acc: List[float], x: float) -> List[float]:
        acc.append(float(x)); return acc
    def merge_accumulators(self, accs: Iterable[List[float]]) -> List[float]:
        out: List[float] = []
        for a in accs: out.extend(a)
        return out
    def extract_output(self, acc: List[float]) -> float:
        if not acc:
            return 0.0
        acc.sort()
        k = int(round((self.pct / 100) * (len(acc) - 1)))
        return acc[k]

# ---------- main pipeline ----------
def run(input_path: str, out_prefix: str, beam_args=None):
    """Run Beam pipeline to compute metrics and write Parquet."""
    options = PipelineOptions(beam_args or [])

    # define schema for Parquet
    schema = pa.schema([
        ("endpoint", pa.string()),
        ("total_hits", pa.int64()),
        ("unique_users", pa.int64()),
        ("p95_latency_ms", pa.int64()),
        ("success_rate", pa.float64()),
    ])

    with beam.Pipeline(options=options) as p:
        recs = (
            p
            | "ReadInput" >> beam.io.ReadFromText(input_path)
            | "ParseJson" >> beam.ParDo(ParseJson())
            | "FilterBots" >> beam.Filter(is_not_bot)
            | "AddFlags" >> beam.Map(add_flags)
        )

        # --- unique labels to avoid collisions ---
        hits = (
            recs
            | "KV_Hits" >> beam.Map(to_hit)
            | "SumHits" >> beam.CombinePerKey(sum)
        )

        uniques = (
            recs
            | "KV_Users" >> beam.Map(to_user)
            | "CountUniqueUsers" >> beam.CombinePerKey(UniqueUsersCombineFn())
        )

        p95 = (
            recs
            | "KV_Latency" >> beam.Map(to_latency)
            | "CalcP95" >> beam.CombinePerKey(PercentileCombineFn(95))
        )

        succ = (
            recs
            | "KV_Success" >> beam.Map(to_success)
            | "SumSuccess" >> beam.CombinePerKey(sum)
        )

        merged = (
            {'hits': hits, 'uniques': uniques, 'p95': p95, 'succ': succ}
            | "JoinMetrics" >> beam.CoGroupByKey()
        )

        rows = (
            merged
            | "ToDictRows" >> beam.Map(lambda kv: {
                "endpoint": kv[0],
                "total_hits": (kv[1]['hits'][0] if kv[1]['hits'] else 0),
                "unique_users": (kv[1]['uniques'][0] if kv[1]['uniques'] else 0),
                "p95_latency_ms": int(kv[1]['p95'][0]) if kv[1]['p95'] else 0,
                "success_rate": (
                    (kv[1]['succ'][0] / kv[1]['hits'][0])
                    if (kv[1]['hits'] and kv[1]['hits'][0] > 0 and kv[1]['succ'])
                    else 0.0
                ),
            })
        )

        _ = rows | "WriteParquet" >> WriteToParquet(
            file_path_prefix=out_prefix,
            schema=schema,
            file_name_suffix=".parquet",
            num_shards=1  # one file while learning
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_logs.jsonl", help="Input JSONL log file")
    parser.add_argument("--out_prefix", default="out/metrics_parquet", help="Output Parquet file prefix")
    args, beam_args = parser.parse_known_args()
    run(args.input, args.out_prefix, beam_args=beam_args)
