# 12. IMPLEMENTATION ROADMAP & NEXT STEPS

## 12.1 Implementation Phases

| Phase | Timeline | Focus | Deliverables |
|-------|----------|-------|--------------|
| **Phase 1: Foundation** | Weeks 1-4 | Core infrastructure, Oracle connector, NetworkX sync | Working ingestion, basic GraphQL API |
| **Phase 2: Core Services** | Weeks 5-10 | NL2SQL, Glossary, Debugger, Narrator, Impact | Functional semantic services |
| **Phase 3: Integration** | Weeks 11-14 | Batch Monitor → Semantic API, GraphQL UI | End-to-end working system |
| **Phase 4: Migration** | Weeks 15-20 | PySpark connector, Transform checker, Reconciliation | Migration-ready |
| **Phase 5: Production** | Weeks 21-24 | Security, monitoring, docs, UAT | Production-ready system |

---

## 12.2 Phase 1: Foundation (Weeks 1-4)

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| **Week 1** | Project setup, Oracle connector, config | Running ingestion, Oracle schema deployed |
| **Week 2** | NetworkX ↔ Neo4j sync, GraphQL API | Working GraphQL API, NetworkX ↔ Neo4j sync |
| **Week 3** | Oracle connector (SP, tables, views), Ab Initio parser | Full Oracle + Ab Initio ingestion |
| **Week 4** | Vector store, embeddings, basic NL2SQL | End-to-end: ingestion → vector → NL2SQL |

**Exit Criteria**: 
- [ ] Oracle connector extracts SPs, tables, views
- [ ] Ab Initio connector parses .mp/.xfr/.dml
- [ ] NetworkX ↔ Neo4j sync every 5 min
- [ ] Basic NL2SQL works on sample schema

---

## 12.3 Phase 2: Core Services (Weeks 5-10)

| Week | Service | Key Features |
|------|---------|--------------|
| **5-6** | **Glossary Builder** | Auto-extract terms from code, LLM definitions, technical mappings |
| **7-8** | **NL2SQL Translator** | Tier 1 model, schema awareness, lineage trace |
| **9** | **Trade Match Debugger** | Lineage trace, mismatch detection, business action |
| **10** | **Narrator + Impact** | Tier 2 narratives, impact analysis, change analyzer |

**Exit Criteria**: All 6 services functional, unit tests >80%, integration tests passing

---

## 12.4 Phase 3: Integration (Weeks 11-14)

| Week | Focus | Deliverables |
|------|-------|--------------|
| **11** | Batch Monitor → Semantic API | `/explain`, `/debug`, `/impact` called on breaks |
| **12** | GraphQL UI | React + Cytoscape real-time graph, WebSocket updates |
| **13** | Email ingestion | Narrator processes email threads |
| **14** | End-to-end testing | Break detection → explanation → UI update |

---

## 12.4 Phase 4: Migration Acceleration (Weeks 15-20)

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| **15-16** | **PySpark Connector** | `PySparkConnector` implements `BaseIngestionConnector` |
| **17** | **Transform Checker** | Ab Initio .xfr ↔ PySpark DataFrame equivalence |
| **18** | **Reconciliation** | Side-by-side Ab Initio vs PySpark output comparison |
| **19** | **Glossary Continuity** | Business terms stable; only `source_system` tag changes |
| **20** | **Migration Dashboard** | Real-time parity tracking, drift alerts |

---

## 12.5 Phase 5: Production Hardening (Weeks 21-24)

| Week | Focus | Deliverables |
|------|-------|--------------|
| **21** | **Security** | RBAC, mTLS, Vault integration, audit logging |
| **22** | **Observability** | Prometheus metrics, Grafana dashboards, alerting |
| **23** | **Load Testing** | Locust scripts, 1000 concurrent users |
| **24** | **UAT + Docs** | Runbooks, API docs, runbooks, UAT sign-off |

---

## 12.5 Immediate Next Steps (This Week)

```bash
# 1. Fix build environment (THIS WEEK)
# 1.1 Install MSVC Build Tools
#    → Visual Studio Installer → "Desktop development with C++"

# 2. Upgrade tooling
uv pip install --upgrade setuptools wheel maturin

# 3. Retry install
uv pip install -e . --no-build-isolation

# 2. If pydantic-core fails:
uv pip install maturin
uv pip install -e . --no-build-isolation

# 3. Start Docker services (ChromaDB, Neo4j)
docker-compose -f infra/docker-compose.yml up -d

# 4. Initialize Oracle schema (run as DBA)
sqlplus sys/password@ORCL as sysdba @scripts/init_db.sql

# 5. Run tests
pytest tests/unit -v --cov=src --cov-report=html
```

---

## 13.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Latency (p99)** | < 2s (Tier 1), Async (Tier 2) | Prometheus histogram |
| **Ingestion Throughput** | > 1000 artifacts/min | Prometheus counter |
| **NL2SQL Accuracy** | > 90% on eval set | Ragas evaluation |
| **Break Detection → Explanation** | < 30s end-to-end | Distributed tracing |
| **Uptime** | 99.9% | Prometheus availability |
| **MTTR Reduction** | 60% vs baseline | Incident tracking |

---

## 13.3 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **MSVC build failures** | High | High | Install VS Build Tools; use `--no-build-isolation` |
| **cx-Oracle/oracledb issues** | Medium | High | Use `oracledb` (thin mode), test early |
| **cx_Oracle deprecation** | Low | Medium | Migrate to `oracledb` thin mode |
| **Tree-sitter grammar gaps** | Medium | Medium | Fallback regex parsers |
| **Model API rate limits** | Low | High | Implement retry/backoff, local Tier 1 fallback |
| **NetworkX memory at scale** | Low | Medium | Partition graph, use Neo4j for full graph |

---

## 13.5 Team Structure Recommendation

| Role | Responsibilities | FTE |
|------|------------------|-----|
| **Tech Lead** | Architecture, code review, stakeholder sync | 1.0 |
| **Backend Engineers** | Ingestion, services, API | 2-3 |
| **ML Engineer** | Embeddings, NL2SQL, Tier 2 prompts | 1.0 |
| **Frontend Engineer** | React + Cytoscape, GraphQL subscriptions | 1.0 |
| **DevOps** | CI/CD, Docker, K8s, monitoring | 0.5 |
| **SME (Part-time)** | Glossary validation, scenario validation | 0.5 |

---

*End of Document*

---

## Appendix: Key References

| Document | Location |
|----------|----------|
| Architecture Decision Records | `docs/adr/` |
| SME Interview Guide | `docs/sme/INTERVIEW_GUIDE.md` |
| Glossary Template | `docs/sme/GLOSSARY_TEMPLATE.yaml` |
| API Specification | `src/isp_semantic_wise/api/routes/` |
| Database Schema | `scripts/init_db.sql` |
| CI/CD Pipeline | `.github/workflows/ci-cd.yml` |
| Harness Pipeline | `infra/harness.yaml` |
| Docker Compose | `infra/docker-compose.yml` |
| Dockerfile | `infra/Dockerfile` |

---

*Document Version: 1.0*  
*Last Updated: 2026-09-28*  
*Status: Architecture Complete - Implementation In Progress*