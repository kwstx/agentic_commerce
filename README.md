# Agentic Commerce: Modular Multi-Agent System

This repository contains the high-level architecture and initial implementation of a smart purchasing agent.

## Project Structure

```text
agentic_commerce/
├── backend/            # Python FastAPI backend
│   ├── agents/         # LangGraph modular agents
│   ├── main.py         # Entry point & WebSocket handler
│   ├── database.py     # PostgreSQL connection & schemas
│   ├── redis_client.py # Caching logic
│   └── schemas.py      # Pydantic models
├── frontend/           # Next.js 15 UI (Tailwind CSS)
│   ├── src/app/        # App router & components
│   └── public/         # Static assets
└── docker-compose.yml  # Infrastructure (Postgres, Redis)
```

## Core Features Implemented

1.  **Modular Multi-Agent System**:
    - **Supervisor**: Coordinates the workflow.
    - **Intent Parser**: Extracts product specs from natural language.
    - **Product Discovery**: Searches (mocked) for matches across sources.
    - **Option Comparison**: Ranks and summarizes findings.
    - **Transaction Executor**: Handles (mocked) checkout.
    - **Error Recovery**: Self-healing loops for failed parsing/searches.

2.  **Modern Stack**:
    - **Backend**: Python, FastAPI, LangGraph, SQLAlchemy, Redis.
    - **Frontend**: Next.js 15, React, Tailwind CSS.
    - **Real-time**: High-velocity WebSocket communication for a "chat-first" experience.

3.  **Premium Design**:
    - Glassmorphism UI components.
    - Dark mode first aesthetics.
    - Smooth micro-animations for agent transitions.

## Getting Started

### 1. Infrastructure
Run the database and cache:
```bash
docker-compose up -d
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m backend.main
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Future Roadmap
- [ ] Integrate actual Shopify/Amazon Merchant APIs.
- [ ] Real payment processing with Stripe.
- [ ] Advanced user preference learning via vector embeddings.
