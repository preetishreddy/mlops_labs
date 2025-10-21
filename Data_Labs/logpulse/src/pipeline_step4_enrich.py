import json, re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

BOT_RE = re.compile(r"(bot|crawler|spider)", re.IGNORECASE)

class ParseJson(beam.DoFn):
    def process(self, line: str):
        try:
            rec = json.loads(line)
            must = {"ts","user_id","endpoint","status","latency_ms","ua"}
            if must.issubset(rec.keys()):
                yield rec
        except Exception:
            return  # skip bad json

def is_not_bot(rec: dict) -> bool:
    return not BOT_RE.search(rec.get("ua", ""))

def add_flags(rec: dict) -> dict:
    # copy to avoid mutating upstream elements
    r = dict(rec)
    r["is_success"] = 200 <= int(r["status"]) < 300
    r["endpoint_group"] = r["endpoint"].split("?")[0]
    return r

def run(input_path: str, output_prefix: str, beam_args=None):
    options = PipelineOptions(beam_args or [])

    with beam.Pipeline(options=options) as p:
        enriched = (
            p
            | "Read" >> beam.io.ReadFromText(input_path)
            | "Parse" >> beam.ParDo(ParseJson())
            | "FilterBots" >> beam.Filter(is_not_bot)
            | "Enrich" >> beam.Map(add_flags)
        )

        # show a few rows so you can visually confirm enrichment worked
        sample = (
            enriched
            | "Pick3" >> beam.combiners.Sample.FixedSizeGlobally(3)
            | "ToStr" >> beam.FlatMap(lambda rows: [str(r) for r in rows])
        )

        _ = sample | "Write" >> beam.io.WriteToText(
            output_prefix, file_name_suffix=".txt", shard_name_template=""
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_logs.jsonl")
    parser.add_argument("--output_prefix", default="out/step4_enrich")
    args, beam_args = parser.parse_known_args()
    run(args.input, args.output_prefix, beam_args=beam_args)
