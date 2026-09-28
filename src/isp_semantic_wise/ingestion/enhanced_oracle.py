"""
Enhanced Oracle Connector for Broadridge Trading Data & Reference Data
Handles multiple feed sources, reference data systems, and impact analysis via chaos document
"""
import re
import cx_Oracle
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from collections import defaultdict

from .base import BaseIngestionConnector, IngestionResult
from .oracle import OracleConnector


@dataclass
class FeedConfig:
    """Configuration for a data feed"""
    feed_name: str
    source_system: str  # e.g., 'BROADRIDGE', 'REF_DATA_1', 'REF_DATA_2'
    feed_type: str  # 'trading', 'reference', 'reference_enrichment'
    tables: List[str]
    schedule: str  # cron or frequency
    criticality: str  # 'critical', 'high', 'medium', 'low'
    downstream_systems: List[str] = field(default_factory=list)
    business_owner: str = ""
    sla_minutes: int = 60


@dataclass
class ChaosDocumentEntry:
    """Entry from chaos document - maps feed to downstream impacts"""
    feed_name: str
    downstream_systems: List[str]
    downstream_tables: List[str]
    downstream_reports: List[str]
    business_processes: List[str]
    criticality: str
    sla_minutes: int
    contact_team: str
    escalation_path: List[str]


