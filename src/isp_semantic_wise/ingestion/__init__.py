"""
Ingestion Package - Source Connectors
"""

from .base import BaseIngestionConnector, IngestionJob, IngestionResult, IngestionStatus
from .ab_initio import AbInitioConnector
from .oracle import OracleConnector
from .unix import UnixConnector
from .email import EmailConnector
from .jira import JiraConnector
from .networkx_sync import NetworkXSyncConnector
from .enhanced_oracle import (
    EnhancedOracleConnector, 
    FeedConfig, 
    ChaosDocumentEntry, 
    FeedIngestionOrchestrator,
    create_enhanced_oracle_connector,
    EXAMPLE_CONFIG
)
from .pipeline import (
    IngestionPipeline, 
    PipelineConfig, 
    create_ingestion_pipeline
)

__all__ = [
    "BaseIngestionConnector",
    "IngestionJob",
    "IngestionResult",
    "IngestionStatus",
    "AbInitioConnector",
    "OracleConnector",
    "UnixConnector",
    "EmailConnector",
    "JiraConnector",
    "NetworkXSyncConnector",
    "EnhancedOracleConnector",
    "FeedConfig",
    "ChaosDocumentEntry",
    "FeedIngestionOrchestrator",
    "create_enhanced_oracle_connector",
    "EXAMPLE_CONFIG",
    "IngestionPipeline",
    "PipelineConfig",
    "create_ingestion_pipeline",
]