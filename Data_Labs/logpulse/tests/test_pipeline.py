import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

# Import the things we wrote in step-5
from src.pipeline_step5_metrics import (
    ParseJson, is_not_bot, add_flags,
    to_hit, to_user, to_latency, to_success,
    UniqueUsersCombineFn, PercentileCombineFn,
    format_row
)

# ---------- 1) Parse JSON: keep good rows, drop bad rows ----------
def test_parsejson_keeps_good_and_drops_bad():
    lines = [
        # good
        '{"ts":"2025-10-20T12:00:01Z","user_id":"u1","endpoint":"/api/orders","status":200,"latency_ms":120,"ua":"Mozilla"}',
        # missing a field (ua) -> should drop
        '{"ts":"2025-10-20T12:00:02Z","user_id":"u2","endpoint":"/api/orders","status":200,"latency_ms":180}',
        # malformed json -> should drop
        '{"ts":"2025-10-20T12:00:03Z","user_id":"u3","endpoint":"/api/cart"'
    ]
    with TestPipeline() as p:
        parsed = (p | beam.Create(lines) | beam.ParDo(ParseJson()))
        # Only the first one survives
        assert_that(parsed | "KeepUserIds" >> beam.Map(lambda r: r["user_id"]), equal_to(["u1"]))

# ---------- 2) Filter bots ----------
def test_filter_bots():
    recs = [
        {"ua": "Mozilla/5.0", "endpoint": "/e", "status": 200, "latency_ms": 1, "user_id": "u"},
        {"ua": "Googlebot",   "endpoint": "/e", "status": 200, "latency_ms": 1, "user_id": "u"},
        {"ua": "curl/8.2",    "endpoint": "/e", "status": 200, "latency_ms": 1, "user_id": "u"},
    ]
    with TestPipeline() as p:
        keep = (p | beam.Create(recs) | beam.Filter(is_not_bot))
        # Googlebot is dropped, 2 remain
        assert_that(keep | beam.Map(lambda r: r["ua"]), equal_to(["Mozilla/5.0", "curl/8.2"]))

# ---------- 3) Enrichment flags ----------
def test_add_flags():
    rec = {"endpoint": "/api/orders?id=1", "status": 201, "latency_ms": 50, "ua": "Mozilla", "user_id": "u1", "ts":"t"}
    with TestPipeline() as p:
        enriched = (p | beam.Create([rec]) | beam.Map(add_flags))
        def check(e):
            return e["is_success"] is True and e["endpoint_group"] == "/api/orders"
        assert_that(enriched | beam.Map(check), equal_to([True]))

# ---------- 4) CombinePerKey: hits / uniques / p95 / success ----------
def test_hits_sum_per_key():
    items = [{"endpoint_group":"/a"}, {"endpoint_group":"/a"}, {"endpoint_group":"/b"}]
    with TestPipeline() as p:
        hits = (p
                | beam.Create(items)
                | beam.Map(to_hit)
                | beam.CombinePerKey(sum))
        # order does not matter
        assert_that(hits, equal_to([("/a", 2), ("/b", 1)]))

def test_unique_users_per_key():
    items = [
        {"endpoint_group":"/a", "user_id":"u1"},
        {"endpoint_group":"/a", "user_id":"u1"},
        {"endpoint_group":"/a", "user_id":"u2"},
        {"endpoint_group":"/b", "user_id":"u9"},
    ]
    with TestPipeline() as p:
        uniques = (p
                   | beam.Create(items)
                   | beam.Map(to_user)
                   | beam.CombinePerKey(UniqueUsersCombineFn()))
        assert_that(uniques, equal_to([("/a", 2), ("/b", 1)]))

def test_p95_latency_per_key():
    items = [
        {"endpoint_group":"/a", "latency_ms":1},
        {"endpoint_group":"/a", "latency_ms":2},
        {"endpoint_group":"/a", "latency_ms":100},
    ]
    with TestPipeline() as p:
        p95 = (p
               | beam.Create(items)
               | beam.Map(to_latency)
               | beam.CombinePerKey(PercentileCombineFn(95)))
        # sorted [1,2,100] -> index round(0.95*(3-1))=round(1.9)=2 -> 100
        assert_that(p95, equal_to([("/a", 100.0)]))

def test_success_rate_row_formatting():
    # Build a merged KV output in the same shape our pipeline expects *before* format_row.
    endpoint = "/api/orders"
    hits = 3
    uniques = 2
    p95 = 210.0
    succ = 3
    row = format_row(endpoint, hits, uniques, p95, succ/hits)
    assert row == "/api/orders,3,2,210,1.0"

# ---------- 5) End-to-end mini (no write): two endpoints from in-memory lines ----------
def test_end_to_end_mini():
    lines = [
        # orders (two successes)
        '{"ts":"t1","user_id":"u1","endpoint":"/api/orders","status":200,"latency_ms":120,"ua":"Mozilla"}',
        '{"ts":"t2","user_id":"u2","endpoint":"/api/orders","status":200,"latency_ms":210,"ua":"Mozilla"}',
        # cart (one success)
        '{"ts":"t3","user_id":"u3","endpoint":"/api/cart","status":200,"latency_ms":60,"ua":"Mozilla"}',
        # bot (should be dropped)
        '{"ts":"t4","user_id":"u9","endpoint":"/api/cart","status":500,"latency_ms":950,"ua":"Googlebot"}'
    ]
    with TestPipeline() as p:
        recs = (p | beam.Create(lines) | beam.ParDo(ParseJson()) | beam.Filter(is_not_bot) | beam.Map(add_flags))

        hits     = recs | "H" >> beam.Map(to_hit)     | "HSum" >> beam.CombinePerKey(sum)
        uniques  = recs | "U" >> beam.Map(to_user)    | "USum" >> beam.CombinePerKey(UniqueUsersCombineFn())
        p95      = recs | "L" >> beam.Map(to_latency) | "LP95" >> beam.CombinePerKey(PercentileCombineFn(95))
        succ     = recs | "S" >> beam.Map(to_success) | "SSum" >> beam.CombinePerKey(sum)

        merged = ({'hits': hits, 'uniques': uniques, 'p95': p95, 'succ': succ}
                  | "Join" >> beam.CoGroupByKey())

        rows = (merged
                | "Compute" >> beam.Map(
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
                ))

        # Expect two endpoints; orders has 2 hits, 2 uniques, p95=210, success_rate=1.0
        # cart has 1 hit, 1 unique, p95=60, success_rate=1.0 (bot 500 was dropped)
        assert_that(rows, equal_to([
            "/api/orders,2,2,210,1.0",
            "/api/cart,1,1,60,1.0",
        ]))
