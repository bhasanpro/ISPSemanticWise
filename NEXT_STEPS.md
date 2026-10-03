# NEXT_STEPS.md - Prioritized Checklist for ISPSemanticWise

## 🚨 IMMEDIATE (Blockers - Do First)

### 1. Fix Build Environment (CRITICAL - Blocks Everything)
- [ ] **Install MSVC Build Tools** - Required for C-extensions on Windows
  - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  - Select: "Desktop development with C++" workload
  - Verify: `cl.exe` available in PATH
- [ ] **Upgrade setuptools** 
  ```bash
  uv pip install --upgrade setuptools wheel
  ```
- [ ] **Install maturin** (for pydantic-core)
  ```bash
  uv pip install maturin
  ```
- [ ] **Retry install**
  ```bash
  uv pip install -e . --no-build-isolation
  ```

### 2. Core Dependencies (Blocked on MSVC)
- [ ] `numpy` 1.26.4 - needs MSVC or Python 3.11/3.12
- [ ] `pydantic-core` - needs `maturin` (Rust)
- [ ] `pyyaml` 6.0.1 - needs MSVC
- [ ] `chroma-hnswlib` - needs MSVC

---

## 🟡 HIGH PRIORITY (After Build Works)

### 2. Infrastructure & Services
- [ ] **Start Docker Services**
  ```bash
  docker-compose -f infra/docker-compose.yml up -d
  ```
  - ChromaDB (port 8001)
  - Neo4j (port 7474/7687)
  - PostgreSQL (if used)
- [ ] **Oracle Connection** - Configure `config/.env` with real credentials
- [ ] **Initialize Oracle Schema**
  ```bash
  sqlplus sys/password@ORCL as sysdba @scripts/init_db.sql
  ```

### 3. Core Testing
- [ ] Unit tests: `pytest tests/unit -v`
- [ ] Integration tests: `pytest tests/integration -v`
- [ ] API health check: `curl http://localhost:8000/api/v1/health`
- [ ] Test each endpoint:
  - `GET /api/v1/health`
  - `POST /api/v1/nl2sql/generate`
  - `POST /api/v1/debugger/debug`
  - `POST /api/v1/narrator/narrate`
  - `POST /api/v1/impact/analyze`
  - `POST /api/v1/lineage/trace`

---

## 🟢 HIGH PRIORITY (Production Hardening)

### 4. Testing & Quality
- [ ] Unit tests: `pytest tests/unit -v --cov=src --cov-report=html`
- [ ] Integration tests: `pytest tests/integration -v`
- [ ] Contract tests: Schema validation for all APIs
- [ ] Load testing: `locust -f tests/load_test.py`
- [ ] Mutation testing: `mutmut run`
- [ ] Type checking: `mypy src/`
- [ ] Linting: `ruff check src/ && black --check src/ && isort --check-only src/`

### 5. Documentation
- [ ] **API Docs**: Auto-generate from OpenAPI (`/docs` endpoint)
- [ ] **Architecture Diagrams**: Mermaid diagrams in `docs/architecture/`
- [ ] **Runbooks**: `docs/runbooks/` for common operations
- [ ] **API Reference**: Auto-generated from FastAPI OpenAPI spec
- [ ] **SME Interview Guide**: `docs/sme/INTERVIEW_GUIDE.md` (exists)
- [ ] **Glossary Template**: `docs/sme/GLOSSARY_TEMPLATE.yaml` (exists)

### 6. Deployment & Infrastructure
- [ ] **K8s Manifests**: `infra/k8s/` - Deployments, Services, ConfigMaps, Secrets
- [ ] **Helm Charts**: `infra/helm/` with values for dev/staging/prod
- [ ] **Terraform**: `infra/terraform/` for cloud resources
- [ ] **Docker Images**: Multi-stage builds, distroless base, SBOM generation
- [ ] **GitHub Actions**: Validate CI/CD pipeline (`.github/workflows/ci-cd.yml`)
- [ ] **Harness Pipeline**: Validate `infra/harness.yaml` imports correctly

---

## 🔵 MEDIUM PRIORITY (Observability & Ops)

### 7. Monitoring & Observability
- [ ] **Prometheus Metrics**: `/metrics` endpoint with custom metrics
- [ ] **Grafana Dashboards**: `monitoring/grafana/dashboards/`
  - API latency (p50, p95, p99)
  - Error rates by endpoint
  - Queue depths, cache hit rates
  - LLM token usage & costs
- [ ] **Alerting Rules**: `monitoring/alerts/`
  - High error rate > 1%
  - Latency p99 > 5s
  - Disk/memory/CPU thresholds
  - LLM token budget exceeded
- [ ] **Distributed Tracing**: OpenTelemetry integration
- [ ] **Log Aggregation**: Structured JSON logs → Loki/ELK

