import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from datetime import datetime
import random
import csv
import os

# ------------------------------------------------------------
# Helper: generate fake log events (simulating streaming)
# ------------------------------------------------------------
def generate_events(pipeline, num_events=20):
    """Emit fake API events as a bounded 'stream'."""
    return (
        pipeline
        | "GenerateIDs" >> beam.Create(range(num_events))
        | "MakeEvents" >> beam.Map(lambda i: {
            "ts": datetime.utcnow().isoformat(),
            "endpoint": random.choice(["/api/orders", "/api/cart"]),
            "latency_ms": random.randint(50, 300),
        })
    )

# ------------------------------------------------------------
# Compute average
# ------------------------------------------------------------
class AvgCombineFn(beam.CombineFn):
    """Compute average of numeric values."""
    def create_accumulator(self):
        return (0, 0)  # sum, count
    def add_input(self, acc, input):
        (s, c) = acc
        return s + input, c + 1
    def merge_accumulators(self, accs):
        total_sum = sum(s for s, _ in accs)
        total_count = sum(c for _, c in accs)
        return total_sum, total_count
    def extract_output(self, acc):
        (s, c) = acc
        return (s / c) if c else 0.0

# ------------------------------------------------------------
# Format output rows
# ------------------------------------------------------------
def format_window_result(kv, window=beam.DoFn.WindowParam):
    """Format output as CSV line with window start/end."""
    endpoint, metrics = kv
    hits = metrics["hits"][0] if metrics["hits"] else 0
    avg_latency = metrics["avg_latency"][0] if metrics["avg_latency"] else 0.0
    window_start = datetime.utcfromtimestamp(window.start.to_utc_datetime().timestamp()).strftime("%H:%M:%S")
    window_end = datetime.utcfromtimestamp(window.end.to_utc_datetime().timestamp()).strftime("%H:%M:%S")
    return f"{window_start},{window_end},{endpoint},{hits},{round(avg_latency,2)}"

# ------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------
def run(beam_args=None, out_csv="out/streaming_metrics.csv"):
    options = PipelineOptions(beam_args or [])
    options.view_as(StandardOptions).streaming = True

    os.makedirs("out", exist_ok=True)

    with beam.Pipeline(options=options) as p:
        # 1. generate events
        events = generate_events(p, num_events=30)

        # 2. add timestamps (for windowing)
        with_timestamps = events | "AddTimestamps" >> beam.Map(
            lambda e: beam.window.TimestampedValue(e, datetime.fromisoformat(e["ts"]).timestamp())
        )

        # 3. apply a sliding window (30 s window, slide every 10 s)
        windowed = with_timestamps | "WindowInto" >> beam.WindowInto(
            beam.window.SlidingWindows(size=30, period=10)
        )

        # 4. compute hits per endpoint
        hits = (
            windowed
            | "ToHitKV" >> beam.Map(lambda e: (e["endpoint"], 1))
            | "SumHits" >> beam.CombinePerKey(sum)
        )

        # 5. compute avg latency per endpoint
        avg_latency = (
            windowed
            | "ToLatencyKV" >> beam.Map(lambda e: (e["endpoint"], e["latency_ms"]))
            | "AvgLatency" >> beam.CombinePerKey(AvgCombineFn())
        )

        # 6. join metrics
        merged = (
            {'hits': hits, 'avg_latency': avg_latency}
            | "JoinMetrics" >> beam.CoGroupByKey()
        )

        # 7. format as CSV rows
        rows = merged | "FormatRows" >> beam.Map(format_window_result)

        # 8. write CSV file
        header = "window_start,window_end,endpoint,total_hits,avg_latency_ms\n"
        _ = (
            rows
            | "AddHeader" >> beam.FlatMap(lambda lines: [header] + list(lines))
            | "WriteCSV" >> beam.io.WriteToText(
                out_csv, file_name_suffix=".csv", shard_name_template=""
            )
        )

        # 9. also print to console
        _ = rows | "PrintResults" >> beam.Map(print)

if __name__ == "__main__":
    run()
