# InkosAI API Documentation

Complete API reference for InkosAI.

## Base URL

```
Development: http://localhost:8000/api
Production:  https://api.inkos.ai/api
```

## Authentication

Most endpoints require authentication via Bearer token:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# Use token in subsequent requests
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbG..."
```

### Token Response

```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "dGhpcyBpcyBh..."
}
```

## Health & Monitoring

### Get Health Status

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "inkosai-api",
  "version": "0.1.0"
}
```

### Get Readiness

```
GET /ready
```

Kubernetes readiness probe. Returns 200 when dependencies are healthy.

### Get Liveness

```
GET /live
```

Kubernetes liveness probe. Returns 200 if process is running.

### Get Detailed Health

```
GET /health/detailed
```

Response:
```json
{
  "status": "healthy",
  "service": "inkosai-api",
  "version": "0.1.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 1.23,
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 0.45,
      "message": "Redis connection successful"
    }
  }
}
```

### Get Prometheus Metrics

```
GET /metrics
```

Returns Prometheus-formatted metrics.

## Authentication Endpoints

### Register User

```
POST /auth/register
```

Request:
```json
{
  "username": "newuser",
  "password": "securepassword123",
  "email": "user@example.com",
  "role": "viewer"
}
```

### Login

```
POST /auth/login
```

Request:
```json
{
  "username": "admin",
  "password": "password123"
}
```

### Refresh Token

```
POST /auth/refresh
```

Request:
```json
{
  "refresh_token": "dGhpcyBpcyBh..."
}
```

### Logout

```
POST /auth/logout
```

Requires: Bearer token

### Get Current User

```
GET /auth/me
```

Requires: Bearer token

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Change Password

```
POST /auth/change-password
```

Requires: Bearer token

