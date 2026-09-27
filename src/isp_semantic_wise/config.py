"""
Configuration Management for ISPSemanticWise
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class VectorDBSettings(BaseSettings):
    provider: str = "chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "isp_semantic_chunks"
    persist_directory: str = "./data/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    batch_size: int = 100


class GraphDBSettings(BaseSettings):
    provider: str = "neo4j"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    networkx_graph_path: str = "./data/networkx/observability_graph.gpickle"
    sync_interval_seconds: int = 3600


class RelationalDBSettings(BaseSettings):
    provider: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database: str = "isp_semantic"
    user: str = "postgres"
    password: str = "password"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class ModelSettings(BaseSettings):
    config_file: str = "models.yaml"

    # Loaded from YAML
    tier_1_models: list = []
    tier_2_models: list = []
    routing_rules: dict = {}


class IngestionSettings(BaseSettings):
    # Ab Initio
    ab_initio_graph_path: str = "/data/ab_initio/graphs"
    ab_initio_xfr_path: str = "/data/ab_initio/xfrs"
    ab_initio_dml_path: str = "/data/ab_initio/dmls"

    # Oracle
    oracle_host: str = "localhost"
    oracle_port: int = 1521
    oracle_service_name: str = "ORCL"
    oracle_user: str = "schema_user"
    oracle_password: str = "password"
    oracle_schema: str = "POST_TRADE"

    # Unix
    unix_scripts_path: str = "/data/scripts"

    # Email
    email_enabled: bool = False
    email_source: str = "file"
    email_file_path: str = "./data/emails"

    # Jira
    jira_enabled: bool = False
    jira_url: str = ""
    jira_user: str = ""
    jira_api_token: str = ""
    jira_project_key: str = "PTM"

    # Confluence
    confluence_enabled: bool = False
    confluence_url: str = ""
    confluence_user: str = ""
    confluence_api_token: str = ""
    confluence_space_keys: list = []

    # NetworkX Sync
    networkx_sync_enabled: bool = True
    networkx_graph_path: str = "./data/networkx/observability_graph.gpickle"
    networkx_sync_interval_seconds: int = 3600


class ProcessingSettings(BaseSettings):
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    chunking_strategy: str = "semantic"
    code_chunk_size: int = 100
    code_chunk_overlap: int = 20
    doc_chunk_size: int = 500
    doc_chunk_overlap: int = 50


class ServiceSettings(BaseSettings):
    glossary_enabled: bool = True
    glossary_tier: str = "tier_2"
    nl2sql_enabled: bool = True
    nl2sql_tier: str = "tier_1"
    debugger_enabled: bool = True
    narrator_enabled: bool = True
    impact_enabled: bool = True


class APISettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    timeout: int = 60
    cors_origins: list = ["http://localhost:3000"]


class SecuritySettings(BaseSettings):
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


class FeatureFlags(BaseSettings):
    tier2_enabled: bool = True
    email_ingestion: bool = False
    jira_ingestion: bool = False
    ui_enabled: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ISPSemanticWise"
    version: str = "0.1.0"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    graph_db: GraphDBSettings = Field(default_factory=GraphDBSettings)
    relational_db: RelationalDBSettings = Field(default_factory=RelationalDBSettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    services: ServiceSettings = Field(default_factory=ServiceSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    def load_models_config(self) -> dict:
        """Load model routing config from YAML"""
        config_path = Path(self.models.config_file)
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def get_tier1_model(self) -> str:
        config = self.load_models_config()
        tier1 = config.get("tier_1", {})
        return tier1.get("default_model", "meta/llama-3.2-11b-vision-instruct")

    def get_tier2_model(self) -> str:
        config = self.load_models_config()
        tier2 = config.get("tier_2", {})
        return tier2.get("default_model", "nvidia/nemotron-3-super-120b-a12b")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Convenience function
def get_config() -> Settings:
    return get_settings()