import json, re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from typing import Iterable, Set, List, Tuple

BOT_RE = re.compile(r"(bot|crawler|spider)", re.IGNORECASE)

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
    def create_accumulator(self) -> Set[str]:
        return set()
    def add_input(self, acc: Set[str], user_id: str) -> Set[str]:
        acc.add(user_id); return acc
    def merge_accumulators(self, accs: Iterable[Set[str]]) -> Set[str]:
        out = set()
        for a in accs: out |= a
        return out
    def extract_output(self, acc: Set[str]) -> int:
        return len(acc)

class PercentileCombineFn(beam.CombineFn):
    def __init__(self, pct=95):
        self.pct = pct
    def create_accumulator(self) -> List[float]:
        return []
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

def run(input_path: str, output_prefix: str, beam_args=None):
    options = PipelineOptions(beam_args or [])

    with beam.Pipeline(options=options) as p:
        recs = (
            p
            | "Read" >> beam.io.ReadFromText(input_path)
            | "Parse" >> beam.ParDo(ParseJson())
            | "FilterBots" >> beam.Filter(is_not_bot)
            | "Enrich" >> beam.Map(add_flags)
        )

        hits     = recs | "KV_hits"     >> beam.Map(to_hit)     | "SumHits"     >> beam.CombinePerKey(sum)
        uniques  = recs | "KV_users"    >> beam.Map(to_user)    | "UniqueUsers" >> beam.CombinePerKey(UniqueUsersCombineFn())
        p95      = recs | "KV_latency"  >> beam.Map(to_latency) | "P95Latency"  >> beam.CombinePerKey(PercentileCombineFn(95))
        successes= recs | "KV_success"  >> beam.Map(to_success) | "SumSuccess"  >> beam.CombinePerKey(sum)

        # Join by endpoint key
        merged = ({'hits': hits, 'uniques': uniques, 'p95': p95, 'succ': successes}
                  | "JoinMetrics" >> beam.CoGroupByKey())

        # Compute final row string per endpoint
        rows = (
            merged
            | "ComputeFields" >> beam.Map(
                lambda kv: format_row(
                    endpoint=kv[0],
                    hits=(kv[1]['hits'][0] if kv[1]['hits'] else 0),
                    uniques=(kv[1]['uniques'][0] if kv[1]['uniques'] else 0),
                    p95_ms=(kv[1]['p95'][0] if kv[1]['p95'] else 0.0),
                    success_rate=(
                        (kv[1]['succ'][0] / kv[1]['hits'][0])
                        if (kv[1]['hits'] and kv[1]['hits'][0] > 0 and kv[1]['succ'])
                        else 0.0
                    )
                )
            )
        )

        header = p | "Header" >> beam.Create(
            ["endpoint,total_hits,unique_users,p95_latency_ms,success_rate"]
        )
        output = (header, rows) | "Concat" >> beam.Flatten()

        _ = output | "WriteCSV" >> beam.io.WriteToText(
            output_prefix, file_name_suffix=".csv", shard_name_template=""
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_logs.jsonl")
    parser.add_argument("--output_prefix", default="out/step5_metrics")
    args, beam_args = parser.parse_known_args()
    run(args.input, args.output_prefix, beam_args=beam_args)
