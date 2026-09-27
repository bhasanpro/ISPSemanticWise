# ISPSemanticWise
## SME Knowledge Builder for Capital Markets Post-Trade Management

> **Bridging business language and technical implementation in post-trade operations**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-POC-orange.svg)]()
[![CI/CD](https://github.com/bhasanpro/ISPSemanticWise/actions/workflows/ci-cd.yml/badge.svg)]()

---

## 🎯 Overview

ISPSemanticWise builds a **semantic layer** that connects business users' natural language questions to the technical implementation across:
- **Ab Initio** ETL graphs (current) → **PySpark** (planned migration)
- **Oracle** stored procedures & schemas
- **Unix** shell scripts (ksh/bash)
- **Email/Jira/Confluence** tribal knowledge
- **NetworkX** observability graph (existing)

### Core Problem
```
Business User: "Why did trade T123 fail to match?"
                    │
                    ▼ (SEMANTIC LAYER - THIS PROJECT)
                    │
Technical:  Ab Initio G_TRADE_MATCH → SP_RECON_MATCH → RECON_RESULTS
                    │
                    ▼
Answer: "Fee schedule for GS (0.05%) applied in enrichment 
         but NOT in counterparty confirmation. 
         Difference: $500 → Break Code: SAMT"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ISPSemanticWise                             │
├─────────────────────────────────────────────────────────────────┤
│  INGESTION     │  PROCESSING    │  SEMANTIC SERVICES  │ STORAGE │
│  ──────────    │  ──────────    │  ─────────────────  │ ──────  │
│  • Ab Initio   │  • Parsing     │  • Glossary Builder │ Vector  │
│  • Oracle SP   │  • Chunking    │  • NL→SQL          │ Graph   │
│  • Unix Shell  │  • Embedding   │  • Debugger        │NetworkX │
│  • Emails/Jira │  • Linking     │  • Root Cause      │Relational│
│  • NetworkX    │                │  • Impact Analyzer │         │
└─────────────────────────────────────────────────────────────────┘
```

### Hybrid Model Strategy
| Tier | Models | Use Cases |
|------|--------|-----------|
| **Tier 1 (Cheap)** | Llama-3.2-11B, Phi-3.5-mini | NL→SQL, tool calling, routing, lineage traversal |
| **Tier 2 (High-end)** | Nemotron-3-Super/Ultra | Code understanding, narratives, glossary, impact analysis |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- **Oracle Database** access (19c/21c/23c) - enterprise provided
- **NVIDIA API Key** (for Tier 2 models) or local Ollama
- **GitHub Actions** for CI/CD
- **Harness** for production deployment
- **Docker** (optional - for local ChromaDB/Neo4j only)

### Local Development Setup
```bash
# Clone
git clone https://github.com/bhasanpro/ISPSemanticWise.git
cd ISPSemanticWise

# Setup environment
cp config/.env.example config/.env
# Edit config/.env with your keys (NVIDIA_API_KEY, ORACLE_PASSWORD, SECRET_KEY)

# Install uv (10-100x faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Install dependencies with uv
uv pip install --system --no-cache -e .[dev]

# Start local services (optional - for local development only)
# ChromaDB + Neo4j for local development
docker-compose -f infra/docker-compose.yml up -d

# Initialize Oracle schema (run as DBA)
# sqlplus sys/password@ORCL as sysdba @scripts/init_db.sql

# Run ingestion (sample data)
python scripts/ingest_sample.py

# Start API
python -m isp_semantic_wise.api.main
```

### Access Points (Local Development)
- **API**: http://localhost:8000/docs
- **UI**: http://localhost:3000 (if UI enabled)
- **Graph DB**: http://localhost:7474 (Neo4j Browser)

---

## 🚀 CI/CD & Deployment (GitHub Actions + Harness)

### Pipeline Overview
```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌─────────────────┐
│  Push/PR    │──►│ Lint & Test  │──►│ Integration │──►│ Build & Push    │
│  to main    │   │ (GitHub)     │   │ Tests       │   │ Docker Image    │
└─────────────┘   └──────────────┘   └─────────────┘   └────────┬────────┘
                                                                   │
                                                       ┌───────────▼───────────┐
                                                       │ Trigger Harness       │
                                                       │ Staging Pipeline      │
                                                       └───────────┬───────────┘
                                                                     │
                                                           ┌─────────▼──────────┐
                                                           │ Manual Approval    │
                                                           │ → Harness Prod     │
                                                           └────────────────────┘
```

### GitHub Actions (CI)
- **Lint & Test**: Ruff, MyPy, Black, isort, pytest unit tests
- **Integration Tests**: ChromaDB, Neo4j, Oracle connectivity
- **Build & Push**: Docker image to Docker Hub on merge to main

### Harness (CD)
- **Staging**: Auto-deployed on merge to main
- **Production**: Manual approval via Harness UI
- **Model Evaluation**: Scheduled daily via GitHub Actions schedule

### Required GitHub Secrets
| Secret | Purpose |
|--------|---------|
| `NVIDIA_API_KEY` | Tier 2 model access |
| `ORACLE_PASSWORD` | Oracle DB password |
| `ORACLE_HOST` | Oracle DB host |
| `ORACLE_PORT` | Oracle DB port (1521) |
| `ORACLE_SERVICE_NAME` | Oracle service name |
| `ORACLE_USER` | Oracle user |
| `SECRET_KEY` | JWT signing key |
| `NVIDIA_API_KEY` | NVIDIA API key |
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub token |
| `HARNESS_API_KEY` | Harness API key |
| `HARNESS_ACCOUNT_ID` | Harness account ID |
| `HARNESS_ORG_ID` | Harness org ID |
| `HARNESS_PROJECT_ID` | Harness project ID |

---

## 📁 Project Structure

```
ISPSemanticWise/
├── config/                 # Configuration files
│   ├── settings.yaml       # Main settings
│   ├── .env.example        # Environment template
│   └── models.yaml         # Model routing config
├── docs/                   # Documentation
│   ├── architecture/       # Architecture docs
│   │   └── ARCHITECTURE.md # Main architecture (from brainstorming)
│   ├── sme/                # SME interview guides, glossaries
│   └── adr/                # Architecture Decision Records
├── infra/                  # Infrastructure as Code
│   ├── docker-compose.yml  # Local dev only (ChromaDB + Neo4j)
│   ├── Dockerfile          # Build image for Harness
│   ├── harness.yaml        # Harness pipeline definition
│   └── k8s/                # Kubernetes manifests (for Harness)
├── scripts/                # Operational scripts
│   ├── ingest_sample.py
│   ├── run_ingestion.py
│   └── evaluate.py
├── src/
│   ├── ingestion/          # Source connectors
│   ├── processing/         # Processing pipeline
│   ├── services/           # Semantic services (Tier 1/2)
│   ├── storage/            # Storage adapters
│   ├── api/                # FastAPI REST API
│   └── ui/                 # Frontend (React/Streamlit)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── .github/
│   └── workflows/
│       └── ci-cd.yml       # GitHub Actions CI/CD
└── README.md
```

---

## 🔧 Configuration

### Environment Variables (`config/.env`)
```bash
# NVIDIA API (Tier 2 models)
NVIDIA_API_KEY=your_key_here

# Vector DB (ChromaDB - local dev uses docker-compose)
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Graph DB (Neo4j - local dev uses docker-compose)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Relational DB (Oracle - enterprise provided)
ORACLE_HOST=your-oracle-host
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCL
ORACLE_USER=ISP_SEMANTIC_USER
ORACLE_PASSWORD=your_oracle_password

# Model Routing
TIER1_MODEL=meta/llama-3.2-11b-vision-instruct
TIER2_MODEL=nvidia/nemotron-3-super-120b-a12b
```

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires ChromaDB, Neo4j, Oracle)
pytest tests/integration -v

# With coverage
pytest --cov=src --cov-report=html

# Evaluate model outputs
python scripts/evaluate.py --suite glossary
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [Architecture](docs/architecture/ARCHITECTURE.md) | Full architecture & strategy |
| [SME Interview Guide](docs/sme/INTERVIEW_GUIDE.md) | Questions for domain experts |
| [Glossary Template](docs/sme/GLOSSARY_TEMPLATE.yaml) | Standard glossary format |
| [ADR Index](docs/adr/README.md) | Architecture Decision Records |
| [Harness Pipeline](infra/harness.yaml) | Harness pipeline definition |

---

## 🤝 SME Engagement

### Why SMEs Matter
- **Validate glossary mappings** (business term ↔ technical column)
- **Provide ground truth** for evaluation sets
- **Define break codes & business rules** (tribal knowledge)
- **UAT semantic services** (debugger, narrator accuracy)

### Engagement Model
| Phase | SME Involvement | Time Commitment |
|-------|-----------------|-----------------|
| **Glossary Bootstrapping** | 2-3 sessions × 2hrs | Week 1-2 |
| **Break Code Taxonomy** | 1 session × 3hrs | Week 3 |
| **UAT / Feedback** | Bi-weekly 1hr | Ongoing |

### Questions for SMEs
See [SME Interview Guide](docs/sme/INTERVIEW_GUIDE.md) for detailed questions covering:
- Business term definitions & synonyms
- Break code taxonomy & root causes
- Reconciliation rules & exceptions
- Counterparty-specific behaviors
- Regulatory/reporting requirements

---

## 🛣️ Roadmap

| Phase | Timeline | Focus |
|-------|----------|-------|
| **POC** | Weeks 1-4 | Ingestion, NL→SQL, basic glossary |
| **Core Services** | Weeks 5-10 | Debugger, Narrator, Lineage Explorer |
| **Advanced** | Weeks 11-16 | Impact Analyzer, Email ingestion, PySpark support |
| **Production** | Weeks 17-20 | Security, RBAC, Monitoring, UAT |

---

## 🔐 Security

- **No raw code in prompts** — only embeddings & metadata
- **Tier 1 on-prem** — sensitive code never leaves infrastructure
- **Tier 2 via API** — with DLP scrubbing for PII/secrets
- **RBAC** — role-based access to glossary, lineage, debugger
- **Audit logging** — all queries & responses logged

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built on NetworkX observability foundation
- NVIDIA Nemotron models for Tier 2 reasoning
- Tree-sitter for robust code parsing
- Capital markets post-trade SMEs for domain knowledge

---

## 📞 Contact

**Project Lead**: [Your Name]  
**Team**: [Your Team]  
**Slack**: #isp-semantic-wise  
**Email**: [your-email@company.com]

---

*Last Updated: 2026-09-27 | Version: 0.1.0 (POC)*