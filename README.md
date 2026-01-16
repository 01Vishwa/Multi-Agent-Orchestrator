# 🤖 OmniLife Multi-Agent Orchestrator

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://djangoproject.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1.x-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade **Hierarchical Multi-Agent System** that unifies customer support across four e-commerce products using **LangGraph/LangChain** for orchestration and **Django REST Framework** for API exposure.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Demo Scenarios](#demo-scenarios)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## 🎯 Overview

OmniLife is a comprehensive e-commerce conglomerate with **four distinct products**:

| Product | Domain | Purpose |
|---------|--------|---------|
| **ShopCore** | E-commerce | User accounts, product catalog, orders |
| **ShipStream** | Logistics | Shipments, tracking, warehouses |
| **PayGuard** | FinTech | Wallets, transactions, refunds |
| **CareDesk** | Support | Tickets, messages, surveys |

This system creates a **"Super Agent"** that orchestrates **four specialized Sub-Agents** to handle complex, multi-domain customer queries in real-time.

### The Challenge

> *"I ordered a 'Gaming Monitor' last week, but it hasn't arrived. I opened a ticket about this yesterday. Can you tell me where the package is right now and if my ticket has been assigned?"*

This single query requires coordination across:
1. **ShopCore** → Find the order
2. **ShipStream** → Get tracking info
3. **CareDesk** → Check ticket status

Our orchestrator handles this seamlessly! ✨

---

## 🏗️ Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │   Web    │  │  Mobile  │  │   API    │                       │
│  │   App    │  │   App    │  │  Client  │                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
└───────┼─────────────┼─────────────┼─────────────────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API GATEWAY                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Django REST Framework                        │   │
│  │    POST /api/chat/  │  GET /api/health/  │  Swagger UI   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   LangGraph Workflow                      │   │
│  │                                                           │   │
│  │   [Analyze] → [Plan] → [Execute] → [Synthesize]          │   │
│  │       │          │          │            │                │   │
│  │       ▼          ▼          ▼            ▼                │   │
│  │   Intent     Dependency   Agent      Response             │   │
│  │  Detection   Resolution   Calls     Generation            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┼────────────────────────────────┐    │
│  │                  Sub-Agents                              │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │ShopCore  │ │ShipStream│ │ PayGuard │ │ CareDesk │   │    │
│  │  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │   │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │    │
│  └───────┼────────────┼────────────┼────────────┼──────────┘    │
└──────────┼────────────┼────────────┼────────────┼───────────────┘
           │            │            │            │
           ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATABASE LAYER                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │DB_Shop-  │  │DB_Ship-  │  │DB_Pay-   │  │DB_Care-  │        │
│  │  Core    │  │ Stream   │  │  Guard   │  │  Desk    │        │
│  │          │  │          │  │          │  │          │        │
│  │ • Users  │  │• Shipment│  │• Wallets │  │• Tickets │        │
│  │• Products│  │• Tracking│  │• Trans-  │  │• Messages│        │
│  │• Orders  │  │• Warehouse│ │  actions │  │• Surveys │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### LangGraph Workflow

```
        START
          │
          ▼
    ┌───────────┐
    │  Analyze  │  ← Parse intent, extract entities
    │   Query   │    Identify required agents
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │  Create   │  ← Build execution plan
    │   Plan    │    Resolve dependencies
    └─────┬─────┘
          │
          ▼
    ┌───────────┐◄─────────┐
    │  Execute  │          │ Loop until
    │  Agents   │──────────┘ all complete
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │Synthesize │  ← Combine results
    │ Response  │    Generate natural language
    └─────┬─────┘
          │
          ▼
         END
```

---

## ✨ Features

### Core Capabilities

- 🧠 **Intelligent Query Routing** - Automatically identifies which agents are needed
- 🔗 **Dependency Resolution** - Handles cross-database dependencies (e.g., find order before tracking)
- 💬 **Natural Language I/O** - Accepts plain English, returns helpful responses
- 🔄 **Conversation Context** - Maintains session history for follow-up queries
- ⚡ **Parallel Execution** - Independent agents execute concurrently

### Sub-Agent Capabilities

| Agent | Capabilities |
|-------|-------------|
| **ShopCore** | Order lookup, product search, user info, order status |
| **ShipStream** | Package tracking, delivery ETA, warehouse info, tracking history |
| **PayGuard** | Wallet balance, refund status, transaction history, payment methods |
| **CareDesk** | Ticket status, agent assignment, message history, satisfaction surveys |

### API Features

- 📚 **OpenAPI/Swagger** documentation
- 🔒 **Rate limiting** and error handling
- 🏥 **Health check** endpoint
- 🐛 **Debug mode** for development

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11+ |
| **Framework** | Django 5.0 + Django REST Framework |
| **Agent Orchestration** | LangGraph 0.1.x |
| **LLM Integration** | LangChain 0.2.x + OpenAI GPT-4 |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **API Documentation** | drf-spectacular |
| **Data Generation** | Faker |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- OpenAI API key
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/omni-retail-orchestrator.git
   cd omni-retail-orchestrator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   copy .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Generate synthetic data**
   ```bash
   python scripts/generate_data.py
   ```

7. **Start the server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - **Chat UI**: http://localhost:8000/
   - **API Docs**: http://localhost:8000/api/docs/
   - **Health Check**: http://localhost:8000/api/health/

---

