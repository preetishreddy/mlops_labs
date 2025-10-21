import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# This is the entry point for your Beam assembly line.
# - PipelineOptions holds command-line args for the runner (we'll use the local DirectRunner by default).
# - The "with beam.Pipeline(...)" block defines and RUNS the pipeline.

def run(input_glob: str, output_prefix: str, beam_args=None):
    beam_args = beam_args or []
    options = PipelineOptions(beam_args)

    # A "with" block ensures the pipeline is properly finalized/executed.
    with beam.Pipeline(options=options) as p:
        # 1) Read lines → PCollection[str]
        lines = p | "ReadLines" >> beam.io.ReadFromText(input_glob)

        # 2) Count how many lines → PCollection[int] with a single element (the count)
        line_count = lines | "CountLines" >> beam.combiners.Count.Globally()

        # 3) Format the single int into a string so we can write it
        out_text = line_count | "Format" >> beam.Map(lambda n: f"total_lines,{n}")

        # 4) Write to text files (Beam shards output to support parallelism)
        _ = out_text | "Write" >> beam.io.WriteToText(
            output_prefix, file_name_suffix=".csv"
        )

if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/*.jsonl")
    parser.add_argument("--output_prefix", default="out/step1_count")
    args, beam_args = parser.parse_known_args()

    run(args.input, args.output_prefix, beam_args=beam_args)
