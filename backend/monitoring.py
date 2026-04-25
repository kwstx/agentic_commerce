import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

def setup_monitoring(app):
    # 1. Structured Logging
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s',
        timestamp=True
    )
    log_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO)

    # 2. OpenTelemetry Tracing
    resource = Resource(attributes={
        SERVICE_NAME: "agentic-commerce-backend"
    })
    
    provider = TracerProvider(resource=resource)
    
    # In production, use OTLPSpanExporter. For demo/dev, we use ConsoleSpanExporter as well.
    # processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
    # provider.add_span_processor(processor)
    
    # Fallback to console for visibility in logs
    console_processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(console_processor)
    
    trace.set_tracer_provider(provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

def get_tracer():
    return trace.get_tracer(__name__)
