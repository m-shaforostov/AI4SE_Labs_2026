# NFFH ADR session notes

Date: 1 November 2026

## Request

Maintain compact notes throughout this session; deliver the complete notes file only when requested. Use Architecture Exploration and ADRs to create an ADR from the attached Task 1 discussion.

## Sources and workflow

- Read `NFFH_Architecture_Discussion (1).md` completely. It summarizes Task 1, updated 1 November 2026.
- Read the Architecture Exploration and ADRs skill and its compact ADR template.
- Original `NFFH(1).txt` was not available or independently verified. Requirements/story mappings are reported by the supplied discussion.

## ADR created

Created `NFFH_ADR_001_Proposed.md`: modular monolith on managed hosting with one managed relational database for the initial NFFH backend.

- Retained Proposed status: the source records a provisional recommendation, not final acceptance.
- Proposed five logical modules: Accounts, Farm and Area Information, Catalog and Inventory, Cart, Ordering; administration uses authoritative module interfaces.
- Added evidence ledger, responsibility overview, deployment diagram, alternative comparison, rationale, consequences, current open questions and service-split questions.
- Preserved all-or-nothing checkout and one-team deployment as working policies/assumptions, not original requirements.
- Did not import a one-farm-per-cart restriction: the supplied discussion explicitly leaves cart scope open.
- Specified one transaction for guarded stock changes, order/lines, customer-scoped unique checkout key, fingerprint and durable result/reference.
- Covered concurrency, rollback, crashes, lost responses and same-key retries; limited the deduplication claim to retained identical keys.
- Added cart snapshot/version and immutable retry contents as implementation questions inferred from the documented retry design, not established requirements.
- Compared independent services and managed functions without invented cost or performance evidence. Kept distributed recovery brief and its unresolved protocol explicit.
- Separated logical modules, deployment boundaries and hosting choices. Diagram transaction node denotes one checkout operation, not all module activity.

## Review and remaining work

Reviewed status, source attribution, policy labels, alternatives, rationale, diagram/prose consistency and transaction/idempotency scope. No implementation, provider evaluation, runtime testing or final acceptance occurred.

## ADR refinement requested and completed

- User requested source provenance, explicit committed-result replay before mutable validation, separate architecture-acceptance versus checkout questions, and shorter future service recovery detail.
- Read the available earlier `NFFH_Architecture_Discussion_Notes1_after_skill(4).md` completely. It explicitly stops before final recommendation; it supports the options and checkout/recovery discussion, not final selection.
- Added substantive provenance: later discussion supplies the one-team assumption, suspension discussion, fuller functions comparison, recommendation, completion statement and reconsideration triggers. Original requirements remain unverified here.
- Clarified authentication/authorization precedes fingerprint comparison and committed-result replay; mutable cart, price and stock are not revalidated on matching committed retries. Only newly claimed attempts validate and change stock. Preserved atomic commit, unique claim arbitration, rollback and timeout semantics.
- Split architecture-acceptance questions from checkout implementation details. Shortened service recovery to architectural implications. Preserved Proposed status, existing tables and the diagram.
- Reviewed the revised document for these requirements; no runtime testing or final acceptance occurred. Full revised ADR returned as a file.

## Source-provenance correction

User clarified that the original after-skill notes stop before the checkout-policy answer, while the longer `(4)` copy reaches service recovery. Condensed the provenance explanation into one paragraph, retained the later discussion as primary, and verified the remainder of the ADR was unchanged. The original stopping point is attributed to the user correction; the longer copy was read in this session.

## Final session outcome

The user requested the final notes file. These notes summarize the full ADR-creation session and both refinement requests. The final ADR retains Proposed status, its tables and diagram, and precise atomic-commit/idempotency guarantees. Architecture acceptance, implementation, operational validation and runtime tests remain outstanding; requesting final notes does not establish acceptance.
