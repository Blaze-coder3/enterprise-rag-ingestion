# Lightweight mock wrapper replacing Prometheus Client
# Keeps execution paths safe without needing prometheus-client dependency.

class DummyMetric:
    def __init__(self, *args, **kwargs):
        pass
        
    def labels(self, *args, **kwargs):
        return self
        
    def inc(self, *args, **kwargs):
        pass
        
    def dec(self, *args, **kwargs):
        pass
        
    def set(self, *args, **kwargs):
        pass
        
    def observe(self, *args, **kwargs):
        pass

# Mock all active Prometheus metrics used in the pipeline
docs_ingested_total = DummyMetric()
docs_processing = DummyMetric()
stage_duration_seconds = DummyMetric()
chunks_per_document = DummyMetric()
embedding_batch_duration = DummyMetric()
parse_quality_score = DummyMetric()
quality_gate_outcomes = DummyMetric()
parser_fallback_total = DummyMetric()
tenant_queue_depth = DummyMetric()
tenant_active_jobs = DummyMetric()
tenant_wait_seconds = DummyMetric()
query_latency_seconds = DummyMetric()
retrieval_results_count = DummyMetric()
