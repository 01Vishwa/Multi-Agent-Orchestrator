# Module & Activity Diagrams

## 1. Module Hierarchy

```mermaid
graph TB
    subgraph "config/"
        CONFIG[settings/base.py]
        URLS[urls.py]
    end
    
    subgraph "api/"
        VIEWS[views.py]
        SERIAL[serializers.py]
        API_URLS[urls.py]
    end
    
    subgraph "apps/orchestrator/"
        GRAPH[graph.py]
        NODES[nodes.py]
        STATE[state.py]
        CACHE[cache.py]
        REASON[reasoning.py]
        TOOLS[tools.py]
        CTX[context.py]
    end
    
    subgraph "apps/agents/"
        SC_AGENT[shopcore/agent.py]
        SS_AGENT[shipstream/agent.py]
        PG_AGENT[payguard/agent.py]
        CD_AGENT[caredesk/agent.py]
    end
    
    subgraph "apps/models/"
        SC_MODEL[shopcore/models.py]
        SS_MODEL[shipstream/models.py]
        PG_MODEL[payguard/models.py]
        CD_MODEL[caredesk/models.py]
    end
    
    CONFIG --> URLS --> VIEWS
    VIEWS --> GRAPH
    GRAPH --> NODES
    NODES --> STATE & CACHE & REASON
    NODES --> SC_AGENT & SS_AGENT & PG_AGENT & CD_AGENT
    SC_AGENT --> SC_MODEL
    SS_AGENT --> SS_MODEL
    PG_AGENT --> PG_MODEL
    CD_AGENT --> CD_MODEL
```

---

## 2. Activity Diagram - User Query

```mermaid
flowchart TB
    START((Start))
    
    A[User Types Query]
    B[Select Customer]
    C[Click Send]
    
    D[API Receives Request]
    E[Validate Input]
    
    F{Cache Hit?}
    G[Return Cached Intent]
    
    H{Pattern Match?}
    I[Use ORM-first]
    
    J[Call LLM for Analysis]
    K[Extract Intent & Entities]
    
    L[Create Execution Plan]
    M[Determine Batches]
    
    N[Execute Batch 1]
    O{More Batches?}
    P[Execute Next Batch]
    
    Q[Collect All Results]
    R[Synthesize Response]
    
    S[Display in Chat UI]
    STOP((End))
    
    START --> A --> B --> C --> D --> E
    E --> F
    F -->|Yes| G --> L
    F -->|No| H
    H -->|Yes| I --> L
    H -->|No| J --> K --> L
    L --> M --> N --> O
    O -->|Yes| P --> O
    O -->|No| Q --> R --> S --> STOP
```

---

## 3. Agent Selection Activity

```mermaid
flowchart TB
    Q[Analyze Query]
    
    Q --> E1{Contains 'order'?}
    E1 -->|Yes| SC[Add: ShopCore]
    
    Q --> E2{Contains 'track/ship'?}
    E2 -->|Yes| SS[Add: ShipStream]
    
    Q --> E3{Contains 'refund/payment'?}
    E3 -->|Yes| PG[Add: PayGuard]
    
    Q --> E4{Contains 'ticket/support'?}
    E4 -->|Yes| CD[Add: CareDesk]
    
    SC --> DEP1{SS needs order_id?}
    DEP1 -->|Yes| D1[SS depends on SC]
    
    SC --> DEP2{PG needs user_id?}
    DEP2 -->|Yes| D2[PG depends on SC]
    
    SC --> DEP3{CD needs order_id?}
    DEP3 -->|Yes| D3[CD depends on SC]
    
    D1 & D2 & D3 --> PLAN[Create Execution Plan]
```

---

## 4. State Transition Activity

```mermaid
flowchart LR
    subgraph "LISTENING"
        L1[Await Query]
        L2[Receive Input]
    end
    
    subgraph "ROUTING"
        R1[Check Cache]
        R2[Pattern Match]
        R3[LLM Analysis]
        R4[Extract Entities]
    end
    
    subgraph "EXECUTING"
        E1[Create Batches]
        E2[Execute Parallel]
        E3[Collect Results]
    end
    
    subgraph "ANSWERING"
        A1[Filter Relevant]
        A2[Synthesize]
        A3[Format Response]
    end
    
    subgraph "COMPLETE"
        C1[Return Response]
    end
    
    L1 --> L2 --> R1
    R1 --> R2 --> R3 --> R4 --> E1
    E1 --> E2 --> E3 --> A1
    A1 --> A2 --> A3 --> C1
```

---

## 5. Parallel Execution Detail

```mermaid
sequenceDiagram
    participant M as Main Thread
    participant TP as ThreadPool
    participant A1 as Agent 1
    participant A2 as Agent 2
    participant A3 as Agent 3
    
    M->>TP: Submit Batch [A1, A2, A3]
    
    par Parallel Execution
        TP->>A1: execute()
        TP->>A2: execute()
        TP->>A3: execute()
    end
    
    A1-->>TP: Result 1
    A2-->>TP: Result 2
    A3-->>TP: Result 3
    
    TP->>M: All Results
    M->>M: Merge & Continue
```