Request:
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword123"
}
```

### List Users (admin only)

```
GET /auth/users
```

Requires: Admin role

### Change User Role (admin only)

```
PATCH /auth/users/{username}/role
```

Requires: Admin role

Request:
```json
{
  "role": "operator"
}
```

### Deactivate User (admin only)

```
DELETE /auth/users/{username}
```

Requires: Admin role

## Domains

### Create Domain

```
POST /domains
```

Requires: Bearer token

Request:
```json
{
  "name": "My Domain",
  "type": "custom",
  "description": "A custom domain",
  "template": "starter"
}
```

Response:
```json
{
  "id": "domain-123",
  "name": "My Domain",
  "type": "custom",
  "created_at": "2024-01-15T10:30:00Z",
  "folder_path": "/domains/my-domain"
}
```

### List Domains

```
GET /domains
```

Requires: Bearer token

Response:
```json
{
  "domains": [
    {
      "id": "domain-123",
      "name": "My Domain",
      "type": "custom"
    }
  ]
}
```

### Get Domain

```
GET /domains/{domain_id}
```

Requires: Bearer token

### Update Domain

```
PATCH /domains/{domain_id}
```

Requires: Bearer token

### Delete Domain

```
DELETE /domains/{domain_id}
```

Requires: Bearer token

## Canvas

### Get Canvas State

```
GET /canvas/{domain_id}
```

Requires: Bearer token

Response:
```json
{
  "nodes": [
    {
      "id": "node-1",
      "type": "browser",
      "position": {"x": 100, "y": 100},
      "data": {"url": "https://example.com"}
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-1",
      "target": "node-2"
    }
  ]
}
```

### Update Canvas

```
POST /canvas/{domain_id}
```

Requires: Bearer token

Request:
```json
{
  "nodes": [...],
  "edges": [...]
}
```

### Create Node

```
POST /canvas/{domain_id}/nodes
```

Requires: Bearer token

Request:
```json
{
  "type": "terminal",
  "position": {"x": 200, "y": 200},
  "data": {...}
}
```

## Swarm Mode

### Start Swarm

```
POST /domains/{domain_id}/swarm
```

Requires: Bearer token

Request:
```json
{
  "mode": "quick",  // or "governed"
  "task": "Create a landing page",
  "agents": ["frontend", "backend"]
}
```

Response:
```json
{
  "swarm_id": "swarm-456",
  "status": "running",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Get Swarm Status

```
GET /domains/{domain_id}/swarm/{swarm_id}
```

Requires: Bearer token

### Multi-Domain Swarm

```
POST /swarm/multi-domain
```

Requires: Bearer token

Request:
```json
{
  "domains": ["domain-1", "domain-2"],
  "task": "Create cross-domain integration",
  "mode": "governed"
}
```

## Planning Domains

### Create Planning Domain

```
POST /planning/domains
```

Requires: Bearer token

Request:
```json
{
  "name": "My Planning Domain",
  "participants": ["agent1@domain1", "agent2@domain2"],
  "workflow_type": "collaborative"
}
```

### Execute Planning

```
POST /planning/domains/{domain_id}/execute
```

Requires: Bearer token

Request:
```json
{
  "objective": "Plan feature rollout",
  "constraints": ["deadline: 2024-02-01"]
}
```

## Plugins

### List Available Plugins

```
GET /plugins
```

Requires: Bearer token

### Install Plugin

```
POST /plugins/install
```

Requires: Bearer token, Admin role

Request:
```json
{
  "plugin_id": "plugin-123",
  "version": "1.0.0"
}
```

### Execute Plugin

```
POST /plugins/{plugin_id}/execute
```

Requires: Bearer token

Request:
```json
{
  "input": {"task": "Hello world"},
  "timeout": 30
}
```

### Get Plugin Status

```
GET /plugins/{plugin_id}/status
```

Requires: Bearer token

## AetherGit (Version Control)

### Create Commit

```
POST /aethergit/commit
```

Requires: Bearer token

Request:
```json
{
  "message": "Add new feature",
  "scope": "domains/my-domain",
  "author": "user@example.com"
}
```

### Get History

```
GET /aethergit/log?scope={domain_id}&limit=10
```

Requires: Bearer token

### Revert

```
POST /aethergit/revert
```

Requires: Bearer token

Request:
```json
{
  "commit_id": "abc123",
  "reason": "Revert buggy change"
}
```

## Tape (Audit Log)

### Query Tape

```
GET /tape/query?q=domain:my-domain&limit=50
```

Requires: Bearer token

Response:
```json
{
  "events": [
    {
      "id": "tape-123",
      "timestamp": "2024-01-15T10:30:00Z",
      "event_type": "domain.created",
      "agent_id": "user-123",
      "payload": {...}
    }
  ]
}
```

### Semantic Search

```
POST /tape/semantic-query
```

Requires: Bearer token

Request:
```json
{
  "query": "user login events from yesterday",
  "limit": 20
}
```

## Settings

### Get Settings

```
GET /settings
```

Requires: Bearer token

Response:
```json
{
  "ai_provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "system_prompt": "You are a helpful assistant..."
}
```

### Update Settings

```
PUT /settings
```

Requires: Bearer token

Request:
```json
{
  "ai_provider": "openai",
  "model": "gpt-4"
}
```

### Get LLM Models

```
GET /settings/models
```

Requires: Bearer token

## Prime (Meta-Agent)

### Chat with Prime

```
POST /prime/chat
```

Requires: Bearer token

Request:
```json
{
  "message": "Help me create a new domain",
  "context": {
    "current_domain": "my-domain",
    "canvas_selection": ["node-1"]
  }
}
```

Response:
```json
{
  "response": "I'd be happy to help you create a new domain. What type of domain would you like?",
  "suggestions": ["Web Application", "Data Pipeline", "API Service"],
  "actions": [
    {"type": "suggest_canvas_layout", "layout": "starter"}
  ]
}
```

### Generate Plan

```
POST /prime/plan
```

Requires: Bearer token

Request:
```json
{
  "objective": "Build a user authentication system",
  "constraints": ["use JWT", "include refresh tokens"]
}
```

## Profiles

### Get Profile

```
GET /profiles/{profile_id}
```

Requires: Bearer token

Response:
```json
{
  "id": "profile-123",
  "name": "Development Profile",
  "preferences": {...},
  "context_windows": [...]
}
```

### Create Profile

```
POST /profiles
```

Requires: Bearer token

### Update Profile

```
PATCH /profiles/{profile_id}
```

Requires: Bearer token

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "request_id": "abc123"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 413 | Request Too Large |
| 500 | Server Error |
| 503 | Service Unavailable |

## Rate Limits

- 120 requests per 60 seconds per IP
- Applies to all endpoints
- Returns 429 with `Retry-After` header when exceeded

## WebSockets

Real-time updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data); // { type: 'tape.event', event: {...} }
};
```

## SDK Examples

### Python

```python
import httpx

async with httpx.AsyncClient() as client:
    # Login
    resp = await client.post(
        "http://localhost:8000/api/auth/login",
        json={"username": "admin", "password": "password"}
    )
    token = resp.json()["access_token"]

    # Create domain
    resp = await client.post(
        "http://localhost:8000/api/domains",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "My Domain", "type": "custom"}
    )
    domain = resp.json()
```

### JavaScript

```javascript
// Login
const login = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'password' })
});
const { access_token } = await login.json();

// Create domain
const domain = await fetch('http://localhost:8000/api/domains', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ name: 'My Domain', type: 'custom' })
});
```
