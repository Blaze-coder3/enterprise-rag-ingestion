from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI
from ..config import settings

def setup_tracing(app: FastAPI | None = None, service_name: str = "rag-pipeline") -> trace.Tracer:
    """Initialize OpenTelemetry with Jaeger OTLP exporter."""
    
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    if settings.jaeger_endpoint:
        # Note: Depending on your deployment, you might use http instead of grpc. 
        # Using insecure for local Jaeger container setup.
        exporter = OTLPSpanExporter(endpoint=f"http://{settings.jaeger_endpoint}", insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    
    trace.set_tracer_provider(provider)
    
    if app:
        FastAPIInstrumentor.instrument_app(app)
        
    return trace.get_tracer("rag_pipeline")

def get_tracer(name: str = "rag_pipeline") -> trace.Tracer:
    return trace.get_tracer(name)