class EnhancedOracleConnector(OracleConnector):
    """
    Enhanced Oracle Connector for Broadridge + Reference Data Feeds
    Integrates with chaos document for impact analysis
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Feed configurations
        self.feed_configs: Dict[str, FeedConfig] = {}
        self.chaos_document: Dict[str, ChaosDocumentEntry] = {}
        
        # Load feed configurations
        self._load_feed_configs(config.get("feed_configs", {}))
        self._load_chaos_document(config.get("chaos_document_path", ""))
        
        # Track feed status
        self.feed_status: Dict[str, Dict] = {}
    
    def _load_feed_configs(self, feed_configs: Dict):
        """Load feed configurations from config"""
        for feed_name, config in feed_configs.items():
            self.feed_configs[feed_name] = FeedConfig(
                feed_name=feed_name,
                source_system=config.get("source_system", "BROADRIDGE"),
                feed_type=config.get("feed_type", "trading"),
                tables=config.get("tables", []),
                schedule=config.get("schedule", "daily"),
                criticality=config.get("criticality", "high"),
                downstream_systems=config.get("downstream_systems", []),
                business_owner=config.get("business_owner", ""),
                sla_minutes=config.get("sla_minutes", 60)
            )
    
    def _load_chaos_document(self, chaos_doc_path: str):
        """Load chaos document mapping feeds to downstream impacts"""
        if not chaos_doc_path:
            logger.warning("No chaos document path provided")
            return
        
        path = Path(chaos_doc_path)
        if not path.exists():
            logger.warning(f"Chaos document not found at {chaos_doc_path}")
            return
        
        try:
            if path.suffix.lower() == '.json':
                with open(path) as f:
                    data = json.load(f)
            elif path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(path)
                data = df.to_dict('records')
            else:
                logger.warning(f"Unsupported chaos document format: {path.suffix}")
                return
            
            for entry in data:
                entry_obj = ChaosDocumentEntry(
                    feed_name=entry.get('feed_name', ''),
                    downstream_systems=entry.get('downstream_systems', []),
                    downstream_tables=entry.get('downstream_tables', []),
                    downstream_reports=entry.get('downstream_reports', []),
                    business_processes=entry.get('business_processes', []),
                    criticality=entry.get('criticality', 'high'),
                    sla_minutes=entry.get('sla_minutes', 60),
                    contact_team=entry.get('contact_team', ''),
                    escalation_path=entry.get('escalation_path', [])
                )
                self.chaos_document[entry_obj.feed_name] = entry_obj
            
            logger.info(f"Loaded chaos document with {len(self.chaos_document)} feed mappings")
        except Exception as e:
            logger.error(f"Failed to load chaos document: {e}")
    
    def discover(self) -> List[str]:
        """Discover all objects including feed-specific tables"""
        objects = super().discover()
        
        # Add feed-specific tables
        for feed_name, feed_config in self.feed_configs.items():
            for table in feed_config.tables:
                objects.append(f"feed_table:{feed_config.feed_type}:{table}")
        
        return objects
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract with feed-aware logic"""
        if source.startswith("feed_table:"):
            return self._extract_feed_table(source)
        return super().extract(source)
    
    def _extract_feed_table(self, source: str) -> List[Dict[str, Any]]:
        """Extract feed-specific table with business context"""
        # Parse: feed_table:feed_type:table_name
        parts = source.split(":", 2)
        if len(parts) != 3:
            return []
        
        _, feed_type, table_name = parts
        
        # Find feed config
        feed_config = None
        for feed_name, config in self.feed_configs.items():
            if config.feed_type == feed_type and table_name in config.tables:
                feed_config = self.feed_configs[feed_name]
                break
        
        if not self._connect():
            return []
        
        cursor = self.connection.cursor()
        items = []
        
        try:
            # Get table data with business context
            query = f"SELECT * FROM {self.schema}.{table_name} WHERE ROWNUM <= 1000"
            cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Get column metadata
            col_query = """
                SELECT column_name, data_type, data_length, data_precision, data_scale,
                       nullable, data_default, comments
                FROM all_tab_columns
                WHERE owner = :schema AND table_name = :table_name
                ORDER BY column_id
            """
            col_cursor = self.connection.cursor()
            col_cursor.execute("""
                SELECT column_name, data_type, data_length, data_precision, data_scale,
                       nullable, data_default, comments
                FROM all_tab_columns
                WHERE owner = :schema AND table_name = :table_name
                ORDER BY column_id
            """, schema=self.schema.upper(), table_name=table_name.upper())
            
            columns_meta = []
            for row in col_cursor:
                columns.append({
                    "name": row[0],
                    "data_type": row[1],
                    "data_length": row[2],
                    "data_precision": row[3],
                    "data_scale": row[4],
                    "nullable": row[5] == "Y",
                    "default": row[6],
                    "comment": row[7],
                })
            
            # Build business context
            feed_type_map = {
                'trading': 'Trading data feed from Broadridge',
                'reference': 'Reference data for enrichment',
                'reference_enrichment': 'Reference data for trade enrichment'
            }
            
            return [{
                "artifact_type": "feed_table",
                "name": table_name,
                "source_system": "oracle",
                "path": f"{self.schema}.{table_name}",
                "code_snippet": f"-- Feed table: {table_name}\n-- Feed type: {feed_type}\n-- Source: Broadridge/Reference\n-- Business context: {self._get_business_context(table_name)}",
                "metadata": {
                    "schema": self.schema,
                    "feed_type": feed_type,
                    "feed_name": getattr(self, '_current_feed', 'unknown'),
                    "columns": columns,
                    "row_count": len(rows),
                    "business_context": self._get_business_context(table_name),
                    "downstream_impact": self._get_downstream_impact(table_name),
                    "criticality": self._get_criticality(table_name),
                },
            }]
            
        except Exception as e:
            logger.error(f"Failed to extract feed table {table_name}: {e}")
            return []
        finally:
            cursor.close()
    
    def _get_business_context(self, table_name: str) -> str:
        """Get business context for a table"""
        contexts = {
            'TRADE_CORE': 'Core trade capture - core trade attributes',
            'TRADE_ENRICHED': 'Enriched trades with fees, settlement data',
            'RECON_RESULTS': 'Reconciliation results with break codes',
            'CONFIRMATIONS': 'Counterparty confirmations',
            'FEE_SCHEDULE': 'Fee schedules by counterparty',
            'SETTLEMENT_CALENDAR': 'Settlement date calendars',
            'COUNTERPARTY': 'Counterparty reference data',
            'FEE_SCHEDULE': 'Fee schedules by CP and product',
            'SETTLEMENT_INSTRUCTION': 'Settlement instructions (SSI)',
            'CORPORATE_ACTIONS': 'Corporate actions reference data',
        }
        return contexts.get(table_name.upper(), f"Reference/operational table: {table_name}")
    
    def _get_downstream_impact(self, table_name: str) -> Dict:
        """Get downstream impact from chaos document"""
        impacts = {
            "downstream_systems": [],
            "downstream_tables": [],
            "downstream_reports": [],
            "business_processes": [],
            "criticality": "medium",
            "sla_minutes": 60,
            "contact_team": "",
            "escalation_path": []
        }
        
        # Check chaos document for each feed
        for feed_name, chaos_entry in self.chaos_document.items():
            if table_name.upper() in [t.upper() for t in chaos_entry.downstream_tables]:
                impacts["downstream_systems"].extend(chaos_entry.downstream_systems)
                impacts["downstream_tables"].extend(chaos_entry.downstream_tables)
                impacts["downstream_reports"].extend(chaos_entry.downstream_reports)
                impacts["business_processes"].extend(chaos_entry.business_processes)
                if chaos_entry.criticality == "critical":
                    impacts["criticality"] = "critical"
                impacts["sla_minutes"] = min(impacts["sla_minutes"], chaos_entry.sla_minutes)
                impacts["contact_team"] = chaos_entry.contact_team
                impacts["escalation_path"] = chaos_entry.escalation_path
        
        # Deduplicate
        for key in ["downstream_systems", "downstream_tables", "downstream_reports", "business_processes", "escalation_path"]:
            impacts[key] = list(set(impacts[key]))
        
        return impacts
    
    def _get_criticality(self, table_name: str) -> str:
        """Get criticality from chaos document or feed config"""
        for feed_name, feed_config in self.feed_configs.items():
            if table_name in feed_config.tables:
                return feed_config.criticality
        
        for chaos_entry in self.chaos_document.values():
            if table_name.upper() in [t.upper() for t in chaos_entry.downstream_tables]:
                return chaos_entry.criticality
        
        return "medium"
    
    def get_feed_impact_analysis(self, feed_name: str) -> Dict:
        """Get comprehensive impact analysis for a feed failure"""
        if feed_name not in self.chaos_document:
            return {"error": f"No chaos document entry for feed: {feed_name}"}
        
        chaos_entry = self.chaos_document[feed_name]
        feed_config = self.feed_configs.get(feed_name)
        
        return {
            "feed_name": feed_name,
            "feed_type": feed_config.feed_type if feed_config else "unknown",
            "criticality": chaos_entry.criticality,
            "sla_minutes": chaos_entry.sla_minutes,
            "business_owner": feed_config.business_owner if feed_config else "",
            "contact_team": chaos_entry.contact_team,
            "escalation_path": chaos_entry.escalation_path,
            "impact": {
                "downstream_systems": chaos_entry.downstream_systems,
                "downstream_tables": chaos_entry.downstream_tables,
                "downstream_reports": chaos_entry.downstream_reports,
                "business_processes": chaos_entry.business_processes,
            },
            "recommended_actions": self._get_recommended_actions(chaos_entry),
            "sla_risk": "HIGH" if chaos_entry.criticality == "critical" else "MEDIUM"
        }
    
    def _get_recommended_actions(self, chaos_entry: ChaosDocumentEntry) -> List[str]:
        """Generate recommended actions based on chaos document"""
        actions = [
            f"Alert {chaos_entry.contact_team} immediately",
            f"Escalate per path: {' -> '.join(chaos_entry.escalation_path)}" if chaos_entry.escalation_path else "Follow standard escalation",
        ]
        
        if "trading" in chaos_entry.business_processes:
            actions.append("Verify trade capture and enrichment pipelines")
        if "reconciliation" in chaos_entry.business_processes:
            actions.append("Verify reconciliation runs and break resolution")
        if "settlement" in chaos_entry.business_processes:
            actions.append("Verify settlement instruction generation")
        
        return actions
    
    def get_all_feed_impacts(self) -> List[Dict]:
        """Get impact analysis for all feeds"""
        return [self.get_feed_impact_analysis(feed) for feed in self.chaos_document.keys()]