## 📡 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat/` | Main conversation endpoint |
| `GET` | `/api/chat/history/{session_id}/` | Get conversation history |
| `POST` | `/api/agents/query/` | Direct agent query (debug) |
| `GET` | `/api/health/` | System health check |

### Chat Request

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Where is my Gaming Monitor order?",
    "session_id": "session-123",
    "include_debug": true
  }'
```

### Chat Response

```json
{
  "response": "Your Gaming Monitor order (ORD-abc123) is currently at the Mumbai Distribution Hub. It's expected to arrive tomorrow. I also see you have an open support ticket (TKT-456) which has been assigned to Agent Sarah.",
  "session_id": "session-123",
  "agents_used": ["shopcore", "shipstream", "caredesk"],
  "success": true,
  "intent": "delivery_tracking",
  "intent_confidence": 0.95,
  "execution_details": {
    "agent_results": [
      {
        "agent_name": "shopcore",
        "success": true,
        "data": {...},
        "execution_time_ms": 245
      },
      ...
    ]
  }
}
```

---

## 🎬 Demo Scenarios

### Scenario 1: Multi-Agent Order Tracking

**Query**: *"I ordered a 'Gaming Monitor' last week, but it hasn't arrived. I opened a ticket about this yesterday. Can you tell me where the package is right now and if my ticket has been assigned to an agent?"*

**Agent Flow**:
1. **ShopCore** → Finds OrderID for 'Gaming Monitor'
2. **ShipStream** → Gets tracking events and current location
3. **CareDesk** → Finds recent ticket and assignment status

**Response**: *"Your Gaming Monitor order (ORD-12345) is currently at the Mumbai Hub. Expected delivery is tomorrow. Your support ticket TKT-567 has been assigned to Agent Priya and is being worked on."*

### Scenario 2: Refund Status Check

**Query**: *"I returned my order #123 and requested a refund. What's the status?"*

**Agent Flow**:
1. **ShopCore** → Verifies order exists and status is 'refunded'
2. **PayGuard** → Finds refund transaction status
3. **CareDesk** → Checks if there's a related ticket

### Scenario 3: Premium Customer Inquiry

**Query**: *"Show me all my open tickets and pending orders"*

**Agent Flow**:
1. **ShopCore** → Gets all pending orders for user
2. **CareDesk** → Lists all open tickets

---

## 📂 Project Structure

```
omni-retail-orchestrator/
│
├── config/                     # Django project settings
│   ├── settings/
│   │   └── base.py            # Main configuration
│   ├── urls.py                # URL routing
│   ├── wsgi.py                # WSGI entry point
│   └── asgi.py                # ASGI entry point
│
├── apps/
│   ├── core/                  # Shared utilities
│   │   ├── models.py          # Base models
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── utils.py           # Helper functions
│   │
│   ├── shopcore/              # E-commerce module
│   │   ├── models.py          # Users, Products, Orders
│   │   ├── agent.py           # ShopCore Sub-Agent
│   │   └── schemas.py         # Database schema
│   │
│   ├── shipstream/            # Logistics module
│   │   ├── models.py          # Shipments, Tracking
│   │   ├── agent.py           # ShipStream Sub-Agent
│   │   └── schemas.py
│   │
│   ├── payguard/              # FinTech module
│   │   ├── models.py          # Wallets, Transactions
│   │   ├── agent.py           # PayGuard Sub-Agent
│   │   └── schemas.py
│   │
│   ├── caredesk/              # Support module
│   │   ├── models.py          # Tickets, Messages
│   │   ├── agent.py           # CareDesk Sub-Agent
│   │   └── schemas.py
│   │
│   └── orchestrator/          # LangGraph orchestration
│       ├── state.py           # State schema
│       ├── nodes.py           # Graph nodes
│       └── graph.py           # Workflow definition
│
├── api/                       # REST API layer
│   ├── views.py               # API endpoints
│   ├── serializers.py         # Request/Response schemas
│   └── urls.py                # API routing
│
├── scripts/
│   └── generate_data.py       # Synthetic data generator
│
├── templates/
│   └── index.html             # Chat UI
│
├── requirements.txt           # Python dependencies
├── manage.py                  # Django CLI
└── README.md                  # This file
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (required) |
| `DEBUG` | Debug mode | `True` |
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `OPENAI_MODEL` | LLM model to use | `gpt-4` |
| `DATABASE_URL` | Database connection | `sqlite:///db.sqlite3` |
| `REDIS_URL` | Redis for memory | `redis://localhost:6379/0` |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test
pytest tests/unit/test_shopcore_agent.py
```

---

## 📊 Performance Considerations

- **LLM Caching**: Consider implementing response caching for common queries
- **Database Indexing**: Ensure proper indexes on foreign keys
- **Connection Pooling**: Use Django's database connection pooling
- **Rate Limiting**: Configured at 100 requests/hour for anonymous users

---

## 🛣️ Roadmap

- [ ] Add async agent execution for better performance
- [ ] Implement Redis-backed conversation memory
- [ ] Add streaming responses for real-time chat
- [ ] Support for multiple LLM providers (Anthropic, Azure)
- [ ] Admin dashboard for monitoring
- [ ] Webhook integrations

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the amazing LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Django REST Framework](https://www.django-rest-framework.org/) for the API layer

---

<p align="center">
  Built with ❤️ for the Clickpost AI Engineer Challenge
</p>