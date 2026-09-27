"""
Base Ingestion Connector - Abstract Base Class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class IngestionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionJob:
    """Represents an ingestion job"""
    job_type: str
    source_path: str
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: IngestionStatus = IngestionStatus.PENDING
    items_processed: int = 0
    items_failed: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Result of an ingestion operation"""
    job_id: str
    success: bool
    items: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseIngestionConnector(ABC):
    """Abstract base class for all ingestion connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.job: Optional[IngestionJob] = None
    
    @abstractmethod
    def discover(self) -> List[str]:
        """Discover available source files/entities"""
        pass
    
    @abstractmethod
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract raw data from source"""
        pass
    
    @abstractmethod
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw data to standard format"""
        pass
    
    @abstractmethod
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load transformed data to storage"""
        pass
    
    def run(self, source: Optional[str] = None) -> IngestionResult:
        """Run full ingestion pipeline"""
        self.job = IngestionJob(
            job_type=self.__class__.__name__,
            source_path=source or self.config.get("source_path", ""),
            started_at=datetime.utcnow(),
            status=IngestionStatus.RUNNING,
        )
        
        try:
            sources = [source] if source else self.discover()
            all_items = []
            all_errors = []
            
            for src in sources:
                try:
                    raw = self.extract(src)
                    transformed = self.transform(raw)
                    result = self.load(transformed)
                    all_items.extend(result.items)
                    all_errors.extend(result.errors)
                    self.job.items_processed += len(result.items)
                    self.job.items_failed += len(result.errors)
                except Exception as e:
                    all_errors.append({"source": src, "error": str(e)})
                    self.job.items_failed += 1
            
            self.job.status = IngestionStatus.COMPLETED
            self.job.completed_at = datetime.utcnow()
            
            return IngestionResult(
                job_id=self.job.job_id,
                success=len(all_errors) == 0,
                items=all_items,
                errors=all_errors,
            )
        
        except Exception as e:
            self.job.status = IngestionStatus.FAILED
            self.job.error_message = str(e)
            self.job.completed_at = datetime.utcnow()
            raise
    
    def get_job_status(self) -> Optional[IngestionJob]:
        return self.job