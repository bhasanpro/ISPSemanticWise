# ADR 002: Ab Initio First, PySpark Ready Architecture

## Status
Accepted

## Context
Current production ETL platform is Ab Initio. Migration to PySpark is planned but timeline uncertain. Semantic layer must work with current Ab Initio while being ready for PySpark migration.

## Decision
Design ingestion and parsing with platform-agnostic abstraction:

1. **Connector Interface**: `BaseIngestionConnector` with `AbInitioConnector`, `OracleConnector`, `UnixConnector`, etc.
2. **Parser Abstraction**: `CodeParser` interface with `PLSQLParser`, `PythonParser`, `BashParser`, `AbInitioParser`
3. **Unified Output**: All connectors emit standardized `TechnicalArtifact` objects
4. **Graph Enrichment**: NetworkX observability graph as backbone, enriched with ingested metadata

When PySpark migration happens:
- Add `PySparkConnector` implementing same interface
- Add `PythonParser` for PySpark code (already exists)
- Swap connector in pipeline config
- No changes to downstream services

## Consequences

### Positive
- **Zero-downtime migration**: Swap connectors without service changes
- **Parallel ingestion**: Can run both during transition
- **Testability**: Mock connectors for unit tests
- **Extensibility**: Easy to add new sources (dbt, Airflow, etc.)

### Negative
- **Abstraction overhead**: Extra layer for current single-source
- **Feature parity**: PySpark connector must match Ab Initio capabilities
- **Testing burden**: Need to test both paths

### Risks
- Ab Initio XML parsing complexity (binary .mp files)
- PySpark migration timeline uncertainty
- Schema drift between platforms

## Alternatives Considered
1. **Ab Initio only** - Blocks future migration, technical debt
2. **PySpark only** - Not production-ready, blocks current value
3. **Separate pipelines** - Duplicated logic, maintenance burden
4. **Wait for migration** - Delays semantic layer value delivery

## Related ADRs
- [ADR 003](003-networkx-as-graph-backbone.md) - NetworkX as shared backbone
- [ADR 005](005-tree-sitter-for-code-parsing.md) - Parser abstraction

## References
- Ab Initio SDK documentation (if available)
- PySpark AST parsing examples
- Connector interface in `src/isp_semantic_wise/ingestion/base.py`