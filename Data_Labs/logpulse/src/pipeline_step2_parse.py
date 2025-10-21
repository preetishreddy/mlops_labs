import json
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# A DoFn ("Do Function") is a custom station.
# Beam calls .process(line) for each element on the belt.
class ParseJson(beam.DoFn):
    def process(self, line: str):
        try:
            rec = json.loads(line)   # convert "line" (str) -> dict
            must = {"ts","user_id","endpoint","status","latency_ms","ua"}
            if must.issubset(rec.keys()):
                # yield = put an item back on the belt
                yield rec
            # if required keys missing, drop the line by yielding nothing
        except Exception:
            # bad JSON? just drop it silently
            return

def run(input_glob: str, output_prefix: str, beam_args=None):
    options = PipelineOptions(beam_args or [])

    # This 'with' block builds AND runs the pipeline using the DirectRunner (local).
    with beam.Pipeline(options=options) as p:
        records = (
            p
            # read file(s) => PCollection[str]
            | "ReadLines" >> beam.io.ReadFromText(input_glob)
            # apply our custom DoFn => PCollection[dict]
            | "ParseJson" >> beam.ParDo(ParseJson())
        )

        # sanity check: how many valid records made it through?
        count_valid = records | "CountValid" >> beam.combiners.Count.Globally()

        # map the int to a printable string
        out = count_valid | "Format" >> beam.Map(lambda n: f"valid_records,{n}")

        # write to a single non-sharded file for convenience
        _ = out | "Write" >> beam.io.WriteToText(
            output_prefix, file_name_suffix=".csv", shard_name_template=""
        )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_logs.jsonl")
    parser.add_argument("--output_prefix", default="out/step2_parsed")
    # important: let argparse read ONLY real CLI args (fixes the warning you saw)
    args, beam_args = parser.parse_known_args()
    run(args.input, args.output_prefix, beam_args=beam_args)
