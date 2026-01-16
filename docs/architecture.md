# OmniLife Multi-Agent Orchestrator - Architecture Documentation

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Chat UI<br/>index.html]
    end
    
    subgraph "API Layer"
        API[Django REST API<br/>/api/]
        API --> |POST /chat/| CHAT[ChatView]
        API --> |GET /customers/| CUST[CustomerListView]
        API --> |GET /health/| HEALTH[HealthCheckView]
    end
    
    subgraph "Orchestration Layer"
        ORCH[Super Agent<br/>LangGraph Orchestrator]
        CACHE[Intent Cache<br/>LRU + TTL]
        REASON[Reasoning Chain<br/>Chain-of-Thought]
    end
    
    subgraph "Agent Layer"
        SC[ShopCore Agent<br/>Orders, Products]
        SS[ShipStream Agent<br/>Shipping, Tracking]
        PG[PayGuard Agent<br/>Payments, Refunds]
        CD[CareDesk Agent<br/>Tickets, Support]
    end
    
    subgraph "Database Layer"
        DB1[(DB_ShopCore<br/>Users, Products, Orders)]
        DB2[(DB_ShipStream<br/>Shipments, Warehouses)]
        DB3[(DB_PayGuard<br/>Wallets, Transactions)]
        DB4[(DB_CareDesk<br/>Tickets, Messages)]
    end
    
    UI --> API
    CHAT --> ORCH
    ORCH --> CACHE
    ORCH --> REASON
    ORCH --> SC & SS & PG & CD
    SC --> DB1
    SS --> DB2
    PG --> DB3
    CD --> DB4
```

---

## Component Architecture

```mermaid
graph LR
    subgraph "apps/orchestrator/"
        G[graph.py<br/>LangGraph Workflow]
        N[nodes.py<br/>Graph Nodes]
        S[state.py<br/>State Machine]
        C[cache.py<br/>Intent Caching]
        R[reasoning.py<br/>Chain-of-Thought]
        T[tools.py<br/>MCP Tools]
        CTX[context.py<br/>Context Management]
    end
    
    G --> N
    N --> S
    N --> C
    N --> R
    N --> T
```

---

## State Machine Architecture

```mermaid
stateDiagram-v2
    [*] --> LISTENING: Session Start
    
    LISTENING --> ROUTING: Query Received
    note right of ROUTING: Analyze intent, extract entities
    
    ROUTING --> EXECUTING: Plan Created
    note right of EXECUTING: Run agents in parallel batches
    
    EXECUTING --> ANSWERING: Data Collected
    note right of ANSWERING: Synthesize response
    
    ANSWERING --> COMPLETE: Response Ready
    
    ROUTING --> ERROR: Analysis Failed
    EXECUTING --> ERROR: Agent Failed
    ERROR --> COMPLETE: Fallback Response
    
    COMPLETE --> [*]
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, JavaScript |
| API | Django REST Framework |
| Orchestration | LangGraph + LangChain |
| LLM | GitHub Models API (GPT-4.1) |
| Database | SQLite (Django ORM) |
| Caching | In-memory LRU |

---

## File Structure

```
Omni-Retail-Multi-Agent-Orchestrator/
├── api/                    # REST API
│   ├── views.py           # API endpoints
│   ├── serializers.py     # Request/response schemas
│   └── urls.py            # URL routing
├── apps/
│   ├── core/              # Shared utilities
│   ├── orchestrator/      # Super Agent
│   │   ├── graph.py       # LangGraph workflow
│   │   ├── nodes.py       # Graph nodes
│   │   ├── state.py       # State machine
│   │   ├── cache.py       # Intent caching
│   │   ├── reasoning.py   # Chain-of-thought
│   │   └── tools.py       # MCP tools
│   ├── shopcore/          # E-commerce agent
│   ├── shipstream/        # Logistics agent
│   ├── payguard/          # Payment agent
│   └── caredesk/          # Support agent
├── config/                # Django settings
├── templates/             # HTML templates
└── scripts/               # Utility scripts
```