class FeedIngestionOrchestrator:
    """Orchestrates ingestion of multiple feeds with proper ordering and error handling"""
    
    def __init__(self, connector: EnhancedOracleConnector):
        self.connector = connector
        self.feed_order = []  # Order of feed ingestion
    
    def set_feed_order(self, feed_order: List[str]):
        """Set the order in which feeds should be ingested"""
        self.feed_order = feed_order
    
    def discover_all(self) -> Dict[str, List[str]]:
        """Discover all objects grouped by feed"""
        all_objects = self.connector.discover()
        by_feed = defaultdict(list)
        
        for obj in all_objects:
            if obj.startswith("feed_table:"):
                parts = obj.split(":")
                if len(parts) >= 3:
                    feed_type = parts[1]
                    for feed_name, config in self.connector.feed_configs.items():
                        if config.feed_type == feed_type:
                            by_feed[config.feed_name].append(obj)
                            break
            else:
                by_feed["system"].append(obj)
        
        return dict(by_feed)
    
    def run_ingestion(self, feed_names: List[str] = None) -> Dict[str, IngestionResult]:
        """Run ingestion for specified feeds (or all if None)"""
        feeds_to_process = feed_names or list(self.connector.feed_configs.keys())
        results = {}
        
        for feed_name in feeds_to_process:
            logger.info(f"Starting ingestion for feed: {feed_name}")
            
            feed_config = self.connector.feed_configs.get(feed_name)
            if not feed_config:
                logger.warning(f"Unknown feed: {feed_name}")
                continue
            
            feed_results = []
            for table in feed_config.tables:
                source = f"feed_table:{feed_config.feed_type}:{table_name}"
                extracted = self.connector.extract(source)
                transformed = self.connector.transform(extracted)
                result = self.connector.load(transformed)
                feed_results.append(result)
            
            results[feed_name] = IngestionResult(
                job_id=f"feed_{feed_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                success=all(r.success for r in feed_results),
                items=sum(len(r.items) for r in feed_results),
                metadata={"feed": feed_name, "tables": feed_config.tables}
            )
        
        return results


