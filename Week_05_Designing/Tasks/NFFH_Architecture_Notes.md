# Not Far(m) From Home — Architecture Discussion Notes

Compact record of our discussion, 29 October 2026.
Source: the complete uploaded NFFH.txt, containing the system description and 41 user stories.
These notes summarize the discussion rather than reproduce it verbatim. Proposed assumptions remain distinct from documented requirements.

## 1. System scope and responsibilities

NFFH connects consumers with local farms. Farmers publish produce; customers reserve products and choose a pickup date at the farm.

| Responsibility | Main capabilities | User stories |
|---|---|---|
| Accounts and access | Registration, login, persistent authentication, logout, profiles, administrator user management | 1–5, 17–25, 27–29 |
| Farms and areas | Farms by area, farm details, Google Maps location links, area maintenance | 7, 13, 30–32, 35, 39 |
| Catalog and inventory | Seasonal products, farm products, prices, quantities, product maintenance | 6, 8, 14–16, 33–34, 36–38 |
| Shopping cart | Add, remove, view selected products | 9–11 |
| Orders and pickup | Checkout, pickup date, customer/farmer/admin order views | 12, 26, 40–41 |

These are logical boundaries, not necessarily separate services. Administration spans the domains and should reuse their rules. Catalog and inventory can initially remain together.

Online payment, delivery, notifications, automatic geolocation, and pickup-capacity scheduling are not explicitly required.

## 2. Assumptions and unresolved questions

Proposed baseline:
- One farm per cart; this was suggested, not explicitly confirmed by the user.
- Adding products to the cart does not reserve stock. Successful checkout does.
- All-or-nothing checkout: insufficient quantity for any item means no confirmed order and no committed stock reduction. The customer adjusts the cart and retries.
- Preserve order history when products are removed, for example by archiving products and storing order-line snapshots.
- Areas are maintained categories; distance-based search is an optional extension.

Still unspecified: inventory units and precision; valid pickup dates/opening days/timezones; seasonal-product selection; cancellation and fulfillment rules; user deletion semantics; traffic, budget, team size, and availability targets.

## 3. Architecture A — Modular monolith

One backend application contains business modules and uses one relational database. Modules communicate through function calls. The application can run as multiple instances.

Orders owns checkout policy and coordination. Inventory owns stock validation and reservation rules. A cart expresses intent; an order records a successful reservation.

### Shared checkout transaction

The checkout application service starts one transaction/unit of work and passes its context to Cart, Inventory, and Orders. All operations use the same transaction-bound connection/session. Inner modules neither commit independently nor open unrelated transactions.

Example: Inventory reduces tomatoes, then discovers insufficient potatoes. It raises an insufficient-stock error. That error exits the transaction scope, causing rollback of the tomato reduction and any order writes. The failure response is produced after rollback.

The transaction infrastructure is shared, but modules still modify only their own tables.

### Correctness details

- Use row locks or conditional stock updates; an earlier availability read cannot guarantee stock remains available.
- Example building block: update stock only where available quantity is at least the requested quantity, then check the affected-row count.
- Handle the whole cart in one transaction and roll back if any line fails.
- Acquire multiple inventory locks in a consistent order to reduce deadlock risk.
- Calculate authoritative totals server-side; store price, unit, and relevant product-description snapshots on order lines.
- Use checkout idempotency keys and uniqueness constraints to prevent duplicate orders after retries.
- Validate ownership and permissions on the backend.

Benefits: straightforward atomic checkout, easier debugging/testing, fewer operational components.
Costs: shared deployment and scaling; application failures can affect several features; internal boundaries need discipline.

## 4. Architecture B — Independent services

Proposed services:
- Accounts: identities, profiles, roles, authentication.
- Catalog/Inventory: farms, areas, products, prices, stock, reservations.
- Ordering: carts, checkout attempts, orders, pickup dates.

Each owns its database. Services use APIs or messages, not direct reads/writes of each other's tables. Independent ownership can exist even when databases share physical infrastructure.

Inventory reserves the complete requested item list in one local transaction. Orders cannot extend that transaction across its separate database.

### Partial failure and recovery

If Inventory commits a reservation and Ordering crashes before saving an order, stock can become held without an order.

Proposed workflow:
1. Ordering durably records the checkout attempt and stable reservation ID before contacting Inventory.
2. Inventory creates an all-or-nothing temporary reservation with an expiry.
3. Ordering saves a pending order and requests reservation confirmation.
4. Inventory atomically confirms a live reservation or reports expiry/release.
5. Ordering marks the order confirmed only after authoritative confirmation.

Inventory owns expiry cleanup, so abandoned holds can be released even while Ordering is down. Confirmation and expiry must be mutually exclusive transitions. Confirmed reservations are no longer subject to temporary-hold expiry.

This is a distributed workflow/saga: local transactions plus explicit recovery, rather than one cross-module rollback.

### Timeouts mean uncertainty

