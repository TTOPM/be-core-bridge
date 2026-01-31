"""
BELEL DATABASE ACADEMY v2.0
World's most advanced sovereign AI training data pipeline
"""

from .core.mandate_engine import BelelMandateCore
from .pipelines.ingestion_pipeline import ingest_real_datasets
from .pipelines.processing_pipeline import process_with_mandate

__version__ = "2.0.0"
__all__ = ["BelelMandateCore", "ingest_real_datasets", "process_with_mandate"]
