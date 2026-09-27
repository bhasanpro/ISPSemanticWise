# SME Interview Guide for ISPSemanticWise

## Purpose
This guide structures interviews with Subject Matter Experts (SMEs) in capital markets post-trade operations to:
1. Build the business glossary with authoritative definitions
2. Validate technical-to-business mappings
3. Document break code taxonomy and root causes
4. Capture tribal knowledge from emails/Jira
5. Define reconciliation rules and exception handling

---

## Interview Structure

### Session 1: Business Glossary Bootstrapping (2 hours)
**Participants:** 2-3 Senior Business Analysts / Operations Leads
**Goal:** Establish authoritative definitions for top 50-100 business terms

#### Part A: Term Identification (45 min)
For each business area, identify:
| Business Area | Key Terms to Define |
|---------------|---------------------|
| **Trade Capture** | Trade Date, Trade ID, Counterparty, Trade Status, Settlement Amount, Settlement Currency, Trade Type |
| **Reconciliation** | Break Code, Settlement Amount Mismatch, Settlement Date Mismatch, Counterparty ID Mismatch, Break Resolution |
| **Settlement** | Settlement Date, Value Date, Settlement Amount, Settlement Currency, Settlement Instruction, Failed Settlement |
| **Counterparty** | Counterparty ID, Counterparty Name, SSI (Standard Settlement Instructions), Fee Schedule |
| **Fees & Charges** | Settlement Fee, Custody Fee, Commission, Fee Schedule, Fee Basis |
| **Corporate Actions** | CA Event, Entitlement, Ex-Date, Record Date, Pay Date |

For each term, capture:
- **Standard term** (authoritative name)
- **Synonyms/aliases** used across systems/docs
- **Business definition** (2-3 sentences in business language)
- **Category** (trade/settlement/counterparty/risk/fee/ca)
- **Related terms** (synonyms, antonyms, related concepts)
- **Regulatory relevance** (e.g., CSDR, T+1, MiFID II)

#### Part B: Technical Mapping Validation (45 min)
For each term, validate technical mappings:

| Business Term | Source System | Technical Artifact | Column/Port | Transformation Logic | Confidence (1-5) |
|---------------|---------------|-------------------|-------------|---------------------|------------------|
| Trade Date | Ab Initio | G_TRADE_CAPTURE | TRD_DT | Pass-through | |
| Trade Date | Oracle | TRADE_CORE | TRD_DT | No transform | |
| Trade Date | Unix | pre_process_trades.ksh | TRADE_DATE | Date parsing | |

#### Part C: Synonym & Alias Collection (30 min)
For each term, collect all variants seen in:
- Ab Initio port names
- Oracle column names
- Unix script variables
- Email threads
- Jira tickets
- Confluence pages
- Verbal communication

---

### Session 2: Break Code Taxonomy & Root Causes (2 hours)
**Participants:** 2 Reconciliation Specialists + 1 BA
**Goal:** Authoritative break code taxonomy with root causes

#### Break Code Inventory
For each break code, capture:

| Break Code | Description | Category | Frequency | Typical Root Cause | Resolution SLA | Auto-resolvable? |
|------------|-------------|----------|-----------|-------------------|----------------|------------------|
| SAMT | Settlement Amount Mismatch | Amount | High | Fee schedule mismatch | 4 hours | Partial |
| SDAT | Settlement Date Mismatch | Date | Medium | Calendar/holiday diff | 2 hours | Yes |
| CPID | Counterparty ID Mismatch | Counterparty | Low | SSI mismatch | 2 hours | Manual |

#### Root Cause Deep Dive (Top 10 Break Codes)
For each top break code, document:

1. **Technical Trace**: Step-by-step where divergence occurs
2. **Business Root Cause**: Business-language explanation
3. **Impact**: Financial, regulatory, operational
4. **Current Resolution Process**: Steps, owners, tools
4. **Prevention**: What would prevent recurrence

#### Exception Handling Rules
Document exception rules:
- When is manual override allowed?
- Who authorizes?
- Audit trail requirements
- Regulatory reporting implications

---

### Session 3: Reconciliation Rules & Exception Handling (1.5 hours)
**Participants:** Reconciliation Lead + Senior BA
**Goal:** Document reconciliation logic and exception handling

#### Matching Rules
| Rule ID | Description | Source Fields | Target Fields | Tolerance | Break Code | Exception Handling |
|---------|-------------|---------------|---------------|-----------|------------|-------------------|
| M001 | Settlement Amount Match | Enriched SETT_AMT | Confirmation CONF_AMT | 0.01 | SAMT | Auto-retry with fee adjustment |
| M002 | Settlement Date Match | Enriched TRD_DT | Confirmation CONF_DT | 0 days | SDAT | Auto-retry next business day |

