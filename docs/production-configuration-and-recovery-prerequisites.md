# Production Configuration and Recovery Prerequisites

**Author:** Manus AI

## Implemented configuration safeguards

Settings validation now rejects development-prefixed session secrets and non-HTTPS CORS origins in both staging and production. This closes the prior staging gap, where cookies were marked secure but a development secret or an HTTP browser origin could still be configured. Development and test retain their explicit local defaults so isolated developer and test workflows continue to function.

Production retains its stricter existing gates: secure cookies, a non-local private object-storage root, and a shared rate-limit backend selection are mandatory. Selecting a shared backend still does not activate one; application composition requires an injected provider implementation, and managed private storage remains unimplemented. These are deliberate startup/configuration gates, not claims of deployed distributed controls.

| Environment | Session secret | CORS origins | Storage boundary | Rate-limit boundary |
|---|---|---|---|---|
| Development | Local development placeholder permitted | Explicit HTTP localhost permitted | Local private adapter permitted | Local in-memory backend permitted |
| Test | Test-only value permitted | Explicit test origin permitted | Isolated temporary/private test storage | Local in-memory backend permitted |
| Staging | Development prefix rejected | HTTPS only | No additional production storage assertion in this phase | Local fallback remains a deliberate staging deployment decision |
| Production | Development prefix rejected | HTTPS only | Local root rejected; managed adapter required | Local backend rejected; shared provider factory required |

## Backup and recovery prerequisites

No backup, restore, point-in-time recovery, replica, or deletion-index capability is implemented or implied by this repository. The application readiness endpoint remains intentionally limited to database connectivity; it must not be interpreted as proof of recoverability or backup health.

Before production launch, the responsible operations, security, and privacy owners must approve and document the backup inventory, database point-in-time recovery and object-storage recovery approach, encryption, key management, regional residency, access roles, retention windows, restore testing cadence, recovery objectives, recovery environments, and escalation paths. Exact RPO, RTO, and retention values are business and operational decisions and are not invented here.

A recovery plan must include an isolated restore drill and a restore guard that prevents completed live-data deletions from being silently reintroduced by restored database or object snapshots. The strategy in `docs/privacy-data-lifecycle-strategy.md` remains authoritative: no destructive lifecycle timer, backup purge, account-erasure flow, legal hold, or restore guard is activated until the policy and provider design are approved.

## Verification and limits

Focused configuration tests prove the staging and production secret/CORS rejection behavior. This change introduces no migration, database schema change, storage provider, backup process, or secret value. Deployment operators must provide real values only through an approved secret-management mechanism and must not commit them to tracked configuration files.
