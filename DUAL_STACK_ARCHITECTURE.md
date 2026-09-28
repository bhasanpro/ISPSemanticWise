# ISPBatchObservabilityWise + ISPSemanticWise — Dual Stack Architecture

## Executive Summary

This document proposes a **dual-stack architecture** combining two complementary systems:

| Stack | Status | Purpose |
|-------|--------|---------|
| **ISPBatchObservabilityWise** | Production-Ready | Real-time batch monitoring, break detection, and operational alerting across SIT/UAT/DEV/PROD |
| **ISPSemanticWise** | In Development | Semantic layer for natural language queries, root cause narratives, impact analysis, and Ab Initio → PySpark migration assistance |

**Integration Philosophy**: The batch monitor detects breaks and calls the semantic API (`/explain`, `/debug`, `/impact`) to enrich alerts with business narratives. Both share a **NetworkX graph backbone** (synced every 5 minutes) and **Oracle schema** for a single source of truth.

---

## 1. ISPBatchObservabilityWise — Production-Ready Batch Monitoring

### 1.1 Overview
Monitors AutoSys batch jobs across all environments (SIT/UAT/DEV/PROD) with intelligent break detection, automated RCA, and actionable notifications for support teams.

### 1.2 Six Core Improvements in Place

| # | Improvement | Description |
|---|-------------|-------------|
| **1** | **New Repo with Observability Layer** | Dedicated repository with NetworkX + Strawberry (GraphQL) observability layer |
| **2** | **4 Major Boxes (500+ JIL Files)** | Complete job definitions with playbooks and tie-break priorities for automated resolution |
| **3** | **Pattern-Based Lessons + Memory (hex-memory)** | Persistent pattern matching with lesson learning for recurring break types |
| **4** | **Observability Layer (NetworkX + GraphQL)** | Real-time graph of job dependencies, status, and data flow via GraphQL API |
| **5** | **JIL → NetworkX Pre-load at Batch Start** | Single Source of Truth: JIL definitions loaded into NetworkX graph before batch execution |
| **6** | **Email Insights + Blocker Handling** | Automated email analysis for failures, false lookback AC status, terminated/inactive jobs |

### 1.3 Agent Architecture (5 Agents)

| Agent | Role |
|-------|------|
| **Orchestrator** | Coordinates batch monitoring workflow, schedules, and state |
| **Fixer** | Executes automated remediation per playbook (rerun, dependency check, resource restart) |
| **Notifier** | Sends enriched alerts (email, Slack, Teams) with semantic context |
| **DB-MCP** | Manages Oracle/PostgreSQL connections, query execution, schema introspection |
| **Coordinator** | Cross-environment coordination, SLA tracking, escalation management |

### 1.4 Key Capabilities
- **Real-time dashboards** via GraphQL (Strawberry) showing job status, dependencies, SLA risk
- **Pattern matcher** learns from historical breaks → stores in hex-memory → feeds Semantic Glossary
- **Blocker taxonomy**: Failure, False Lookback AC, Terminated, Inactive — each with dedicated playbook
- **Multi-environment**: Single pane of glass for SIT/UAT/DEV/PROD

---

## 2. ISPSemanticWise — Semantic Layer (In Development)

### 2.1 Overview
Zero-agent, service-oriented semantic layer providing natural language access to post-trade data, code understanding, and migration assistance.

### 2.2 Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **No Agents** | Orchestrated services (not autonomous agents) |
| **Hybrid Model Routing** | Tier 1 (11B) for NL2SQL/Tools \| Tier 2 (120B+) for Reasoning |
| **Platform-Agnostic Ingestion** | Ab Initio first, PySpark-ready via connector abstraction |
| **Multi-Store Backend** | Neo4j (graph), ChromaDB (vectors), Oracle (relational), NetworkX (analysis) |

### 2.3 Tiered Model Strategy (ADR 001)

