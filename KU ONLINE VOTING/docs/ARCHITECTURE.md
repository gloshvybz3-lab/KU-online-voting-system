# KU Online Voting — Production MVP Architecture

## Runtime architecture

```text
Students / EC Officials
        |
   CDN + WAF + TLS
        |
  Load Balancer
        |
+-------------------------+
| Stateless Flask API/Web |
| Gunicorn workers        |
+-------------------------+
   |       |        |
   |       |        +--> Object Storage/CDN (candidate media)
   |       +-----------> Redis (sessions/rate limits/cache/queues)
   +-------------------> MySQL/InnoDB primary
                           |
                           +--> Read replicas (results/reporting)

Background workers -> notifications, scheduled status changes, exports
Observability -> structured logs + metrics + traces + audit log
```

## Design principles

1. **Ballot secrecy is non-negotiable.** `voter_participation` proves that a student voted; `votes` contains no voter identifier or receipt token.
2. **All administrative writes go through application services.** Routes validate HTTP input; services enforce business invariants and transactions.
3. **Election hierarchy is validated server-side.** A candidate's `position_id` must belong to the submitted `election_id`.
4. **Stateless web workers.** Session state should move to Redis when horizontally scaling beyond one worker/host.
5. **MySQL is the source of truth.** SQLite is development/test only.
6. **Media is externalized.** Production candidate photos/symbols should use S3-compatible object storage, not the local filesystem.
7. **Background work is asynchronous.** Email/SMS/broadcasts should be queued instead of blocking vote/election transactions.
8. **Audit logs never record ballot selections.** Administrative and authentication events may be audited; vote contents must remain anonymous.

## Service boundaries for the next scaling stage

- `identity`: student/admin authentication and role management.
- `elections`: election lifecycle, positions, candidates and eligibility.
- `voting`: eligibility, ballot casting and participation receipts.
- `results`: tabulation, certification and publication.
- `notifications`: email/SMS/in-app delivery.
- `assistant`: read-only navigation/help assistant.

The current Flask application is a modular monolith. That is intentional for the MVP: it preserves transactional simplicity while keeping service boundaries explicit enough to extract later.
