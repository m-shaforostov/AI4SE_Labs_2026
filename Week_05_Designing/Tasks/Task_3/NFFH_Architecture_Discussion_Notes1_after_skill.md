# NFFH architecture exploration — complete discussion notes

Updated: 1 November 2026  
Status: Task 1 complete at the architecture-selection level. Recommendation remains Proposed.

## 1. Purpose and evidence

The user requested three viable architectures for Not Far(m) From Home (NFFH), a guided discussion of implementation trade-offs and failure cases, and compact notes covering the whole discussion.

The Architecture Exploration and ADRs skill was used. The requirements source, `NFFH(1).txt`, was read completely earlier in this conversation: system description and user stories 1–41. These notes summarize the discussion, not a verbatim transcript. They describe proposed behavior, not an implemented or tested system.

## 2. Requirements and logical responsibilities

| Responsibility | Requirements evidence | Architectural relevance |
|---|---|---|
| Accounts and access | Customer and company registration; login, persistent sessions, logout, profiles; administrator access (stories 1–5, 17–24) | Authentication, authorization and account lifecycle |
| Farm discovery | Seasonal products, farms by area, products by farm, Google Maps directions (6–8, 13) | Catalog, farm and area data; a maps link suffices for the stated story |
| Cart and ordering | Add/remove/view cart, complete order with pickup date, view customer/farmer orders (9–12, 40–41) | Checkout coordination and order history |
| Products and inventory | Farmers add/remove products and change prices and quantities (14–16) | Ownership, validation and concurrent stock changes |
| Administration | Manage users, products and areas; inspect orders, companies and their distribution (25–39) | Privileged operations using authoritative business rules |

Logical responsibilities do not dictate deployment boundaries. Accounts, farm/area information, Catalog/Inventory, Cart and Ordering may be modules in one application or capabilities separated into services. Administration need not own a second copy of their business data.

Payments, delivery, notifications, pickup-capacity limits and recommendation algorithms are not stated requirements. Their absence from the document does not establish a permanent prohibition.

## 3. Working assumptions and proposed policies

| Classification | Statement | Status and effect |
|---|---|---|
| User-proposed policy | Fail the whole checkout when an item is unavailable; let the customer review the cart rather than silently placing a partial order | Working all-or-nothing checkout policy; not in original requirements |
| User-confirmed consequence | Stock reserved for available items must be restored if that checkout fails | Required consequence of the proposed policy |
| Illustrative assumption | Successful checkout reserves quantities, preventing the same available stock from being promised twice | Used for concurrency examples; exact stock lifecycle still needs specification |
| User-proposed working assumption | One small team initially deploys the backend together | Supports a single deployment; not a stated project constraint |
| User-proposed policy | Suspension should block price changes once it takes effect | Suspension and its effective timing require confirmation |
| Assistant-proposed outage behavior | Temporarily reject price updates when current account status cannot be established | Follows the proposed suspension policy; user has not separately accepted this outage choice |

Multi-farm cart support was used as a hypothetical scenario, not established as a requirement. No one-farm-per-cart restriction was agreed in this discussion.

## 4. Three architectural proposals

### A. Modular monolith with one relational database

One backend is deployed together, with internal interfaces separating the logical responsibilities. One relational database stores authoritative business data. Module boundaries still require discipline; shared storage is not permission for arbitrary cross-module writes.

Ordering coordinates checkout through ordinary in-process calls. Stock updates, order creation and durable retry information use one explicit database transaction.

Benefits:
- Local atomicity for checkout.
- A comparatively direct development, deployment and debugging path for one team.
- Managed hosting and a managed database can reduce infrastructure work.

Costs:
- Coordinated backend releases.
- Shared database capacity and potential interference between workloads.
- Process-level failures may affect several capabilities.
- Module boundaries and resource limits require deliberate enforcement.

Managed hosting is compatible with this design; monolithic deployment does not imply maintaining a server manually.

### B. Independently deployed services with separately owned databases

One possible split is Accounts, Discovery/Catalog, Inventory and Ordering, with Cart owned by Ordering. Each service owns its data and exposes APIs. Other services do not directly read its database.

Ordering durably records a checkout attempt, requests a reservation from Inventory, and records the eventual order outcome. Each database commits independently.

Benefits:
- Independent capability releases and operation.
- Selected workloads can scale separately.
- Deployment, resource and security isolation where the dependency design supports it.

Costs:
- Cross-service partial failures, uncertain timeouts and recovery.
- Durable coordination, idempotency and reconciliation.
- More complex authorization, diagnostics and operations.
- Isolation is weakened if checkout synchronously depends on the failing capability.

A multi-step reservation protocol can recover toward an all-or-nothing business outcome, but it does not provide instantaneous cross-database atomicity. Temporary holds and pending states may remain visible during recovery. The full protocol was not finalized.

### C. Managed authentication, backend functions and a managed relational database

Managed authentication establishes identity. Stateless backend functions execute application logic against one shared managed relational database. Logical module boundaries remain useful.

One checkout invocation owns the entire checkout transaction. Separate function invocations do not automatically share a transaction, and in-memory state cannot be relied on after termination.