# Factory function for easy initialization
def create_enhanced_oracle_connector(config: Dict) -> EnhancedOracleConnector:
    """Factory function to create enhanced oracle connector with all configs"""
    return EnhancedOracleConnector(config)


# Example configuration structure for reference
EXAMPLE_CONFIG = {
    "host": "your-oracle-host",
    "port": 1521,
    "service_name": "ORCL",
    "user": "ISP_SEMANTIC_USER",
    "password": "${ORACLE_PASSWORD}",
    "schema": "ISP_SEMANTIC",
    "chaos_document_path": "./data/chaos_document.json",
    "feed_configs": {
        "broadridge_trades": {
            "source_system": "BROADRIDGE",
            "feed_type": "trading",
            "tables": ["TRADE_CORE", "TRADE_ENRICHED", "TRADE_RAW"],
            "schedule": "0 6 * * *",  # Daily 6 AM
            "criticality": "critical",
            "downstream_systems": ["RECON", "SETTLEMENT", "REPORTING"],
            "business_owner": "Trading Ops",
            "sla_minutes": 30
        },
        "ref_data_counterparty": {
            "source_system": "REF_DATA_1",
            "feed_type": "reference",
            "tables": ["COUNTERPARTY", "COUNTERPARTY_SSI", "COUNTERPARTY_FEES"],
            "schedule": "0 5 * * *",
            "criticality": "high",
            "downstream_systems": ["ENRICHMENT", "RECON", "SETTLEMENT"],
            "business_owner": "Reference Data Team",
            "sla_minutes": 60
        },
        "ref_data_fees": {
            "source_system": "REF_DATA_2",
            "feed_type": "reference_enrichment",
            "tables": ["FEE_SCHEDULE", "FEE_RULES", "FEE_EXCEPTIONS"],
            "schedule": "0 4 * * *",
            "criticality": "high",
            "downstream_systems": ["ENRICHMENT", "RECON", "FEE_CALC"],
            "business_owner": "Fee Management",
            "sla_minutes": 60
        },
        "ref_data_settlement": {
            "source_system": "REF_DATA_3",
            "feed_type": "reference",
            "tables": ["SETTLEMENT_CALENDAR", "SETTLEMENT_INSTRUCTION", "CURRENCY_PAIRS"],
            "schedule": "0 3 * * *",
            "criticality": "high",
            "downstream_systems": ["SETTLEMENT", "REPORTING"],
            "business_owner": "Settlement Team",
            "sla_minutes": 120
        },
    }
}