| Tier | Models | Use Cases | Latency | Cost |
|------|--------|-----------|---------|------|
| **Tier 1** | Llama-3.2-11B, Phi-3.5-mini | NL→SQL, tool calling, query routing, entity extraction, lineage traversal | < 2s | ~$0.0001/1K tokens |
| **Tier 2** | Nemotron-3-Super/Ultra, Llama-3.1-Nemotron-70B | Code understanding, glossary generation, root cause narratives, impact analysis | Async | ~$0.001-0.002/1K tokens |

**Routing**: Keyword-based with confidence scoring (ADR 007), service-level overrides, 90%+ queries on Tier 1.

### 2.4 Six Core Services

| Service | Tier | Purpose |
|---------|------|---------|
| **Glossary** | Tier 2 | Auto-generates business glossary from code, transforms, SME interviews |
| **NL2SQL** | Tier 1 | Natural language → SQL with lineage trace, validation, schema awareness |
| **Debugger** | Hybrid | Trade break debugging: lineage trace → mismatch points → root cause → business action |
| **Narrator** | Tier 2 | Generates executive-ready RCA narratives from break data |
| **Impact** | Tier 2 | Downstream impact analysis of proposed changes (schema, logic, schedule) |
| **Lineage** | Tier 1 | Cross-system lineage: Source → Ab Initio → Oracle → Recon → Report |

### 2.5 Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ISPSemanticWise                           │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│   Neo4j     │  ChromaDB   │   Oracle    │    NetworkX       │
│  (Graph)    │ (Vectors)   │ (Relational)│   (Analysis)      │
├─────────────┼─────────────┼─────────────┼───────────────────┤
│ Entities,   │ Semantic    │ Schema,     │ Observability     │
│ relations,  │ chunks,     │ metadata,   │ graph (shared     │
│ lineage     │ embeddings  │ glossary    │ with Batch Stack) │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

### 2.6 Ingestion Pipeline (Ab Initio First, PySpark Ready)

Per **ADR 002**: Connector interface (`BaseIngestionConnector`) with `AbInitioConnector`, `OracleConnector`, `UnixConnector`, `PySparkConnector` (future). All emit standardized `TechnicalArtifact` objects → NetworkX enrichment → downstream services unchanged during migration.

---

## 3. Integration — How They Work Together

### 3.1 Integration Points

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DUAL STACK INTEGRATION                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ISPBatchObservabilityWise                          ISPSemanticWise    │
│  ┌─────────────────────┐                        ┌─────────────────┐  │
│  │  Batch Monitor      │─── break detected ───▶│  /explain       │  │
│  │  (Orchestrator)     │                        │  /debug         │  │
│  │                     │◀─── enriched alert ───│  /impact        │  │
│  └─────────────────────┘                        └─────────────────┘  │
│         │                                              ▲              │
│         │              ┌───────────────────────────────┘              │
│         │              │                                              │
│         ▼              ▼                                              │
│  ┌─────────────────────────────────────────┐                         │
│  │         SHARED INFRASTRUCTURE            │                         │
│  │  ┌──────────────┐    ┌──────────────┐   │                         │
│  │  │   NetworkX   │◀───│    Oracle    │   │                         │
│  │  │  (Graph)     │    │   (Schema)   │   │                         │
│  │  │  Sync: 5 min │    │  Single      │   │                         │
│  │  └──────────────┘    │  Source of   │   │                         │
│  │                      │  Truth       │   │                         │
│  │  ┌──────────────┐    └──────────────┘   │                         │
│  │  │ Pattern      │                         │                         │
│  │  │ Matcher →    │                         │                         │
│  │  │ hex-memory → │                         │                         │
│  │  │ Semantic     │                         │                         │
│  │  │ Glossary     │                         │                         │
│  │  └──────────────┘                         │                         │
│  └─────────────────────────────────────────┘                         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow Details

| Flow | Description | Frequency |
|------|-------------|-----------|
| **Break → Semantic API** | Batch monitor calls `/debug` (lineage), `/explain` (narrative), `/impact` (risk) on break | On break detection |
| **NetworkX Sync** | Batch stack's observability graph synced to semantic Neo4j | Every 5 minutes |
| **Pattern → Glossary** | Batch pattern matcher learns → hex-memory → Semantic Glossary enrichment | Continuous |
| **Email → Narrator** | Support email threads ingested → Narrator generates RCA docs | On incident |