Benefits:
- Provider-managed invocation scheduling, instance lifecycle and scaling within configured limits.
- Potential value from platform integrations, triggers and existing team expertise.
- Possible advantages for intermittent workloads, subject to evidence.

Costs:
- Execution and platform limits.
- Aggregate database connection pressure.
- Persistent recovery state and explicit application authorization remain necessary.
- Provider dependence and a different debugging/deployment workflow.

Hosting/execution and decomposition are separate axes: services or a modular monolith can also use managed infrastructure.

## 5. Checkout responsibilities

Ordering coordinates:
1. Accounts: identify the customer and establish permission.
2. Cart: obtain intended items and quantities.
3. Catalog/Inventory: determine valid products, current prices, availability and stock effects.
4. Farm information: identify pickup farms and validate any adopted pickup rules.
5. Ordering itself: validate the pickup selection, calculate totals and save the order.

Discovery screens, Google Maps and administrator screens do not need to participate directly. Specific pickup rules and price-change acceptance remain open.

Order lines should preserve agreed descriptions, prices and quantities so later catalog edits do not rewrite historical orders.

## 6. Single-database checkout: concurrency and crashes

A transaction must explicitly include all relevant writes, using the same transaction context/connection. No participating module commits independently.

Conceptual sequence:

```text
BEGIN
  Claim the customer-scoped checkout key
  Validate checkout and perform guarded stock changes
  Save the order and its lines
  Save the durable result or reference to that order
COMMIT
```

Checking availability before writing is insufficient: two requests may both read the last available unit. A conditional stock update can enforce sufficient availability, with the affected-row count checked. Alternatively, suitable row locking can protect the operation. Multi-item failure rolls back all changes under the proposed policy.

If order creation fails, roll back. If the application crashes before commit, the database aborts the uncommitted transaction after detecting connection loss or a timeout. Application cleanup code is not required for that rollback; locks can remain until detection.

If the application crashes after commit, the order and stock effects remain durable. A lost response must be handled through result recovery, not by assuming the transaction failed.

## 7. Lost responses and simultaneous retries

The user proposed a stable checkout key saved with the order in the same transaction.

Enforce database uniqueness on `(customer_id, checkout_key)`. An application-level “does this key exist?” check alone has a race.

- Claim the key before changing stock within the checkout transaction.
- Persist a fingerprint of the immutable checkout contents.
- Commit the key, stock effects, order and result/reference together.
- A competing same-key request cannot independently claim the key.
- After the winner commits, the competing request retrieves the existing result using a fresh statement/transaction as required by database conflict handling.
- If the winner rolls back, its key claim and stock effects disappear, allowing another request to proceed.
- Same key with different products, quantities or pickup details produces a conflict.
- A waiting timeout leaves the outcome uncertain; retain the same key for retry or status lookup.

This prevents repeated effects for the same retained key. It does not automatically deduplicate attempts using different keys. Key retention and any stronger business-level uniqueness rule still require definition.

## 8. Separate-service recovery

The user recognized that Inventory and Ordering databases commit independently.

Before contacting Inventory, Ordering persists:
- Customer-scoped checkout key.
- Checkout contents/fingerprint.
- Stable reservation operation ID.
- Pending workflow state.

Inventory persists the reservation ID, matching contents and status atomically with the stock changes, enforcing uniqueness on the ID.

If Inventory reserves stock and Ordering crashes before saving the reply:
1. A recovery worker finds the pending attempt.
2. Ordering queries Inventory or retries with the same reservation ID.
3. Inventory returns the recorded reservation instead of reserving again.
4. Ordering records the order/outcome locally.

The worker ensures recovery does not depend on a customer retry. A timeout is an unknown outcome, not proof of failure. Generating a new reservation ID on recovery could reserve twice.

### Abandonment and release timeouts

Ordering durably saves `RELEASE_PENDING` before requesting release. Its worker keeps querying/retrying the same reservation until the authoritative outcome is known.

Inventory performs one local transaction:
- Conditionally transition `HELD → RELEASED`.
- Restore quantities only when that transition succeeds.

Concurrent releases use a conditional update or row lock. Repeated release of an already released reservation returns the recorded outcome without restoring stock again. A crash before commit rolls back both changes; after commit, both remain saved.

This provides an exactly-once stock effect through idempotent handling, not exactly-once network delivery. Eventual release assumes Inventory recovers and retries continue.

Confirmation, release and expiry must have mutually exclusive transitions. The question “What if release arrives after confirmation?” was raised but not resolved. Temporary hold expiry was discussed as a possible mechanism, not an adopted requirement.

## 9. Farmer price changes and authorization

Identity alone is insufficient. The backend must verify:
- Permission to manage products.
- Ownership by the farmer's agricultural company.
- Product existence and eligibility for editing.
- Valid price amount, currency and precision under agreed rules.
- Product version where preventing overwritten concurrent edits is required.

The authenticated identity comes from the session/token, not a browser-supplied owner ID. Ownership/status checks must remain valid when the write executes, for example through transactional or conditional updates.

