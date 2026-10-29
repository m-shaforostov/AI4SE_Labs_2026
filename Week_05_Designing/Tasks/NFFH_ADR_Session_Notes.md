# NFFH — ADR Session Notes

29 October 2026. Compact summary of this session; the earlier Task 1 architecture discussion is recorded separately in `NFFH_Architecture_Notes(1).md`.

## Purpose and source

Create an architecture decision record (ADR) from the attached Task 1 architecture discussion notes. The attached notes were read as the source; the original system description and its user stories were not independently rechecked during this session.

## ADR created

File: `NFFH_ADR_001.md`.

Title: **ADR-001: Use a modular monolith on managed hosting for NFFH**.

Status: **Proposed**, preserving the earlier discussion’s provisional recommendation. No final stakeholder acceptance, implementation, provider selection, or performance/cost validation was claimed.

The ADR documents context, decision drivers, the proposed architecture, implementation properties, alternatives, consequences, assumptions, open questions, and conditions for reconsideration.

## Proposed architecture

One backend deployment on managed hosting, with one relational application database and five logical modules:

- Accounts and access.
- Farms and areas.
- Catalog and inventory.
- Shopping cart.
- Orders and pickup.

Modules communicate through explicit internal interfaces and modify only their own tables. Administration reuses their business rules. Multiple application instances can run without changing this decomposition.

Orders coordinates checkout; Inventory owns stock validation and reservation rules. Cart, Inventory, and Orders share one transaction context and transaction-bound connection/session. Inner modules do not commit independently.

Managed authentication is compatible with this architecture. The framework, database product, provider, and authentication implementation remain undecided. Managed hosting does not itself imply serverless functions or microservices.

## Rationale and alternatives

The main reason for the proposed monolith is straightforward atomic checkout with fewer operational components. No measured requirement for independent deployment or scaling was established.

Independent services were deferred because separate databases introduce partial failures and require durable checkout attempts, stable reservation IDs, temporary holds, confirmation, expiry, idempotency, and reconciliation. Network timeouts represent uncertainty, not definite failure.

Managed serverless remains viable if one checkout function or database routine performs the stock and order writes within one transaction. Separate function invocations do not automatically share a transaction. Connection pressure, execution limits, startup latency, platform tooling, and provider dependence remain trade-offs; no cost or performance advantage was demonstrated.

## Revision 1 — Architecture diagram

Added a compact Mermaid diagram to the ADR showing all five modules within one backend deployment, the shared relational database, and a checkout transaction boundary grouping Orders, Cart, and Catalog/Inventory.

The accompanying explanation clarifies that the inner boundary represents operations participating in checkout, not every operation of those modules. Checkout work commits or rolls back together; all modules retain ownership of their tables.

## Revision 2 — Atomic idempotency

Made the retry guarantee explicit: **the customer-scoped checkout key record, associated request contents and order result, and stock changes commit in the same database transaction**.

- If commit succeeds but the response is lost, a retry with the same key and contents returns the saved order result without creating another order or reserving stock again.
- If the transaction rolls back, none of these changes is committed.
- A uniqueness constraint prevents simultaneous requests using the same customer-scoped key from committing duplicate orders.
- Reusing a key with changed contents is rejected.

## Other implementation properties retained

All-or-nothing checkout requires rollback if any cart item is unavailable. Row locks or conditional stock updates protect against concurrent overselling; availability reads alone are insufficient. Consistent lock ordering reduces deadlock risk.

The backend calculates authoritative totals and stores relevant product, price, and unit snapshots on order lines. Product removal must preserve order history. Authorization checks identity, permissions, and product-to-farm ownership; a farmer role alone is insufficient.

Connection limits must account for all application instances. Transactions should remain short, with appropriate connection-acquisition, lock, and transaction timeouts.

## Consequences and open questions

The design simplifies checkout, testing, debugging, and operation, but shares application deployment, scaling, failure scope, and database capacity. Module boundaries require discipline. Managed infrastructure does not remove responsibility for authorization, schema design, backups, or recovery configuration.

Proposed policies remain distinct from confirmed requirements: cart additions do not reserve stock; checkout does; checkout is all-or-nothing; and product removal preserves order history. One farm per cart remains unconfirmed.

Unresolved details include inventory units/precision, pickup dates and timezones, seasonal-product rules, cancellation and fulfillment behavior, user deletion, and account-suspension policy. Traffic, budget, team size, and availability/performance targets are unspecified.

## When to reconsider

Revisit the architecture if several teams demonstrably need independent releases, Inventory must serve other sales channels or partners, measured workloads require different scaling, or explicit security, infrastructure, or failure-isolation requirements demand separation. Serverless execution should be reconsidered if platform experience and workload/cost evidence establish a clear benefit.

Extract only capabilities justified by the new requirement. Catalog browsing could be separated while order creation and stock reservation remain in one transaction.

## Final session outcome

Created the proposed ADR and completed both requested revisions: the architecture diagram and explicit atomic persistence of the checkout key, order result, and stock changes. No implementation or architectural acceptance was performed.
