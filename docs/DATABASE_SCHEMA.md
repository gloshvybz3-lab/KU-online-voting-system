# Production database schema

The MVP keeps the current relational model because its ballot-secrecy boundary is strong and understandable.

```text
university_records

admins ──< student account registration ──> students

admins ──< elections ──< positions ──< candidates
                     │          │
                     │          └──< votes (anonymous ballot rows)
                     └──< eligibility_rules

students ──< voter_participation >── elections

admins ──< audit_logs
admins ──< notifications
```

## Core tables

| Table | Purpose | Critical keys/indexes |
|---|---|---|
| `university_records` | Registrar source of truth | unique `student_id`, `reg_no`, `email` |
| `students` | Authenticated voters | unique student/reg/email; campus/faculty indexes |
| `admins` | EC officials and administrators | unique username/email; role |
| `elections` | Election lifecycle and schedule | status + start/end index; created_by |
| `positions` | Offices contested within an election | election + priority index |
| `candidates` | Candidate profiles | election + position + status index |
| `eligibility_rules` | Position voter eligibility | election/position foreign keys |
| `voter_participation` | Proof a voter has voted | unique `(election_id, student_id)` |
| `votes` | Anonymous ballot choices | **no student identifier**; election/position index |
| `notifications` | In-app announcements | created_by |
| `audit_logs` | Security/admin audit trail | created_at/action index |
| `faqs` | Help content | active + priority |

## Ballot secrecy invariant

Never add `student_id`, `user_id`, `receipt_token`, IP address, session ID, or another voter-correlating field to `votes`. `voter_participation` and `votes` must remain operationally and logically decoupled.

## Scaling recommendations

- MySQL/InnoDB for the primary transactional store.
- Read replicas for reporting and result dashboards.
- Redis for rate limiting, cache and background-job coordination.
- Object storage for candidate photos/symbols.
- Partition/archival strategy for `votes`, `audit_logs`, and notifications when volume becomes very large.
- Use migrations; never mutate production schema from a web worker.