The user proposed blocking changes after suspension takes effect. An unexpired token may still reflect authorization issued before suspension.

For a separate Accounts service, the assistant proposed temporarily rejecting the update if current account status cannot be established. This sacrifices update availability during an Accounts outage. It should be reported as a temporary service problem, not as evidence the farmer is suspended.

A live check still leaves a race between authorization and the write. The business must define whether suspension blocks requests authorized afterward or also stops previously authorized writes from committing afterward. The latter requires stronger coordination.

## 10. Managed functions: resource limits and operating value

Hypothetical example: 500 checkout invocations start while the database permits 100 connections. These numbers are illustrative, not measured NFFH workload.

The user proposed:
- Bound checkout concurrency.
- Cap connections across all function instances.
- Leave database capacity for other work.
- Queue or reject excess requests with controlled retries.
- Use pooling to reuse connections, recognizing that it cannot increase database throughput.

Any asynchronous acceptance requires durable work and a way to retrieve the result; queueing and retry behavior must preserve the stable checkout identity.

Functions need a demonstrated benefit over a managed monolith:
- Lower operational effort for tasks the application host otherwise leaves to the team.
- Lower total cost under the expected workload.
- Useful managed triggers/jobs and reliable retry support.
- Faster delivery from existing team expertise and integrations.

No provider was selected, pricing compared, traffic measured or platform limits verified. Automatic scaling alone does not establish superiority. A managed monolith already removes significant infrastructure work.

## 11. Final comparison

| Driver | Modular monolith on managed hosting | Independent services | Managed function application |
|---|---|---|---|
| Checkout correctness | One explicit local transaction can commit stock, order and retry result atomically | Durable coordination and reconciliation across independent commits | Same local guarantee when one invocation owns one database transaction |
| Initial team assumption | Fits one small team deploying together | Independence benefit not established for this team | Viable if platform expertise/integrations justify it |
| Failure handling | Transaction rollback plus durable idempotency | Pending attempts, stable reservation IDs and idempotent recovery | Transaction/idempotency plus invocation termination and resource-limit handling |
| Deployment/scaling | Coordinated release; shared resource pressure | Independent capability deployment/scaling | Platform-managed invocation scaling constrained by downstream capacity |
| Operational cost | Managed hosting reduces infrastructure work; application operations remain | More services, contracts and distributed diagnostics | Potential operational savings; provider constraints and connection management |
| Evidence gaps | Workload, service targets, budget and team skills | Concrete need for isolation/autonomy and full checkout protocol | Measured cost, effort, delivery advantage and provider fit |

Comparisons are qualitative design judgments, not benchmark or cost findings.

## 12. Provisional recommendation and rationale

Recommend a modular monolith on managed hosting with one managed relational database for the initial version.

Rationale:
- One small team deploying together is the user's explicit working assumption.
- The proposed all-or-nothing checkout policy benefits from one local transaction.
- Stock changes, order creation, checkout identity and durable result can commit together.
- Current requirements do not establish a need for independently deployed capabilities.
- Managed functions have not demonstrated enough additional operational, cost or delivery benefit over managed application hosting.

Trade-offs retained:
- Shared deployment and database capacity.
- Need for module discipline, bounded connections, monitoring, backups/recovery configuration and application authorization.
- Provider and hosting selection still require operational evidence.

The user summarized and retained this provisional recommendation, and explicitly stated Task 1 was complete at the architecture-selection level. No explicit final acceptance or implementation approval was recorded. Recommendation/ADR status therefore remains Proposed.

## 13. Concrete reconsideration triggers

The user identified:
1. Separate teams repeatedly blocked by coordinated releases.
2. Measured workloads requiring independent scaling.
3. Security or availability requirements demanding deployment isolation.
4. Evidence that functions reduce total cost, operational effort or delivery time.

Other illustrative scenarios discussed were Inventory serving farm terminals/external partners and discovery failures needing isolation from checkout. These are possible future needs, not current requirements.

More users alone does not prove a service split is necessary. Diagnose the bottleneck and assess narrower improvements first. Prefer changing the boundary under demonstrated pressure rather than migrating the entire system automatically.

## 14. Remaining implementation questions and completion

Task 1 is complete at architecture-selection level: three alternatives explored, critical implementation trade-offs discussed, provisional architecture recommended, and reconsideration triggers stated.

Current implementation questions:
- Multi-farm carts, order grouping and pickup representation.
- Exact stock lifecycle, cancellations and price-change acceptance.
- Pickup-date rules and historical deletion/archive behavior.
- Suspension semantics, authorization freshness and race handling.
- Checkout-key retention and cross-key duplicate policy.
- Workload, availability targets, budget, platform expertise and operational validation.

Questions relevant if separate service databases are introduced:
- Complete confirmation/release/expiry state machine.
- Release after confirmation and stale competing recovery actions.
- Full protocol for eventual all-or-nothing outcomes, pending customer experience and reconciliation.

No ADR was created in this conversation. Task 2 would document this rationale, alternatives, consequences, assumptions, open questions and triggers in a Proposed ADR. No implementation, deployment, runtime test or provider-specific evaluation was completed.

