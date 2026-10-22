# API v1

Base path: `/api/v1`

## Assistant

`POST /assistant/chat`

Request:
```json
{"message":"How do I vote?"}
```

Response:
```json
{
  "ok": true,
  "message": "Open My Ballot...",
  "links": [{"label":"How to vote","url":"/voting/elections"}]
}
```

The endpoint is read-only and rate limited. It deliberately uses application-owned knowledge so it cannot invent election state.

## Health

`GET /health`

Returns `{"status":"ok"}` for load balancer health checks.

## Recommended internal/admin API contract

For a future SPA/mobile client, use the following REST resources:

- `POST /api/v1/admin/elections`
- `GET /api/v1/admin/elections`
- `GET /api/v1/admin/elections/{id}`
- `PATCH /api/v1/admin/elections/{id}`
- `POST /api/v1/admin/elections/{id}/positions`
- `DELETE /api/v1/admin/elections/{id}/positions/{positionId}`
- `POST /api/v1/admin/elections/{id}/candidates`
- `PATCH /api/v1/admin/candidates/{candidateId}/status`
- `GET /api/v1/elections/{id}/ballot`
- `POST /api/v1/elections/{id}/ballot`
- `GET /api/v1/elections/{id}/results`
- `POST /api/v1/elections/{id}/publish`

All write endpoints should use idempotency keys for retry-safe clients and return a consistent envelope:

```json
{"ok":true,"data":{},"request_id":"..."}
```

Errors:

```json
{"ok":false,"error":{"code":"VALIDATION_ERROR","message":"..."},"request_id":"..."}
```