### 3.3 API Contract (Semantic Layer)

```yaml
# POST /api/v1/debugger/debug
{ "trade_id": "TRD_20240115_001", "break_code": "SAMT" }
→ { "lineage_trace": [...], "mismatch_points": [...], "root_cause": "...", "business_action": "..." }

# POST /api/v1/narrator/generate
{ "incident_id": "INC-12345", "break_data": {...}, "include_prevention": true }
→ { "narrative": "...", "root_cause": "...", "prevention_steps": [...] }

# POST /api/v1/impact/analyze
{ "change_type": "column", "artifact_path": "TRADE_CORE.SETT_AMT", "change_description": "Data type change DECIMAL(18,2) → DECIMAL(20,4)" }
→ { "affected_artifacts": [...], "risk_score": 0.75, "risk_level": "high", "recommendations": [...] }
```

---

## 4. High-Value Use Cases

### 4.1 Support Team (Operations) — Batch Monitoring + Business Explanations

| Scenario | Batch Stack Action | Semantic Stack Enrichment | Outcome |
|----------|-------------------|---------------------------|---------|
| **SAMT break on TRD_123** | Detects break, triggers Fixer playbook | Calls `/debug` → lineage trace shows fee applied in enrichment but not confirmation | Support sees: "Fee schedule (GS 0.05%) applied in SP_ENRICH_TRADE but counterparty confirmation excludes fee. Action: Confirm fee handling with GS ops." |
| **Job stuck in PROD** | Coordinator detects SLA breach, escalates | Calls `/impact` on downstream jobs → risk score, affected reports | "Job G_TRADE_ENRICH delayed 45 min. Impact: RECON_REPORT (high), FEE_CALC (medium). ETA: 15 min with rerun." |
| **Recurring SDAT breaks** | Pattern matcher identifies trend | Stores pattern in hex-memory → enriches Glossary with "SDAT: Settlement Date Mismatch — common causes: timezone, holiday calendar" | Next break auto-tagged with known causes, reduces MTTR by 60% |

### 4.2 Business Users — Natural Language Queries, RCA Documents

| Query | NL2SQL Translation | Lineage Provided |
|-------|-------------------|------------------|
| "Show all SAMT breaks for Goldman Sachs last week" | `SELECT * FROM RECON_RESULTS WHERE BREAK_CODE='SAMT' AND CP_CD='GS' AND RECON_DT >= CURRENT_DATE - 7` | TRADE_CORE → Ab Initio G_TRADE_ENRICH → SP_ENRICH_TRADE → RECON_RESULTS |
| "Why did trade TRD_456 break?" | N/A (uses `/debug`) | Full trace: Source SWIFT → Ab Initio transform → Oracle enrichment → Recon match → Break |
| "Generate RCA for INC-789" | N/A (uses `/narrator`) | Executive summary: "Settlement amount mismatch caused by fee schedule applied during enrichment but not reflected in counterparty confirmation. Root cause: Fee logic in SP_ENRICH_TRADE not synchronized with confirmation matching rules." |

### 4.3 Technical Teams — RCA Documents, Triage Calls, Impact Analysis

| Activity | Tool | Value |
|----------|------|-------|
| **Pre-deployment impact check** | `/impact` | "Changing FEE_SCHEDULE.FEE_PCT affects 12 downstream procedures, 3 reports, risk_score=0.82 (critical). Requires coordinated deployment." |
| **Triage call preparation** | `/debug` + `/narrator` | Auto-generates: timeline, divergence point, business action, similar historical breaks |
| **Cross-system lineage trace** | `/lineage` | "Column TRADE_CORE.SETT_AMT flows through: Ab Initio G_TRADE_ENRICH (CAST) → SP_ENRICH_TRADE (fee) → SP_RECON_MATCH (compare) → RECON_REPORT" |

