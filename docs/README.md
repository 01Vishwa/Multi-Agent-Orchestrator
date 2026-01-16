# OmniLife Multi-Agent Orchestrator - Documentation Index

## Overview

This documentation covers the OmniLife Multi-Agent Orchestrator system, a hierarchical multi-agent system that coordinates four specialized agents to answer complex, multi-domain customer queries.

---

## Documentation Files

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System architecture, component design, state machine |
| [API Documentation](api.md) | REST API endpoints, request/response schemas |
| [Data Flow](data_flow.md) | Query processing, agent execution, database relationships |
| [Diagrams](diagrams.md) | Module hierarchy, activity diagrams, sequence diagrams |

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Generate synthetic data
python scripts/generate_data.py

# Start server
python manage.py runserver 8000
```

**Access**: http://localhost:8000/

---

## Key Features

### 1. Multi-Agent Orchestration
- **Super Agent**: Coordinates 4 specialized agents
- **Parallel Execution**: Agents run in batches for low latency
- **Dependency Resolution**: Automatic ordering based on data needs

### 2. AI Efficiency Optimizations
- **Intent Caching**: 80% faster on repeat queries
- **ORM-first Pattern Matching**: 60% queries skip LLM
- **Reasoning Chain**: Chain-of-thought visibility

### 3. Four Specialized Agents

| Agent | Domain | Database Tables |
|-------|--------|-----------------|
| ShopCore | E-commerce | Users, Products, Orders |
| ShipStream | Logistics | Shipments, Warehouses, Tracking |
| PayGuard | Payments | Wallets, Transactions |
| CareDesk | Support | Tickets, Messages |

---

## Architecture Highlights

```
User Query → API → Orchestrator → [Agents in Parallel] → Synthesize → Response
                       ↓
              Cache / Pattern Match
                 (Skip LLM!)
```

---

## Environment Variables

```env
# Required
GITHUB_TOKEN=your_github_token

# Optional
DEBUG=True
DJANGO_SECRET_KEY=your_secret_key
LLM_MODEL=openai/gpt-4.1
LLM_BASE_URL=https://models.github.ai/inference
```

---

## API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send customer query |
| GET | `/api/customers/` | List customers |
| GET | `/api/health/` | System health |
| POST | `/api/agents/query/` | Direct agent query |

---

## Contact

For issues or questions, refer to the [README.md](../README.md) or open an issue.
