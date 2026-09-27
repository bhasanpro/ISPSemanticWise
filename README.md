# ISPSemanticWise
## SME Knowledge Builder for Capital Markets Post-Trade Management

> **Bridging business language and technical implementation in post-trade operations**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-POC-orange.svg)]()

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
- Docker & Docker Compose
- NVIDIA API Key (for Tier 2 models) or local Ollama

### Installation
```bash
# Clone
git clone https://github.com/your-org/ISPSemanticWise.git
cd ISPSemanticWise

# Setup environment
cp config/.env.example config/.env
# Edit config/.env with your keys

# Install dependencies
pip install -r requirements.txt

# Start services
docker-compose up -d

# Run ingestion (sample data)
python scripts/ingest_sample.py

# Start API
python -m src.api.main
```

### Access Points
- **API**: http://localhost:8000/docs
- **UI**: http://localhost:3000 (if UI enabled)
- **Graph DB**: http://localhost:7474 (Neo4j Browser)

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
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── k8s/                # Kubernetes manifests (future)
├── scripts/                # Operational scripts
│   ├── setup.sh
│   ├── ingest_sample.py
│   ├── run_ingestion.py
│   └── evaluate.py
├── src/
│   ├── ingestion/          # Source connectors
│   │   ├── ab_initio/      # Ab Initio XML/GraphML parser
│   │   ├── oracle/         # PL/SQL parser, schema extractor
│   │   ├── unix/           # Shell script parser
│   │   ├── email/          # Email thread parser
│   │   ├── jira/           # Jira/Confluence connector
│   │   └── networkx/       # NetworkX graph sync
│   ├── processing/         # Processing pipeline
│   │   ├── parsers/        # Tree-sitter based parsers
│   │   ├── chunkers/       # Semantic chunking strategies
│   │   ├── embedders/      # Embedding generation
│   │   └── linkers/        # Entity linking & resolution
│   ├── services/           # Semantic services (Tier 1/2)
│   │   ├── glossary/       # Business glossary builder
│   │   ├── nl2sql/         # NL→SQL translator
│   │   ├── debugger/       # Trade match debugger
│   │   ├── narrator/       # Root cause narrator
│   │   ├── impact/         # Impact analyzer
│   │   └── router.py       # Model tier routing
│   ├── storage/            # Storage adapters
│   │   ├── vector.py       # Chroma/Pinecone/Weaviate
│   │   ├── graph.py        # Neo4j/NetworkX
│   │   └── relational.py   # PostgreSQL metadata
│   ├── api/                # FastAPI REST API
│   │   ├── routes/         # API endpoints
│   │   ├── schemas/        # Pydantic models
│   │   └── main.py         # App entry point
│   └── ui/                 # Frontend (React/Streamlit)
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Sample data (Ab Initio, SQL, Shell)
└── .github/
    └── workflows/          # CI/CD pipelines
```

---

## 🔧 Configuration

### Environment Variables (`config/.env`)
```bash
# NVIDIA API (Tier 2 models)
NVIDIA_API_KEY=your_key_here

# Vector DB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Graph DB
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Relational DB
POSTGRES_DSN=postgresql://user:pass@localhost:5432/isp_semantic

# Model Routing
TIER1_MODEL=meta/llama-3.2-11b-vision-instruct
TIER2_MODEL=nvidia/nemotron-3-super-120b-a12b
```

### Model Routing (`config/models.yaml`)
```yaml
tier_1:
  model: "meta/llama-3.2-11b-vision-instruct"
  provider: "nvidia"
  use_cases:
    - nl2sql
    - query_routing
    - entity_extraction
    - lineage_traversal
  max_tokens: 2000
  temperature: 0.1

tier_2:
  model: "nvidia/nemotron-3-super-120b-a12b"
  provider: "nvidia"
  use_cases:
    - code_understanding
    - glossary_generation
    - root_cause_narrative
    - impact_analysis
  max_tokens: 4000
  temperature: 0.3
```

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
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