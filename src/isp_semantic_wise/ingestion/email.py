"""
Email Connector - Parses email threads for tribal knowledge
"""

import email
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
from email_reply_parser import EmailReplyParser

from .base import BaseIngestionConnector, IngestionResult


class EmailConnector(BaseIngestionConnector):
    """Connector for email threads"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.source = config.get("source", "file")  # file, exchange, imap
        self.file_path = Path(config.get("file_path", "./data/emails"))
        self.thread_reconstruction = config.get("thread_reconstruction", True)
    
    def discover(self) -> List[str]:
        """Discover email files"""
        if self.source == "file":
            return [str(f) for f in self.file_path.rglob("*.eml")]
        return []
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract email thread from .eml file"""
        path = Path(source)
        raw_content = path.read_bytes()
        
        try:
            msg = email.message_from_bytes(raw_content)
            thread = self._parse_thread(msg)
            
            return [{
                "artifact_type": "email_thread",
                "name": path.stem,
                "source_system": "email",
                "path": str(path.relative_to(self.file_path)),
                "code_snippet": "",
                "metadata": {
                    "file_path": str(path),
                    "thread": thread,
                    "subject": msg.get("Subject", ""),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "date": msg.get("Date", ""),
                    "message_id": msg.get("Message-ID", ""),
                },
            }]
        except Exception as e:
            logger.error(f"Failed to parse email {source}: {e}")
            return []
    
    def _parse_thread(self, msg) -> List[Dict]:
        """Parse email thread into structured format"""
        thread = []
        
        # Walk through multipart messages
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True)
                if body:
                    body = body.decode('utf-8', errors='ignore')
                    # Use EmailReplyParser to split thread
                    parsed = EmailReplyParser.parse_reply(body)
                    thread.append({
                        "content": parsed,
                        "content_type": "text/plain",
                    })
        
        return thread
    
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform emails to standard artifacts"""
        transformed = []
        
        for item in raw_data:
            thread = item["metadata"].get("thread", [])
            
            for i, message in enumerate(thread):
                content = message.get("content", "")
                if not content.strip():
                    continue
                
                # Extract entities from email content
                entities = self._extract_entities(content)
                
                transformed.append({
                    "artifact_type": "email_message",
                    "name": f"{item['name']}_msg_{i}",
                    "source_system": "email",
                    "path": f"{item['path']}/msg_{i}",
                    "code_snippet": content,
                    "metadata": {
                        "source_path": item["metadata"]["file_path"],
                        "subject": item["metadata"]["subject"],
                        "from": item["metadata"]["from"],
                        "date": item["metadata"]["date"],
                        "message_index": i,
                        "entities": entities,
                    },
                })
        
        return transformed
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract business entities from email content"""
        entities = {
            "trade_ids": [],
            "break_codes": [],
            "counterparties": [],
            "systems": [],
            "tables": [],
        }
        
        # Trade IDs
        trade_pattern = r'\b(TRD[_\-]?\d{8,}|TRADE[_\-]?\d+)\b'
        entities["trade_ids"] = re.findall(trade_pattern, content, re.IGNORECASE)
        
        # Break codes
        break_pattern = r'\b(SAMT|SDAT|CPID|TRDT|QTYM|PRCM|CURM|BRK[_\-]?\w+)\b'
        entities["break_codes"] = re.findall(break_pattern, content, re.IGNORECASE)
        
        # Counterparties
        cp_pattern = r'\b(GS|MS|JPM|CITI|BARC|DB|UBS|CS|BAML|HSBC)\b'
        entities["counterparties"] = re.findall(cp_pattern, content, re.IGNORECASE)
        
        # Systems
        sys_pattern = r'\b(Ab Initio|Oracle|Informatica|PySpark|Airflow|Control-M)\b'
        entities["systems"] = re.findall(sys_pattern, content, re.IGNORECASE)
        
        # Tables
        table_pattern = r'\b([A-Z_]{3,})\b'
        entities["tables"] = re.findall(table_pattern, content)
        
        return entities
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to storage"""
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )