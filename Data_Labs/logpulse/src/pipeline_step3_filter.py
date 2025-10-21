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
            return

def is_not_bot(rec: dict) -> bool:
    # True = keep it; False = drop it
    return not BOT_RE.search(rec.get("ua", ""))

def run(input_glob: str, output_prefix: str, beam_args=None):
    options = PipelineOptions(beam_args or [])

    with beam.Pipeline(options=options) as p:
        non_bots = (
            p
            | "Read" >> beam.io.ReadFromText(input_glob)
            | "Parse" >> beam.ParDo(ParseJson())
            | "FilterBots" >> beam.Filter(is_not_bot)  # keeps only non-bot rows
        )

        count_clean = non_bots | "Count" >> beam.combiners.Count.Globally()
        out = count_clean | "Fmt" >> beam.Map(lambda n: f"non_bot_records,{n}")

        _ = out | "Write" >> beam.io.WriteToText(
            output_prefix, file_name_suffix=".csv", shard_name_template=""
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_logs.jsonl")
    parser.add_argument("--output_prefix", default="out/step3_clean")
    args, beam_args = parser.parse_known_args()
    run(args.input, args.output_prefix, beam_args=beam_args)
