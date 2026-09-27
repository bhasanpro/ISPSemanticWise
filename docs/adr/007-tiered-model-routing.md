# ADR 007: Tiered Model Routing with Confidence

## Status
Accepted

## Context
Hybrid model strategy (ADR 001) requires reliable routing between Tier 1 and Tier 2 models. Routing must be fast, accurate, and explainable.

## Decision
Implement keyword-based routing with confidence scoring and service-specific overrides:

1. **Keyword-based classification**: Maintain keyword lists for Tier 1 and Tier 2 intents
2. **Confidence scoring**: Score based on keyword matches, default to Tier 1
3. **Service-level overrides**: Explicit routing for known services
4. **Confidence threshold**: Route to Tier 2 only if confidence > 0.7
4. **Explicit override**: Context can force tier

### Routing Logic
```
if context.force_tier:
    return context.force_tier
elif context.service in SERVICE_TIERS:
    return SERVICE_TIERS[context.service]
else:
    tier1_score = count(tier1_keywords in query)
    tier2_score = count(tier2_keywords in query)
    
    if tier2_score > tier1_score:
        return tier_2 (confidence = 0.5 + tier2_score * 0.1)
    elif tier1_score > tier2_score:
        return tier_1 (confidence = 0.5 + tier1_score * 0.1)
    else:
        return default_tier (confidence = 0.6)
```

### Tier 1 Keywords
show, list, find, search, query, lineage, trace, map, column, table, procedure

### Tier 2 Keywords
explain, why, root cause, impact, analyze, generate glossary, document, narrative, recommend, assess, synthesize

### Service Overrides
| Service | Tier |
|---------|------|
| nl2sql | tier_1 |
| glossary_generation | tier_2 |
| root_cause_narrative | tier_2 |
| impact_analysis | tier_2 |
| trade_match_debugger | hybrid |
| value_reconciler | hybrid |

## Consequences

### Positive
- **Fast**: O(keywords) classification, no LLM call
- **Explainable**: Clear reasoning for routing decision
- **Tunable**: Keyword lists easily adjustable
- **Extensible**: Service overrides for hybrid services

### Negative
- **Keyword maintenance**: Lists need periodic review
- **False positives**: Keyword matching can misclassify
- **Context blind**: Doesn't understand query semantics

### Risks
- Misrouting complex queries to Tier 1
- Overusing Tier 2 increasing costs
- Keyword drift over time

## Alternatives Considered
1. **LLM-based classifier** - More accurate but adds latency/cost
2. **Embedding-based routing** - Semantic but needs embeddings
3. **Fixed per-service** - Simpler but inflexible for hybrid
4. **User-selected** - Burden on user, inconsistent

## Related ADRs
- [ADR 001](001-hybrid-model-strategy.md) - Hybrid Model Strategy
- [ADR 004](004-vector-graph-hybrid-storage.md) - Could use embeddings for routing

## References
- Implementation in `src/isp_semantic_wise/services/router.py`
- Keywords configurable in `config/models.yaml`
- Evaluation in `scripts/evaluate.py`