### 10. Security & Compliance
- [ ] **RBAC**: Role-based access (admin, analyst, viewer)
- [ ] **mTLS**: Service-to-service encryption
- [ ] **Secrets Management**: HashiCorp Vault / AWS Secrets Manager
- [ ] **Audit Logging**: All API calls, data access, admin actions
- [ ] **Data Encryption**: At rest (Oracle TDE) + in transit (mTLS)
- [ ] **PII Handling**: Data classification, masking, retention policies
- [ ] **Compliance**: SOX, BCBS239, GDPR readiness checks

---

## 🟣 LOWER PRIORITY (Nice to Have)

### 11. Advanced Features
- [ ] **Predictive Break Detection**: ML model on hex-memory patterns
- [ ] **Auto-remediation**: Fixer executes semantic recommendations
- [ ] **SME Chat Interface**: Slack/Teams bot `@semantic why did TRD_123 break?`
- [ ] **Migration Dashboard**: Real-time Ab Initio vs PySpark parity tracking
- [ ] **Regulatory Audit Trail**: Immutable RCA documents for SOX/BCBS239

### 12. Migration Acceleration (Ab Initio → PySpark)
- [ ] **PySpark Connector**: Implement `PySparkConnector` in ingestion
- [ ] **Transform Equivalence Checker**: Ab Initio .xfr ↔ PySpark DataFrame API
- [ ] **Side-by-side Reconciliation**: Compare outputs row-by-row
- [ ] **Migration Dashboard**: Real-time parity tracking with drift alerts

---

## 📋 Quick Reference: Commands Cheatsheet

```bash
# Install with uv (after MSVC installed)
uv pip install -e . --no-build-isolation

# Run tests
pytest tests/unit -v --cov=src --cov-report=html
pytest tests/integration -v

# Code quality
ruff check src/ && black --check src/ && isort --check-only src/ && mypy src/

# Start services
docker-compose -f infra/docker-compose.yml up -d

# Run API
python -m isp_semantic_wise.api.main

# Health checks
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/detailed

# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Lint & format
ruff check src/ && black --check src/ && isort --check-only src/ && mypy src/

# Type check
mypy src/

# Docker
docker-compose -f infra/docker-compose.yml up -d
docker-compose -f infra/docker-compose.yml logs -f

# CI/CD locally
act push  # Requires 'act' tool for local GitHub Actions testing
```

---

## 📋 Quick Reference: Key Files

| Category | Key Files |
|----------|-----------|
| **Config** | `config/settings.yaml`, `config/models.yaml`, `config/.env.example` |
| **Architecture** | `DUAL_STACK_ARCHITECTURE.md`, `docs/architecture/ARCHITECTURE.md` |
| **ADRs** | `docs/adr/001-*.md` through `007-*.md` |
| **SME Guides** | `docs/sme/INTERVIEW_GUIDE.md`, `GLOSSARY_TEMPLATE.yaml` |
| **API Routes** | `src/isp_semantic_wise/api/routes/*.py` |
| **Services** | `src/isp_semantic_wise/services/*.py` |
| **Storage** | `src/isp_semantic_wise/storage/*.py` |
| **Processing** | `src/isp_semantic_wise/processing/*.py` |
| **Ingestion** | `src/isp_semantic_wise/ingestion/*.py` |
| **Pipeline** | `src/isp_semantic_wise/ingestion/pipeline.py` |
| **Tests** | `tests/unit/`, `tests/integration/`, `tests/fixtures/` |
| **CI/CD** | `.github/workflows/ci-cd.yml`, `infra/harness.yaml` |
| **Docker** | `infra/Dockerfile`, `infra/docker-compose.yml` |
| **Harness** | `infra/harness.yaml` |

---

## 🎯 Immediate Next Action

```bash
# 1. Install MSVC Build Tools (from Visual Studio Installer)
#    Workload: "Desktop development with C++"

# 2. Then run:
uv pip install -e . --no-build-isolation

# 2b. If pydantic-core fails:
uv pip install maturin
uv pip install -e . --no-build-isolation

# 2c. If pyyaml fails:
uv pip install pyyaml==6.0.3
uv pip install -e . --no-build-isolation

# 3. Start services
docker-compose -f infra/docker-compose.yml up -d

# 4. Initialize Oracle schema (run as DBA)
sqlplus sys/password@ORCL as sysdba @scripts/init_db.sql

# 5. Run API
python -m isp_semantic_wise.api.main

# 6. Test
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/health
```

---

## 📝 Notes

- **Primary Blocker**: MSVC Build Tools (Visual C++ 14.0+) required for C-extensions
- **Alternative**: Use Python 3.11/3.12 instead of 3.13 for better wheel availability
- **Alternative**: Use GitHub Actions (Linux runners) for CI/CD - no MSVC needed
- **Alternative**: Use WSL2/Ubuntu for development - native Linux wheels

---

*Last Updated: 2026-09-28 | Version: 0.1.0 | Status: Architecture Complete - Blocked on MSVC*