### 4.4 Developers — Ab Initio → PySpark Migration, BAU Enhancements

| Task | Semantic Assistance |
|------|---------------------|
| **Ab Initio graph understanding** | Glossary generates: "G_TRADE_ENRICH: Enriches raw trades with fee schedules, settlement calendars, counterparty mappings. Input: SWIFT MT540. Output: Enriched trade records." |
| **Transform logic translation** | Debugger shows: `out.SETT_AMT :: CAST(REPLACE(in.SETT_RAW, ',', '') AS DECIMAL(18,2));` → PySpark equivalent: `df.withColumn('SETT_AMT', regexp_replace('SETT_RAW', ',', '').cast(DecimalType(18,2)))` |
| **Impact of migration changes** | `/impact` on proposed PySpark graph changes → identifies Oracle procedures, reports, downstream Ab Initio graphs affected |
| **BAU enhancement validation** | NL2SQL validates new reconciliation logic against production schema before deployment |

---

## 5. Semantic Layer for Ab Initio → PySpark Migration

### 5.1 Migration Challenge
- **Current**: 500+ Ab Initio graphs (.mp/.grf), 1000+ transforms (.xfr), complex DMLs
- **Target**: PySpark on Databricks/EMR with equivalent business logic
- **Risk**: Silent data drift, missed transformations, broken lineage

### 5.2 How Semantic Layer Accelerates Migration

| Phase | Semantic Service | Migration Value |
|-------|------------------|-----------------|
| **Discovery** | **Glossary + Ingestion** | Auto-inventories all graphs, transforms, DMLs → business glossary with 2000+ terms mapped to code |
| **Understanding** | **Debugger + Lineage** | For each graph: input/output ports, transform logic, downstream consumers, data quality rules |
| **Translation** | **NL2SQL + Glossary** | Tier 2 model generates PySpark equivalents for Ab Initio transforms with business context |
| **Validation** | **Impact + Debugger** | Compare Ab Initio vs PySpark output on sample data → mismatch detection at column level |
| **Cutover** | **Impact Analysis** | Risk-score every proposed cutover step: schema changes, schedule changes, consumer notifications |

### 5.3 Connector Abstraction (ADR 002) — Zero-Downtime Migration

```python
# Current: Ab Initio ingestion
connector = AbInitioConnector(config={"graph_path": "/data/ab_initio/graphs"})
artifacts = connector.discover() → extract() → transform() → load()

# Migration: Add PySpark connector, same interface
connector = PySparkConnector(config={"workspace": "/databricks/repos/pyspark"})
artifacts = connector.discover() → extract() → transform() → load()

# Downstream services (Glossary, NL2SQL, Debugger, Impact) UNCHANGED
# All consume standardized TechnicalArtifact objects
```

### 5.4 Migration-Specific Semantic Features

| Feature | Description |
|---------|-------------|
| **Side-by-side lineage** | NetworkX graph shows both Ab Initio and PySpark paths for same business flow |
| **Transform equivalence checker** | Compares Ab Initio `.xfr` logic vs PySpark DataFrame API → flags semantic differences |
| **Data reconciliation** | Debugger runs same trade through both pipelines → compares outputs at every stage |
| **Glossary continuity** | Business terms stay constant; only `source_system` tag changes from `ab_initio` to `pyspark` |
| **Rollback safety** | Impact analyzer scores rollback risk if PySpark introduces regressions |

### 5.5 Example: Ab Initio Transform → PySpark Translation

**Ab Initio (.xfr)**:
```abinitio
out.SETT_AMT :: CAST(REPLACE(in.SETT_RAW, ',', '') AS DECIMAL(18,2));
out.FEE_AMT :: ROUND(in.SETT_AMT * in.FEE_PCT, 2);
out.NET_SETT_AMT :: in.SETT_AMT + in.FEE_AMT;
```

