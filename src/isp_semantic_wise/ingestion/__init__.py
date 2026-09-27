"""
Ingestion Package - Source Connectors
"""

from .base import BaseIngestionConnector, IngestionJob, IngestionResult
from .ab_initio import AbInitioConnector
from .oracle import OracleConnector
from .unix import UnixConnector
from .email import EmailConnector
from .jira import JiraConnector
from .networkx_sync import NetworkXSyncConnector

__all__ = [
    "BaseIngestionConnector",
    "IngestionJob",
    "IngestionResult",
    "AbInitioConnector",
    "OracleConnector",
    "UnixConnector",
    "EmailConnector",
    "JiraConnector",
    "NetworkXSyncConnector",
]