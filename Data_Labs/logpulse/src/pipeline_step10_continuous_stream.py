# src/pipeline_step10_continuous_stream.py
import os
import time
import random
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

# ---------------------------
# Config knobs (easy to tweak)
# ---------------------------
EVENTS_PER_SECOND = 2          # emission rate
WINDOW_SIZE_SEC = 60           # sliding window size
WINDOW_PERIOD_SEC = 10         # slide every N seconds
OUTPUT_PREFIX = "out/stream/metrics"  # windowed CSVs go here

ENDPOINTS = ["/api/orders", "/api/cart", "/api/search"]


# ---------------------------
# Throttle to simulate a live feed
# ---------------------------
class ThrottleDoFn(beam.DoFn):
    """Sleeps a fixed time per element to limit emission rate."""
    def __init__(self, per_element_seconds: float):
        self.delay = per_element_seconds

    def process(self, x):
        time.sleep(self.delay)
        yield x


# ---------------------------
# Average combiner
# ---------------------------
class AvgCombineFn(beam.CombineFn):
    def create_accumulator(self):
        return (0.0, 0)  # sum, count

    def add_input(self, acc, value):
        s, c = acc
        return (s + float(value), c + 1)

    def merge_accumulators(self, accs):
        total_sum = sum(s for s, _ in accs)
        total_cnt = sum(c for _, c in accs)
        return (total_sum, total_cnt)

    def extract_output(self, acc):
        s, c = acc
        return (s / c) if c else 0.0


# ---------------------------
# Event generation
# ---------------------------
def generate_events(p, per_second: int = 1):
    """
    Use GenerateSequence to simulate an unbounded source.
    Each element becomes a fake API event. Throttled by a sleep DoFn.
    """
    delay_per_element = 1.0 / max(1, per_second)

    # GenerateSequence without an end = unbounded stream
    return (
        p
        | "GenSeq" >> beam.io.GenerateSequence(start=0)    # unbounded source
        | "Throttle" >> beam.ParDo(ThrottleDoFn(delay_per_element))
        | "MakeEvents" >> beam.Map(
            lambda i: {
                "ts": datetime.utcnow().isoformat(),
                "endpoint": random.choice(ENDPOINTS),
                "latency_ms": random.randint(50, 600),
            }
        )
    )


# ---------------------------
# Formatting helpers
# ---------------------------
def to_hit_kv(e):       return (e["endpoint"], 1)
def to_latency_kv(e):   return (e["endpoint"], int(e["latency_ms"]))

def format_row(kv, window=beam.DoFn.WindowParam):
    endpoint, metrics = kv
    hits = metrics["hits"][0] if metrics["hits"] else 0
    avg_latency = metrics["avg_latency"][0] if metrics["avg_latency"] else 0.0

    # window times for readability
    ws = window.start.to_utc_datetime()
    we = window.end.to_utc_datetime()
    window_start = ws.strftime("%Y-%m-%d %H:%M:%S")
    window_end   = we.strftime("%Y-%m-%d %H:%M:%S")

    return f"{window_start},{window_end},{endpoint},{hits},{round(avg_latency,2)}"


# ---------------------------
# Main pipeline
# ---------------------------
def run(beam_args=None):
    os.makedirs("out/stream", exist_ok=True)

    options = PipelineOptions(beam_args or [])
    options.view_as(StandardOptions).streaming = True  # mark as streaming

    with beam.Pipeline(options=options) as p:
        # 1) live-ish events (throttled)
        events = generate_events(p, per_second=EVENTS_PER_SECOND)

        # 2) add event-time timestamps for windowing
        with_ts = events | "AddTimestamps" >> beam.Map(
            lambda e: beam.window.TimestampedValue(
                e, datetime.fromisoformat(e["ts"]).timestamp()
            )
        )

        # 3) sliding windows (e.g., 60s size; advance every 10s)
        windowed = with_ts | "WindowInto" >> beam.WindowInto(
            beam.window.SlidingWindows(size=WINDOW_SIZE_SEC, period=WINDOW_PERIOD_SEC)
        )

        # 4) metrics per window x endpoint
        hits = (
            windowed
            | "ToHitKV" >> beam.Map(to_hit_kv)
            | "SumHits" >> beam.CombinePerKey(sum)
        )

        avg_latency = (
            windowed
            | "ToLatencyKV" >> beam.Map(to_latency_kv)
            | "AvgLatency" >> beam.CombinePerKey(AvgCombineFn())
        )

        merged = (
            {'hits': hits, 'avg_latency': avg_latency}
            | "JoinMetrics" >> beam.CoGroupByKey()
        )

        rows = merged | "FormatRows" >> beam.Map(format_row)

        # 5) write rolling CSV (no windowedWrites)
        # We’ll timestamp each filename ourselves
        def write_to_csv(line, prefix=OUTPUT_PREFIX):
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = f"{prefix}_{ts}.csv"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            header = "window_start,window_end,endpoint,total_hits,avg_latency_ms\n"
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write(header)
            with open(path, "a") as f:
                f.write(line + "\n")
            return line  # so Print still sees it

        _ = rows | "WriteCSVManual" >> beam.Map(write_to_csv)

        # 6) also print to console so you see live updates
        _ = rows | "PrintToConsole" >> beam.Map(print)


if __name__ == "__main__":
    run()