**Semantic Glossary Entry** (Tier 2 generated):
```yaml
term: "Settlement Amount Enrichment"
business_definition: "Raw settlement amount from SWIFT parsed, fee calculated per counterparty schedule, net amount computed"
technical_artifacts:
  - system: "ab_initio"
    graph: "G_TRADE_ENRICH"
    transform: "XFR_SETTLEMENT_ENRICH"
    logic: "CAST(REPLACE(SETT_RAW, ',', '') AS DECIMAL(18,2)) → fee → net"
  - system: "pyspark"  # Post-migration
    job: "trade_enrichment_job"
    function: "enrich_settlement_amount"
    logic: "regexp_replace(SETT_RAW, ',', '').cast(DecimalType(18,2)) → fee → net"
```

**PySpark Translation** (Tier 2 + Tier 1 hybrid):
```python
def enrich_settlement_amount(df: DataFrame, fee_schedule: DataFrame) -> DataFrame:
    """Enriches raw trades with fee schedules per counterparty.
    
    Business Logic (from Glossary):
    - Parse SETT_RAW removing commas
    - Apply counterparty fee percentage from FEE_SCHEDULE
    - Compute NET_SETT_AMT = SETT_AMT + FEE_AMT
    """
    return (df
        .withColumn("SETT_AMT", regexp_replace("SETT_RAW", ",", "").cast(DecimalType(18,2)))
        .join(fee_schedule, "CP_CD", "left")
        .withColumn("FEE_AMT", round(col("SETT_AMT") * col("FEE_PCT"), 2))
        .withColumn("NET_SETT_AMT", col("SETT_AMT") + col("FEE_AMT"))
    )
```

---

## 6. Brainstorming Insights & Strategic Opportunities

### 6.1 Pattern Flywheel (Batch → Semantic → Batch)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS LEARNING LOOP                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Batch Break Detected                                           │
│       │                                                         │
│       ▼                                                         │
│  Pattern Matcher analyzes break signature                      │
│       │                                                         │
│       ▼                                                         │
│  hex-memory stores: {break_code, context, root_cause, fix}    │
│       │                                                         │
│       ▼                                                         │
│  Semantic Glossary enriched with new pattern                   │
│       │                                                         │
│       ▼                                                         │
│  Next break: Glossary provides instant context → faster MTTR  │
│       │                                                         │
│       ▼                                                         │
│  Narrator generates RCA doc → fed back to hex-memory           │
│       │                                                         │
│       └──────────────────┬────────────────────────────────────┘
│                          │
│                          ▼
│  Pattern confidence increases → auto-remediation enabled     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Strategic Differentiators

| Differentiator | Why It Matters |
|----------------|----------------|
| **Shared NetworkX Graph** | Single source of truth for both operational monitoring and semantic reasoning |
| **Tiered LLM Routing** | 10x cost savings vs single-model; right model for right task |
| **Ab Initio-First, PySpark-Ready** | Delivers value today, zero-throwaway for migration |
| **Pattern Memory (hex-memory)** | Institutional knowledge captured, not lost when experts leave |
| **Hybrid Services** | Debugger uses Tier 1 for lineage (fast) + Tier 2 for narrative (deep) |

### 6.3 Future Extensions

| Extension | Description | Effort |
|-----------|-------------|--------|
| **Auto-remediation** | Fixer agent executes semantic recommendations (e.g., "re-run with corrected fee schedule") | Medium |
| **Predictive break detection** | Train on hex-memory patterns → predict breaks before they happen | High |
| **SME chat interface** | Slack/Teams bot: "@semantic why did TRD_123 break?" → Narrator response | Low |
| **Migration dashboard** | Real-time Ab Initio vs PySpark parity tracking with drift alerts | Medium |
| **Regulatory audit trail** | Immutable RCA documents with lineage for SOX/BCBS239 compliance | Medium |

### 6.4 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tier 1 hallucination on complex code | Confidence threshold 0.7; fallback to Tier 2; human-in-loop for glossary validation |
| NetworkX sync lag (5 min) | Critical paths use direct Oracle queries; graph for analysis not real-time ops |
| Ab Initio .mp binary parsing | Use Ab Initio SDK export to XML; prioritize .xfr/.dml which are text |
| Model deprecation (NVIDIA API) | Abstract provider layer; config-driven model swap; evaluation suite catches regressions |

