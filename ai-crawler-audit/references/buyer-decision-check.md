# Buyer decision check

Use in `buyer-check` mode or after Phase 5 of the full audit. This is an information
review. It does not forecast demand, prove an agent recommends the offer, or authorize
publication, booking, account access, a data disclosure, or purchase.

## Inputs and boundary

Declare one business, one offer, its buyer and the exact files/URLs to open. Read the
business's `docs/brand/facts.md`, `sources.md`, `audience.md` and `positioning.md` when
present; label draft records. Price values stay in their existing canonical source.
If sources are absent, record that absence and evaluate only what is actually available.
Never pull another client's facts to fill a gap.

Questions from customers or approved intake cite their source. New questions are marked
`hypothesis`, not represented as customer language. A manual pass over declared public
pages needs no paid model or account connector. Any later model/connector pass inherits
the existing graph's approved cost and call budget; stop at a rate limit.

## Review three perspectives

1. **User fit:** Which job is covered? Who fits or does not fit? What must the customer
   supply? What are the scope, limits and supported handoff? What proof is relevant?
2. **Implementation:** Which integrations and permissions are needed? What happens on
   uncertainty or failure? Who owns the data, system and off switch? Which privacy,
   retention, access and support terms are actually stated?
3. **Budget owner:** Where is the price authority? Which offer/tier does a price cover?
   What recurring or usage costs are stated or unknown? What evidence supports value?
   What must be scoped, approved or agreed before the next step?

An honest scoping step is a valid answer for custom work. Don't invent a fixed quote,
ROI, implementation date, unlimited support, security certification or checkout capability.
Distinguish a specialist entry package from broader workflow/custom-build price bands.

## Output: buyer-decision-check.md

Write in the existing run folder, or `docs/audits/<run-id>/` for a standalone pass.
Use `status: draft`; a separate checker records its later review. Save the following:

```markdown
# Buyer decision check - <offer>
- Business / buyer / observation date:
- Mode: buyer-check (information review; discovery and transactions not tested)
- Declared sources:
- Question basis: customer evidence | approved intake | hypothesis
- Fact authority: approved | proposed | mixed | none

| ID | Perspective | Question | Required for next step? | Answer / exact source pointer | Answerability | Evidence kind | Owner confirmation |
|----|-------------|----------|-------------------------|-------------------------------|---------------|---------------|--------------------|

## Required unknowns or conflicting answers
## What the existing sources already answer
## Before/after comparison (same questions and sources)
## Next internal action and owner
## What was not tested
```

Allowed `Answerability` values: `answered`, `partial`, `missing`, `conflicting`.
Allowed `Evidence kind` values: `published claim`, `source-code definition`,
`observed behavior`, `customer report`, `none`. A published claim is not an operational
test. A source-code price is not proof that checkout charges it.
`Owner confirmation` is `approved` only with recorded owner approval, otherwise
`proposed` or `unknown`. Keep question answerability separate from confirmation.

Never manufacture a before state. If a price or case study already existed, mark it
answered before and after; the improvement may be a clearer distinction or a documented
unknown. Don't count reorganizing text as a measured conversion or ranking uplift.

## Verdict and handoff

- `information gaps` if a required question is missing, partial or conflicting.
- `needs confirmation` if required answers exist but rely on unapproved claims.
- `answerable from declared evidence` only when required answers and their authority
  are supported. This is still not approval or buying readiness.

Name the evidence and owner for each next action. Route factual validation to
`claim-audit`, missing brand inputs to `marketing-start`, and performance measurement
to the existing campaign review. Ask a human about facts only after the actual missing
information is concrete; do not halt internal implementation or investigation for a
hypothetical future publication gate.

## Checks

- A known public price is not reported missing because the draft pack omitted it.
- Two prices for different scopes are not called inconsistent without checking scope.
- A qualitative case study never becomes a quantified uplift.
- Required missing integration/privacy/usage terms remain unknown; no guessing.
- Draft sources never become approved because a model agreed or the files were committed.
- Access, discoverability, shortlist results, transactions and conversions stay distinct.