If confirmation times out, Inventory may already have confirmed it. Ordering keeps durable pending state, retries the same idempotent operation or queries status, and reconciles after restart.

| Inventory outcome | Ordering action |
|---|---|
| Confirmed for this order | Finish confirming the order |
| Held and unexpired | Retry confirmation |
| Expired/released | Fail checkout |
| Unreachable | Remain pending; retry with backoff |

Do not create another reservation or report definite failure simply because a request timed out. Customers see a pending confirmation state.

### Duplicate checkout protection

The frontend generates and preserves one idempotency key per business attempt, reusing it on retries.

Ordering stores customer ID, key, cart version/payload fingerprint, checkout/order ID, reservation ID, and status. A unique constraint on customer ID plus key handles simultaneous retries.

- Pending retry: return the same attempt/status.
- Completed retry: return the existing result.
- Same key with changed contents: reject.
- Different keys from separate tabs: an additional one-active-checkout-per-cart-version rule can prevent duplicates.

Inventory also enforces unique reservation IDs and matching request contents. Reservation records and stock changes are committed atomically.

Recovery workers resume interrupted attempts. Durable work records or a transactional outbox avoid losing follow-up work; repeated messages still require idempotent handling.

### Authorization without Accounts database access

Catalog validates a signed token's identity, issuer, audience, signature, and expiry. It checks product-to-farm and farm-to-owner relationships in its own database.

A farmer role alone does not prove product ownership. Never trust a user ID supplied in the request body as the caller identity. Prevent ownership changes racing with updates through appropriate local transaction/locking rules.

Proposed policy for farmer price/inventory writes: require a live account-status check and fail closed with a temporary 503 response if Accounts is unavailable. Public browsing can continue. This creates runtime dependence on Accounts.

The guarantee is active status at authorization time, not instantaneous enforcement against a suspension that happens immediately afterward.

Benefits: independent team ownership, deployments, scaling, and potentially stronger failure isolation.
Costs: network failures, recovery states, API evolution, cross-service administration views, correlation/logging, and operational complexity.

## 5. Architecture C — Managed serverless

Hosted frontend + managed identity + backend functions + one managed relational application database.

The provider runs infrastructure and function execution. We still implement authorization, validation, schema, indexes, business rules, transactions, idempotency, and recovery. Operational configuration such as backup retention remains a deliberate choice.

One checkout function calls shared Inventory/Orders code inside one database transaction, or invokes one transactional database routine. Module boundaries do not require separate function invocations.

Independent function calls do not automatically share a transaction. Splitting stock and order writes across them would reintroduce distributed consistency problems.

If execution stops before commit, an uncommitted transaction rolls back once the database detects connection termination or a timeout; locks may persist until cleanup. If commit succeeds but the response is lost, retrying the same key returns the saved order.

Persistent state belongs in the database, not function memory. Browser code must never receive privileged database credentials.

### Connection limits and backpressure

Example: 500 checkout functions versus 100 database connections.

- Use a shared pool/proxy with a bounded database-facing connection count.
- Limit checkout execution concurrency and waiting time.
- Reserve capacity for other operations; 70 checkout connections and 30 for other uses was illustrative, not a measured configuration.
- Small per-instance pools alone are insufficient: their limits multiply across instances.
- Keep transactions short; avoid waiting on external services while holding a transaction open.
- Set connection-acquisition, transaction, and lock timeouts.
- Use retry backoff with jitter and stable idempotency keys.
- Monitor database throughput, connection utilization, and waiting.

A proxy cannot provide unlimited database throughput. Excess work must wait within limits or receive a retryable busy response. A durable queue is possible but introduces asynchronous checkout.

Other costs: startup latency, execution limits, platform-specific tooling, local reproduction challenges, and provider dependence.

## 6. Comparison and provisional recommendation

| Option | Checkout consistency | Main attraction | Main cost |
|---|---|---|---|
| Modular monolith | One database transaction | Simple implementation and operation | Shared deployment/scaling |
| Independent services | Local transactions plus reservation/recovery workflow | Independent ownership and deployment | Distributed failures and reconciliation |
| Managed serverless | One database transaction if kept within one checkout operation | Managed execution infrastructure | Resource limits and platform dependence |

Logical decomposition and hosting are separate choices. A modular monolith can also use managed authentication, a managed database, and managed hosting. Serverless does not inherently mean microservices.

Provisional recommendation: a modular monolith on managed hosting, with a relational database and clear internal boundaries. No final implementation or platform was selected.

Serverless could be preferable for a team familiar with its platform that values its operational workflow and has suitable usage patterns. The requirements alone do not establish that advantage; no cost or performance measurements were made.

Independent services become more defensible when:
- Several teams demonstrably need independent releases and operation.
- Inventory becomes an independent authority for multiple sales channels or partners.
- Measured workloads require separate scaling.
- Explicit failure-isolation, security, or infrastructure boundaries are required.

Extract only what the pressure justifies. Catalog browsing could be separated while order creation and stock reservation remain together. Speculative growth alone does not justify distributing checkout.