---

## 7. Target Audiences & Value Proposition

| Audience | Primary Stack | Key Value | Success Metrics |
|----------|---------------|-----------|-----------------|
| **Support Team (Ops)** | Batch + Semantic `/debug`, `/explain` | MTTR ↓ 60%, escalations ↓ 40%, zero "unknown cause" breaks | Mean time to acknowledge < 5 min; MTTR < 30 min |
| **Business Users** | Semantic `/nl2sql`, `/narrator` | Self-service answers, no SQL needed, audit-ready RCA docs | Query response < 10s; RCA doc generation < 2 min |
| **Technical Teams** | Semantic `/impact`, `/lineage` | Safe deployments, fast triage, cross-system visibility | Pre-deploy impact checks 100%; triage prep < 5 min |
| **Developers** | Semantic Glossary, Debugger, Impact | Migration velocity 3x, zero silent regressions, BAU confidence | Migration story points/sprint ↑ 200%; regression rate < 1% |

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4) ✅ **In Progress**
- [x] ISPSemanticWise repo, config, ADRs
- [x] Tiered model routing (Tier 1 + Tier 2 + Hybrid)
- [x] Ab Initio connector (graphs, transforms, DMLs)
- [x] NetworkX ↔ Neo4j sync infrastructure
- [ ] Oracle connector (procedures, views, tables)
- [ ] Vector store (ChromaDB) + embedding pipeline

### Phase 2: Core Services (Weeks 5-10)
- [ ] NL2SQL with lineage trace (Tier 1)
- [ ] Glossary generation (Tier 2)
- [ ] Trade Match Debugger (Hybrid)
- [ ] Impact Analyzer (Tier 2)
- [ ] Narrator RCA generation (Tier 2)

### Phase 3: Integration (Weeks 11-14)
- [ ] Batch Monitor → Semantic API integration
- [ ] Pattern Matcher → hex-memory → Glossary loop
- [ ] Email ingestion → Narrator enrichment
- [ ] Shared NetworkX graph validation

### Phase 4: Migration Acceleration (Weeks 15-20)
- [ ] PySpark connector implementation
- [ ] Transform equivalence checker
- [ ] Side-by-side reconciliation framework
- [ ] Migration dashboard

### Phase 5: Operational Excellence (Weeks 21+)
- [ ] Predictive break detection
- [ ] Auto-remediation playbooks
- [ ] SME chat interface
- [ ] Regulatory audit trail

---

## 9. Appendix: Key Configuration References

### 9.1 Model Routing (config/models.yaml)
- Tier 1: Llama-3.2-11B, Phi-3.5-mini (NL2SQL, tools, routing)
- Tier 2: Nemotron-3-Super/Ultra, Llama-3.1-Nemotron-70B (reasoning, generation)
- Hybrid: Debugger, Value Reconciler, Incident Narrator

### 9.2 Settings (config/settings.yaml)
- NetworkX sync: 300 seconds
- Neo4j: bolt://localhost:7687
- ChromaDB: ./data/chroma
- Oracle: ISP_SEMANTIC schema
- Feature flags: tier2_enabled, graph_visualization, export_enabled

### 9.3 API Endpoints
| Service | Endpoints |
|---------|-----------|
| Glossary | GET/POST /api/v1/glossary |
| NL2SQL | POST /api/v1/nl2sql/translate |
| Debugger | POST /api/v1/debugger/debug, POST /api/v1/debugger/analyze_break |
| Narrator | POST /api/v1/narrator/generate |
| Impact | POST /api/v1/impact/analyze |
| Lineage | GET /api/v1/lineage/{artifact_path} |
| Health | GET /api/v1/health |

---

*Document Version: 1.0*  
*Last Updated: 2026-09-28*  
*Status: For Review & Proposal*