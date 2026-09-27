# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the ISPSemanticWise project.

## What is an ADR?

An Architecture Decision Record captures a significant architectural decision along with its context and consequences. Each ADR is immutable once written - if a decision changes, a new ADR supersedes the old one.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-hybrid-model-strategy.md) | Hybrid Model Strategy (Tier 1 + Tier 2) | Accepted | 2026-01-27 |
| [002](002-ab-initio-first-pyspark-ready.md) | Ab Initio First, PySpark Ready Architecture | Accepted | 2026-01-27 |
| [003](003-networkx-as-graph-backbone.md) | NetworkX as Graph Backbone | Accepted | 2026-01-27 |
| [004](004-vector-graph-hybrid-storage.md) | Vector + Graph Hybrid Storage | Accepted | 2026-01-27 |
| [005](005-tree-sitter-for-code-parsing.md) | Tree-sitter for Code Parsing | Accepted | 2026-01-27 |
| [006](006-offline-first-mobile-health-tracker.md) | Offline-First Mobile Health Tracker (Separate Product) | Accepted | 2026-01-27 |
| [007](007-tiered-model-routing.md) | Tiered Model Routing with Confidence | Accepted | 2026-01-27 |

## ADR Template

```markdown
# ADR XXX: [Title]

## Status
[Proposed | Accepted | Superseded | Deprecated]

## Context
[What is the issue that we're seeing that is motivating this decision or change?]

## Decision
[What is the change that we're proposing or have decided to do?]

## Consequences
[What becomes easier or more difficult to do and any risks introduced by this change?]

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Drawback 1]
- [Drawback 2]

### Risks
- [Risk 1]
- [Risk 2]

## Alternatives Considered
1. [Alternative 1] - [Why rejected]
2. [Alternative 2] - [Why rejected]

## Related ADRs
- [ADR XXX] - [Related decision]

## References
- [Link to relevant docs, discussions, etc.]
```