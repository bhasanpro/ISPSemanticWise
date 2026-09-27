"""
Relational Store - Oracle abstraction for metadata
"""

from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from loguru import logger

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from ..config import get_settings


class RelationalStore:
    """Oracle relational store for metadata"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
    
    def initialize(self):
        """Initialize database connection"""
        db_config = self.settings.relational_db
        
        # Oracle connection string
        dsn = f"oracle+cx_oracle://{db_config.user}:{db_config.password}@"
        dsn += f"{db_config.host}:{db_config.port}/?service_name={db_config.service_name}"
        
        self.engine = create_engine(
            dsn,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_pre_ping=True,
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        
        logger.info("Relational store (Oracle) initialized")
    
    @asynccontextmanager
    async def get_session(self) -> Session:
        """Get database session"""
        session = self.SessionLocal()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_session_sync(self) -> Session:
        """Get synchronous session"""
        return self.SessionLocal()
    
    def execute(self, query: str, params: Dict = None) -> List[Dict]:
        """Execute raw SQL query"""
        session = self.SessionLocal()
        try:
            result = session.execute(text(query), params or {})
            if result.returns_rows:
                return [dict(row._mapping) for row in result]
            return []
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
        finally:
            session.close()
    
    def execute_many(self, query: str, params_list: List[Dict]) -> int:
        """Execute bulk insert/update"""
        session = self.SessionLocal()
        try:
            result = session.execute(text(query), params_list)
            session.commit()
            return result.rowcount
        except Exception as e:
            session.rollback()
            logger.error(f"Batch execute failed: {e}")
            raise
        finally:
            session.close()
    
    # ==========================================
    # BUSINESS TERMS
    # ==========================================
    
    def upsert_business_term(self, term: Dict) -> str:
        """Upsert business term - Oracle MERGE syntax"""
        query = """
            MERGE INTO business_terms bt
            USING (SELECT :term as term FROM dual) src
            ON (bt.term = src.term)
            WHEN MATCHED THEN
                UPDATE SET
                    synonyms = :synonyms,
                    definition = :definition,
                    category = :category,
                    confidence_score = :confidence_score,
                    source_system = :source_system,
                    updated_at = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (id, term, synonyms, definition, category, confidence_score, source_system)
                VALUES (SYS_GUID(), :term, :synonyms, :definition, :category, :confidence_score, :source_system)
        """
        session = self.SessionLocal()
        try:
            session.execute(text(query), term)
            session.commit()
            
            # Get the ID
            result = session.execute(text("SELECT id FROM business_terms WHERE term = :term"), {"term": term["term"]})
            row = result.fetchone()
            return str(row[0]) if row else None
        finally:
            session.close()
    
    def get_business_term(self, term: str) -> Optional[Dict]:
        """Get business term by name"""
        return self.execute(
            "SELECT * FROM business_terms WHERE term = :term",
            {"term": term}
        )
    
    def search_business_terms(self, query: str, category: str = None, limit: int = 20) -> List[Dict]:
        """Search business terms - Oracle uses UPPER for case-insensitive"""
        sql = "SELECT * FROM business_terms WHERE UPPER(term) LIKE UPPER(:query)"
        params = {"query": f"%{query}%"}
        
        if category:
            sql += " AND category = :category"
            params["category"] = category
        
        sql += " ORDER BY confidence_score DESC"
        params["limit"] = limit
        sql += " FETCH FIRST :limit ROWS ONLY"
        
        return self.execute(sql, params)
    
    def upsert_term_mapping(self, mapping: Dict) -> str:
        """Upsert business-technical mapping"""
        query = """
            MERGE INTO business_technical_mappings btm
            USING (SELECT :business_term_id as btid, :technical_artifact_id as taid FROM dual) src
            ON (btm.business_term_id = src.btid AND btm.technical_artifact_id = src.taid)
            WHEN MATCHED THEN
                UPDATE SET
                    mapping_type = :mapping_type,
                    confidence_score = :confidence_score,
                    transformation_logic = :transformation_logic,
                    business_rule = :business_rule
            WHEN NOT MATCHED THEN
                INSERT (id, business_term_id, technical_artifact_id, mapping_type, confidence_score, transformation_logic, business_rule)
                VALUES (SYS_GUID(), :business_term_id, :technical_artifact_id, :mapping_type, :confidence_score, :transformation_logic, :business_rule)
        """
        session = self.SessionLocal()
        try:
            session.execute(text(query), mapping)
            session.commit()
            
            result = session.execute(text(
                "SELECT id FROM business_technical_mappings WHERE business_term_id = :btid AND technical_artifact_id = :taid"
            ), {"btid": mapping["business_term_id"], "taid": mapping["technical_artifact_id"]})
            row = result.fetchone()
            return str(row[0]) if row else None
        finally:
            session.close()
    
    def get_term_mappings(self, term_id: str) -> List[Dict]:
        """Get technical mappings for a business term"""
        return self.execute(
            """
            SELECT btm.*, ta.name as artifact_name, ta.artifact_type, ta.source_system, ta.path
            FROM business_technical_mappings btm
            JOIN technical_artifacts ta ON btm.technical_artifact_id = ta.id
            WHERE btm.business_term_id = :term_id
            ORDER BY btm.confidence_score DESC
            """,
            {"term_id": term_id}
        )
    
    # ==========================================
    # TECHNICAL ARTIFACTS
    # ==========================================
    
    def upsert_technical_artifact(self, artifact: Dict) -> str:
        """Upsert technical artifact"""
        query = """
            MERGE INTO technical_artifacts ta
            USING (SELECT :source_system as src_sys, :path as pth FROM dual) src
            ON (ta.source_system = src.src_sys AND ta.path = src.pth)
            WHEN MATCHED THEN
                UPDATE SET
                    artifact_type = :artifact_type,
                    name = :name,
                    code_snippet = :code_snippet,
                    metadata = :metadata,
                    updated_at = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (id, artifact_type, name, source_system, path, code_snippet, metadata)
                VALUES (SYS_GUID(), :artifact_type, :name, :source_system, :path, :code_snippet, :metadata)
        """
        session = self.SessionLocal()
        try:
            session.execute(text(query), artifact)
            session.commit()
            
            result = session.execute(text(
                "SELECT id FROM technical_artifacts WHERE source_system = :src_sys AND path = :pth"
            ), {"src_sys": artifact["source_system"], "pth": artifact["path"]})
            row = result.fetchone()
            return str(row[0]) if row else None
        finally:
            session.close()
    
    def get_technical_artifact(self, artifact_id: str) -> Optional[Dict]:
        return self.execute(
            "SELECT * FROM technical_artifacts WHERE id = :id",
            {"id": artifact_id}
        )
    
    def search_technical_artifacts(self, artifact_type: str = None, source_system: str = None, name: str = None, limit: int = 50) -> List[Dict]:
        """Search technical artifacts"""
        sql = "SELECT * FROM technical_artifacts WHERE 1=1"
        params = {}
        
        if artifact_type:
            sql += " AND artifact_type = :artifact_type"
            params["artifact_type"] = artifact_type
        
        if source_system:
            sql += " AND source_system = :source_system"
            params["source_system"] = source_system
        
        if name:
            sql += " AND UPPER(name) LIKE UPPER(:name)"
            params["name"] = f"%{name}%"
        
        sql += " ORDER BY updated_at DESC"
        params["limit"] = limit
        sql += " FETCH FIRST :limit ROWS ONLY"
        
        return self.execute(sql, params)
    
    # ==========================================
    # TRANSFORMATIONS (LINEAGE)
    # ==========================================
    
    def upsert_transformation(self, transform: Dict) -> str:
        """Upsert transformation"""
        query = """
            MERGE INTO transformations t
            USING (SELECT :source_artifact_id as said, :target_artifact_id as taid FROM dual) src
            ON (t.source_artifact_id = src.said AND t.target_artifact_id = src.taid)
            WHEN MATCHED THEN
                UPDATE SET
                    transformation_logic = :transformation_logic,
                    code_reference = :code_reference,
                    business_rule = :business_rule
            WHEN NOT MATCHED THEN
                INSERT (id, source_artifact_id, target_artifact_id, transformation_logic, code_reference, business_rule, source_system)
                VALUES (SYS_GUID(), :source_artifact_id, :target_artifact_id, :transformation_logic, :code_reference, :business_rule, :source_system)
        """
        session = self.SessionLocal()
        try:
            session.execute(text(query), transform)
            session.commit()
            
            result = session.execute(text(
                "SELECT id FROM transformations WHERE source_artifact_id = :said AND target_artifact_id = :taid"
            ), {"said": transform["source_artifact_id"], "taid": transform["target_artifact_id"]})
            row = result.fetchone()
            return str(row[0]) if row else None
        finally:
            session.close()
    
    def get_transformations(self, source_id: str = None, target_id: str = None) -> List[Dict]:
        """Get transformations"""
        sql = "SELECT * FROM transformations WHERE 1=1"
        params = {}
        
        if source_id:
            sql += " AND source_artifact_id = :source_id"
            params["source_id"] = source_id
        
        if target_id:
            sql += " AND target_artifact_id = :target_id"
            params["target_id"] = target_id
        
        return self.execute(sql, params)
    
    # ==========================================
    # INGESTION JOBS
    # ==========================================
    
    def create_ingestion_job(self, job: Dict) -> str:
        """Create ingestion job record"""
        query = """
            INSERT INTO ingestion_jobs (id, job_type, source_path, status)
            VALUES (SYS_GUID(), :job_type, :source_path, :status)
        """
        session = self.SessionLocal()
        try:
            session.execute(text(query), job)
            session.commit()
            
            result = session.execute(text(
                "SELECT id FROM ingestion_jobs WHERE job_type = :jt AND source_path = :sp AND status = :st AND ROWNUM = 1 ORDER BY started_at DESC"
            ), {"jt": job["job_type"], "sp": job["source_path"], "st": job["status"]})
            row = result.fetchone()
            return str(row[0]) if row else None
        finally:
            session.close()
    
    def update_ingestion_job(self, job_id: str, updates: Dict):
        """Update ingestion job"""
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        query = f"UPDATE ingestion_jobs SET {set_clause} WHERE id = :id"
        updates["id"] = job_id
        self.execute(query, updates)
    
    def get_ingestion_jobs(self, status: str = None, job_type: str = None, limit: int = 50) -> List[Dict]:
        """Get ingestion jobs"""
        sql = "SELECT * FROM ingestion_jobs WHERE 1=1"
        params = {}
        
        if status:
            sql += " AND status = :status"
            params["status"] = status
        
        if job_type:
            sql += " AND job_type = :job_type"
            params["job_type"] = job_type
        
        sql += " ORDER BY started_at DESC FETCH FIRST :limit ROWS ONLY"
        params["limit"] = limit
        
        return self.execute(sql, params)
    
    # ==========================================
    # QUERY LOGS
    # ==========================================
    
    def log_query(self, log: Dict):
        """Log query for analytics"""
        query = """
            INSERT INTO query_logs (id, user_id, query_text, intent, tier_used, model_used, response_time_ms, sql_generated, success, error_message, feedback_score)
            VALUES (SYS_GUID(), :user_id, :query_text, :intent, :tier_used, :model_used, :response_time_ms, :sql_generated, :success, :error_message, :feedback_score)
        """
        self.execute(query, log)
    
    def get_query_analytics(self, days: int = 7) -> List[Dict]:
        """Get query analytics"""
        return self.execute("""
            SELECT 
                TRUNC(created_at) as date,
                tier_used,
                COUNT(*) as query_count,
                AVG(response_time_ms) as avg_response_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM query_logs
            WHERE created_at >= SYSDATE - :days
            GROUP BY TRUNC(created_at), tier_used
            ORDER BY date DESC
        """, {"days": days})
    
    # ==========================================
    # EVALUATION RESULTS
    # ==========================================
    
    def save_evaluation_result(self, result: Dict):
        """Save evaluation result"""
        query = """
            INSERT INTO evaluation_results (id, test_suite, tier, model_used, metric_name, metric_value, test_case_id, details)
            VALUES (SYS_GUID(), :test_suite, :tier, :model_used, :metric_name, :metric_value, :test_case_id, :details)
        """
        self.execute(query, result)
    
    def get_evaluation_results(self, test_suite: str = None, tier: str = None) -> List[Dict]:
        """Get evaluation results"""
        sql = "SELECT * FROM evaluation_results WHERE 1=1"
        params = {}
        
        if test_suite:
            sql += " AND test_suite = :test_suite"
            params["test_suite"] = test_suite
        
        if tier:
            sql += " AND tier = :tier"
            params["tier"] = tier
        
        sql += " ORDER BY evaluated_at DESC"
        return self.execute(sql, params)
    
    def close(self):
        """Close engine"""
        if self.engine:
            self.engine.dispose()