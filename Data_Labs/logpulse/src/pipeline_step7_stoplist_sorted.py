import json, re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from typing import Iterable, Set, List, Tuple

BOT_RE = re.compile(r"(bot|crawler|spider)", re.IGNORECASE)
STOP_ENDPOINTS = {"/healthz", "/metrics"}  # add any others you want to ignore

# ---------- parsing / cleaning ----------
class ParseJson(beam.DoFn):
    def process(self, line: str):
        try:
            rec = json.loads(line)
            must = {"ts","user_id","endpoint","status","latency_ms","ua"}
            if must.issubset(rec.keys()):
                yield rec
        except Exception:
            return

def is_not_bot(rec: dict) -> bool:
    return not BOT_RE.search(rec.get("ua", ""))

def add_flags(rec: dict) -> dict:
    r = dict(rec)
    r["is_success"] = 200 <= int(r["status"]) < 300
    r["endpoint_group"] = r["endpoint"].split("?")[0]
    return r

def not_stopped(rec: dict) -> bool:
    return rec["endpoint_group"] not in STOP_ENDPOINTS

# ---------- to KVs ----------
def to_hit(rec: dict) -> Tuple[str, int]:
    return rec["endpoint_group"], 1

def to_user(rec: dict) -> Tuple[str, str]:
    return rec["endpoint_group"], rec["user_id"]

def to_latency(rec: dict) -> Tuple[str, int]:
    return rec["endpoint_group"], int(rec["latency_ms"])

def to_success(rec: dict) -> Tuple[str, int]:
    return rec["endpoint_group"], 1 if rec["is_success"] else 0

# ---------- custom combiners ----------
class UniqueUsersCombineFn(beam.CombineFn):
    def create_accumulator(self) -> Set[str]: return set()
    def add_input(self, acc: Set[str], user_id: str) -> Set[str]:
        acc.add(user_id); return acc
    def merge_accumulators(self, accs: Iterable[Set[str]]) -> Set[str]:
        out = set()
        for a in accs: out |= a
        return out
    def extract_output(self, acc: Set[str]) -> int: return len(acc)

class PercentileCombineFn(beam.CombineFn):
    def __init__(self, pct=95): self.pct = pct
    def create_accumulator(self) -> List[float]: return []
    def add_input(self, acc: List[float], x: float) -> List[float]:
        acc.append(float(x)); return acc
    def merge_accumulators(self, accs: Iterable[List[float]]) -> List[float]:
        out: List[float] = []
        for a in accs: out.extend(a)
        return out
    def extract_output(self, acc: List[float]) -> float:
        if not acc: return 0.0
        acc.sort()
        k = int(round((self.pct/100) * (len(acc)-1)))
        return acc[k]

def format_row(endpoint: str, hits: int, uniques: int, p95_ms: float, success_rate: float) -> str:
    return f"{endpoint},{hits},{uniques},{int(p95_ms)},{round(success_rate,4)}"

def run(input_path: str, output_csv: str, beam_args=None):
    options = PipelineOptions(beam_args or [])
    with beam.Pipeline(options=options) as p:
        recs = (
            p
            | "Read" >> beam.io.ReadFromText(input_path)
            | "Parse" >> beam.ParDo(ParseJson())
            | "FilterBots" >> beam.Filter(is_not_bot)
            | "Enrich" >> beam.Map(add_flags)
            | "Stoplist" >> beam.Filter(not_stopped)
        )

        hits     = recs | "KV_hits"    >> beam.Map(to_hit)     | "SumHits"     >> beam.CombinePerKey(sum)
        uniques  = recs | "KV_users"   >> beam.Map(to_user)    | "UniqueUsers" >> beam.CombinePerKey(UniqueUsersCombineFn())
        p95      = recs | "KV_latency" >> beam.Map(to_latency) | "P95Latency"  >> beam.CombinePerKey(PercentileCombineFn(95))
        succ     = recs | "KV_succ"    >> beam.Map(to_success) | "SumSuccess"  >> beam.CombinePerKey(sum)

        merged = ({'hits': hits, 'uniques': uniques, 'p95': p95, 'succ': succ}
                  | "Join" >> beam.CoGroupByKey())

        rows = (
            merged
            | "Compute" >> beam.Map(
                lambda kv: (
                    kv[0],
                    kv[1]['hits'][0] if kv[1]['hits'] else 0,
                    kv[1]['uniques'][0] if kv[1]['uniques'] else 0,
                    kv[1]['p95'][0] if kv[1]['p95'] else 0.0,
                    (kv[1]['succ'][0] / kv[1]['hits'][0])
                    if (kv[1]['hits'] and kv[1]['hits'][0] > 0 and kv[1]['succ'])
                    else 0.0
                )
            )
        )

        # Global sort by hits (note: global sorts require materializing all rows)
        sorted_rows = (
            rows
            | "ToList" >> beam.combiners.ToList()
            | "SortDesc" >> beam.Map(lambda lst: sorted(lst, key=lambda x: x[1], reverse=True))
            | "Flatten" >> beam.FlatMap(lambda lst: lst)
            | "FormatCSV" >> beam.Map(lambda t: format_row(*t))
        )

        header = p | "Header" >> beam.Create(
            ["endpoint,total_hits,unique_users,p95_latency_ms,success_rate"]
        )
        output = (header, sorted_rows) | "Concat" >> beam.Flatten()

        _ = output | "WriteCSV" >> beam.io.WriteToText(
            output_csv, file_name_suffix=".csv", shard_name_template=""
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_logs.jsonl")
    parser.add_argument("--output_csv", default="out/step7_sorted.csv")
    args, beam_args = parser.parse_known_args()
    run(args.input, args.output_csv, beam_args=beam_args)
