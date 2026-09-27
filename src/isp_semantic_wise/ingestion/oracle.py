"""
Oracle Connector - Extracts stored procedures, views, tables, and dependencies
"""

import re
import cx_Oracle
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from .base import BaseIngestionConnector, IngestionResult


class OracleConnector(BaseIngestionConnector):
    """Connector for Oracle database schema and code"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 1521)
        self.service_name = config.get("service_name", "ORCL")
        self.user = config.get("user", "schema_user")
        self.password = config.get("password", "password")
        self.schema = config.get("schema", "POST_TRADE")
        self.parse_sps = config.get("parse_stored_procedures", True)
        self.parse_views = config.get("parse_views", True)
        self.parse_tables = config.get("parse_tables", True)
        self.extract_deps = config.get("extract_dependencies", True)
        
        self.connection = None
        self.dsn = None
    
    def _connect(self):
        """Establish Oracle connection"""
        if self.connection is None:
            self.dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
            self.connection = cx_Oracle.connect(
                user=self.user,
                password=self.password,
                dsn=self.dsn,
            )
        return self.connection
    
    def discover(self) -> List[str]:
        """Discover Oracle objects to parse"""
        if not self._connect():
            return []
        
        cursor = self.connection.cursor()
        objects = []
        
        try:
            # Get stored procedures
            if self.parse_sps:
                cursor.execute("""
                    SELECT object_name, object_type
                    FROM all_objects
                    WHERE owner = :schema
                    AND object_type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY')
                    ORDER BY object_name
                """, schema=self.schema.upper())
                for row in cursor:
                    objects.append(f"procedure:{row[0]}")
            
            # Get views
            if self.parse_views:
                cursor.execute("""
                    SELECT view_name
                    FROM all_views
                    WHERE owner = :schema
                    ORDER BY view_name
                """, schema=self.schema.upper())
                for row in cursor:
                    objects.append(f"view:{row[0]}")
            
            # Get tables
            if self.parse_tables:
                cursor.execute("""
                    SELECT table_name
                    FROM all_tables
                    WHERE owner = :schema
                    ORDER BY table_name
                """, schema=self.schema.upper())
                for row in cursor:
                    objects.append(f"table:{row[0]}")
        
        finally:
            cursor.close()
        
        return objects
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract source code for Oracle object"""
        if not self._connect():
            return []
        
        obj_type, obj_name = source.split(":", 1)
        items = []
        
        try:
            cursor = self.connection.cursor()
            
            if obj_type == "procedure":
                items = self._extract_procedure(cursor, obj_name)
            elif obj_type == "view":
                items = self._extract_view(cursor, obj_name)
            elif obj_type == "table":
                items = self._extract_table(cursor, obj_name)
        
        finally:
            cursor.close()
        
        return items
    
    def _extract_procedure(self, cursor, name: str) -> List[Dict]:
        """Extract stored procedure source"""
        cursor.execute("""
            SELECT text
            FROM all_source
            WHERE owner = :schema
            AND name = :name
            AND type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY')
            ORDER BY line
        """, schema=self.schema.upper(), name=name.upper())
        
        source_lines = [row[0] for row in cursor]
        full_source = "".join(source_lines)
        
        return [{
            "artifact_type": "procedure",
            "name": name,
            "source_system": "oracle",
            "path": f"{self.schema}.{name}",
            "code_snippet": full_source,
            "metadata": {
                "schema": self.schema,
                "object_type": "PROCEDURE",
            },
        }]
    
    def _extract_view(self, cursor, name: str) -> List[Dict]:
        """Extract view definition"""
        cursor.execute("""
            SELECT text
            FROM all_views
            WHERE owner = :schema
            AND view_name = :name
        """, schema=self.schema.upper(), name=name.upper())
        
        row = cursor.fetchone()
        if row:
            view_text = row[0] if isinstance(row[0], str) else "".join(row[0])
            return [{
                "artifact_type": "view",
                "name": name,
                "source_system": "oracle",
                "path": f"{self.schema}.{name}",
                "code_snippet": view_text,
                "metadata": {"schema": self.schema},
            }]
        return []
    
    def _extract_table(self, cursor, name: str) -> List[Dict]:
        """Extract table definition with columns"""
        # Get column info
        cursor.execute("""
            SELECT column_name, data_type, data_length, data_precision, data_scale,
                   nullable, data_default, comments
            FROM all_tab_columns c
            LEFT JOIN all_col_comments cc ON c.owner = cc.owner 
                AND c.table_name = cc.table_name 
                AND c.column_name = cc.column_name
            WHERE c.owner = :schema
            AND c.table_name = :name
            ORDER BY c.column_id
        """, schema=self.schema.upper(), name=name.upper())
        
        columns = []
        for row in cursor:
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
        
        # Get table comment
        cursor.execute("""
            SELECT comments
            FROM all_tab_comments
            WHERE owner = :schema
            AND table_name = :name
        """, schema=self.schema.upper(), name=name.upper())
        
        table_comment = cursor.fetchone()
        
        return [{
            "artifact_type": "table",
            "name": name,
            "source_system": "oracle",
            "path": f"{self.schema}.{name}",
            "code_snippet": self._generate_ddl(name, columns),
            "metadata": {
                "schema": self.schema,
                "columns": columns,
                "comment": table_comment[0] if table_comment else None,
            },
        }]
    
    def _generate_ddl(self, table_name: str, columns: List[Dict]) -> str:
        """Generate CREATE TABLE DDL"""
        lines = [f"CREATE TABLE {self.schema}.{table_name} ("]
        for col in columns:
            col_def = f"  {col['name']} {col['data_type']}"
            if col['data_length'] and col['data_type'] in ('VARCHAR2', 'CHAR', 'NVARCHAR2'):
                data_type = col['data_type']
            elif col['data_precision']:
                data_type = f"{col['data_type']}({col['data_precision']},{col['data_scale'] or 0})"
            else:
                data_type = col['data_type']
            col_def = f"  {col['name']} {data_type}"
            if not col['nullable']:
                col_def += " NOT NULL"
            if col['default']:
                col_def += f" DEFAULT {col['default']}"
            lines.append(col_def + ",")
        lines[-1] = lines[-1].rstrip(",")
        lines.append(");")
        return "\n".join(lines)
    
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw Oracle data to standard format"""
        # Already in standard format, just ensure consistency
        for item in raw_data:
            item.setdefault("source_system", "oracle")
            item.setdefault("metadata", {})
            item["metadata"]["schema"] = self.schema
        return raw_data
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to storage"""
        # TODO: Implement loading
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __del__(self):
        self.close()