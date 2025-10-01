from contextlib import contextmanager
@contextmanager
def span(name:str):
    # Stub for OTEL; integrate with actual tracer in prod.
    yield