#### Exception Scenarios
Document for each exception type:
- Trigger condition
- Auto-resolution attempt
- Manual intervention required
- Approval workflow
- Audit trail
- Regulatory reporting

---

### Session 4: Tribal Knowledge Extraction (1 hour)
**Participants:** 2-3 Senior Engineers/DBAs
**Goal:** Capture knowledge from emails, Jira, Confluence

#### Email Thread Analysis
Provide sample email threads about:
- Break investigations
- System changes
- Counterparty issues
- Regulatory changes

Extract:
- Key decisions made
- Rationales
- People involved
- Action items
- Open questions

#### Jira/Confluence Mining
Identify key pages:
- Runbooks
- Incident postmortems
- System architecture docs
- Data dictionary pages
- Change management records

---

### Session 5: UAT & Validation (1 hour, recurring bi-weekly)
**Participants:** Mixed group (BA, Engineer, Operations)
**Goal:** Validate semantic services output

#### Test Scenarios
| Scenario | Input | Expected Output | Pass/Fail | Notes |
|----------|-------|----------------|-----------|-------|
| Glossary term "Settlement Amount" | Query term | Correct mappings + definition | | |
| NL→SQL "Show breaks for GS" | Natural language | Correct SQL + lineage | | |
| Debug trade TRD_123 | Trade ID + break code | Root cause + action | | |
| Narrate incident INC_456 | Incident data | Business narrative | | |

---

## Question Templates

### For Business Term Definition
```
1. What is the standard name for this concept? (e.g., "Settlement Amount")
2. What other names have you heard it called? (synonyms)
3. In 2-3 sentences, how would you explain this to a new hire?
4. Which business area does this belong to? (trade/settlement/counterparty/risk/fee/CA)
5. What related terms should we know? (synonyms, related concepts)
6. Is this term used in regulatory reporting? (CSDR, T+1, etc.)
6. What systems use this term? (Ab Initio, Oracle, Unix, etc.)
7. Are there any common misconceptions about this term?
```

### For Technical Mapping
```
1. In Ab Initio, which graph/port represents this?
2. In Oracle, which table/column?
3. In Unix scripts, which variable?
4. What transformation happens? (formula, lookup, calculation)
5. Are there any data quality issues?
6. Confidence level (1-5)?
```

### For Break Code Root Cause
```
1. Walk me through the technical trace for this break.
2. At what exact step does the divergence occur?
3. What is the business-language root cause?
4. What is the financial/operational impact?
5. How is this currently resolved?
6. Who is involved in resolution?
6. What would prevent this from happening?
7. Can this be auto-resolved? Under what conditions?
```

### For Exception Handling
```
1. What triggers this exception?
2. What auto-resolution is attempted?
3. When is manual intervention required?
4. Who approves manual resolution?
5. What audit trail is created?
6. Any regulatory reporting requirements?
```

---

## Documentation Outputs

### Deliverables from Interviews
1. **Business Glossary YAML** - Authoritative term definitions
2. **Technical Mapping Matrix** - Business ↔ Technical mappings
3. **Break Code Taxonomy** - Authoritative break code definitions
4. **Root Cause Catalog** - Documented root causes per break code
5. **Exception Handling Rules** - Documented exception flows
6. **Synonym Dictionary** - All term variants across systems
6. **Test Cases** - UAT scenarios for semantic services

### Validation Checklist
- [ ] All top 50 terms defined and validated
- [ ] Technical mappings reviewed by both BA and Engineer
- [ ] Break codes cover 95%+ of historical breaks
- [ ] Root causes documented for top 10 break codes
- [ ] Exception handling rules cover 90%+ of exceptions
- [ ] Synonym dictionary covers all system variants
- [ ] UAT scenarios defined for all semantic services

---

## Interview Logistics

### Preparation (1 week before)
- [ ] Send pre-read materials (current glossary draft, break code list)
- [ ] Share sample technical artifacts (Ab Initio graph, Oracle SP, Unix script)
- [ ] Prepare glossary template
- [ ] Schedule 2-hour blocks with 15-min breaks
- [ ] Assign note-taker (separate from facilitator)

### During Interview
- [ ] Record session (with permission)
- [ ] Use shared screen for collaborative editing
- [ ] Park off-topic items for follow-up
- [ ] Summarize decisions at end of each section

### Post-Interview (within 24 hours)
- [ ] Distribute meeting notes
- [ ] Update glossary/mappings
- [ ] Flag items needing follow-up
- [ ] Schedule validation session

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Glossary coverage | 100% of top 100 terms defined |
| Technical mapping accuracy | > 95% validated by SMEs |
| Break code coverage | 95%+ of historical breaks categorized |
| Root cause documentation | 100% of top 10 break codes |
| SME satisfaction | > 4.5/5 on post-interview survey |
| UAT pass rate | > 90% for semantic services |