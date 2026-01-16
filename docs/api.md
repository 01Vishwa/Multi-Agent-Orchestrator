# API Documentation

## Base URL
```
http://localhost:8000/api/
```

---

## Endpoints

### 1. Chat Endpoint

**POST** `/api/chat/`

Process a customer query through the multi-agent orchestrator.

#### Request Body
```json
{
    "message": "What are my recent orders?",
    "session_id": "optional-session-id",
    "user_id": "customer-uuid",
    "include_debug": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message | string | ✅ | Customer's natural language query |
| session_id | string | ❌ | Session ID for conversation continuity |
| user_id | string | ❌ | Customer ID for context |
| include_debug | boolean | ❌ | Include execution details |

#### Response
```json
{
    "response": "You have 3 recent orders...",
    "session_id": "sess_abc123",
    "agents_used": ["shopcore"],
    "success": true,
    "intent": "order_inquiry",
    "intent_confidence": 0.85,
    "execution_details": {
        "parallel_batches": [["shopcore"]],
        "agent_results": [...],
        "execution_times": {"analysis": 150, "shopcore": 2000}
    }
}
```

---

### 2. Customer List

**GET** `/api/customers/`

Get list of customers for frontend selector.

#### Response
```json
[
    {
        "id": "uuid",
        "name": "Jonathan Martinez",
        "email": "jonathan@example.com",
        "premium": true,
        "order_count": 7,
        "wallet": {"balance": "1734.62", "currency": "USD"}
    }
]
```

---

### 3. Health Check

**GET** `/api/health/`

Check system health and agent status.

#### Response
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "database": "healthy",
    "llm": "configured",
    "agents": {
        "shopcore": "ready",
        "shipstream": "ready",
        "payguard": "ready",
        "caredesk": "ready"
    },
    "timestamp": "2026-01-17T00:30:00Z"
}
```

---

### 4. Direct Agent Query

**POST** `/api/agents/query/`

Query a specific agent directly (for testing).

#### Request Body
```json
{
    "agent": "shopcore",
    "query": "Find orders for Gaming Monitor",
    "context": {}
}
```

---

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid request parameters |
| 500 | Internal server error |

```json
{
    "error": "Error message",
    "details": {...}
}
```

---

## Authentication

Currently using `AllowAny` permission for development. 
Production should implement token-based authentication.
