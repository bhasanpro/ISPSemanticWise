# ADR 001: Hybrid Model Strategy (Tier 1 + Tier 2)

## Status
Accepted

## Context
ISPSemanticWise needs to balance cost, latency, and capability across different semantic services:
- NL→SQL translation needs fast, reliable tool calling
- Root cause narratives need deep reasoning over code
- Glossary generation needs code understanding
- Impact analysis needs multi-hop reasoning

NVIDIA Developer Program provides access to models of varying sizes and capabilities.

## Decision
Adopt a hybrid two-tier model strategy:

| Tier | Models | Use Cases |
|------|--------|-----------|
| **Tier 1 (Fast, Cheap)** | Llama-3.2-11B, Phi-3.5-mini | NL→SQL, tool calling, query routing, entity extraction, lineage traversal |
| **Tier 2 (High-end)** | Nemotron-3-Super/Ultra, Llama-3.1-Nemotron-70B | Code understanding, glossary generation, root cause narratives, impact analysis, documentation |

Route queries based on intent classification + keyword matching. Hybrid services (debugger, reconciler) use Tier 1 for structured tasks + Tier 2 for synthesis.

## Consequences

### Positive
- **Cost optimization**: 90%+ queries on Tier 1 (cheap/fast)
- **Right tool for job**: Tier 2 reserved for reasoning-intensive tasks
- **Latency**: Tier 1 < 2s, Tier 2 async acceptable
- **Flexibility**: Can swap models per tier independently

### Negative
- **Routing complexity**: Need reliable intent classification
- **Consistency risk**: Different models may give different answers
- **Debugging**: Harder to trace which tier produced output

### Risks
- Tier 1 may hallucinate on complex code understanding
- Tier 2 API latency could impact hybrid service SLAs
- Model deprecation (e.g., Llama-3.1-70B EOL) requires migration

## Alternatives Considered
1. **Single large model** - Too expensive, high latency for simple queries
2. **All Tier 1** - Insufficient for code understanding, narrative generation
3. **All Tier 2** - Prohibitive cost, high latency
4. **Local models only** - Limited by hardware, no Nemotron access

## Related ADRs
- [ADR 007](007-tiered-model-routing.md) - Tiered Model Routing implementation
- [ADR 002](002-ab-initio-first-pyspark-ready.md) - Ab Initio ingestion affects code understanding needs

## References
- NVIDIA API Model Catalog
- Model evaluation results in `tests/fixtures/eval/`