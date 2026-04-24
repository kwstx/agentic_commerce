# Architecture: Smart Purchasing Agent

This document outlines the modular multi-agent architecture for the Smart Purchasing Agent, an AI-driven commerce platform designed to automate the end-to-end shopping experience.

## 1. System Overview

The system is designed as an **Agentic Workflow** where a central **Supervisor Agent** orchestrates a team of specialized sub-agents. The architecture prioritizes modularity, scalability, and secure transaction handling.

---

## 2. Multi-Agent Ecosystem

### Supervisor Agent
- **Role**: Primary orchestrator and state manager.
- **Responsibilities**: 
    - Routes user requests to specialized agents.
    - Maintains conversation context and workflow state.
    - Decides when a process is complete or requires user intervention.
    - Utilizes **LangGraph** (or CrewAI) to manage the acyclic graph of agent interactions.

### Specialized Sub-Agents
| Agent | Responsibility | Key Tools/Integrations |
| :--- | :--- | :--- |
| **Intent Parser** | Extracts product specs, budget, and preferences from natural language. | LLM (GPT-4o/Claude 3.5), Spacy |
| **Product Discovery** | Searches across multiple merchants (Shopify, Amazon, etc.). | Web Search APIs, Merchant Connectors |
| **Option Comparison** | Evaluates results based on price, shipping speed, and user reviews. | Ranking Models, Logic Engines |
| **Transaction Executor** | Handles secure checkout and payment processing. | Stripe API, Adyen, Browser Automation |
| **Error Recovery** | Detects failures (out of stock, payment declined) and suggests alternatives. | Exception Handlers, Feedback Loops |

---

## 3. Technology Stack

### Backend (Python)
- **Framework**: **FastAPI** for high-performance RESTful and WebSocket endpoints (real-time chat).
- **Orchestration**: **LangGraph** for managing complex, stateful agent workflows with tool-calling capabilities.
- **AI Integration**: OpenAI/Anthropic APIs for agent brains.

### Frontend (React / Next.js)
- **UI Framework**: Next.js for a seamless, SSR-supported commerce interface.
- **Interface**: 
    - Natural language chat input.
    - Visual "Discovery Cards" for product comparison.
    - Confirmation modals for secure transaction authorization.

### Data & Infrastructure
- **Primary Database**: **PostgreSQL** for persistent storage:
    - User Profiles & Preferences.
    - Transaction History & Audit Logs.
- **Caching & Sessions**: **Redis** for:
    - Rapid search result retrieval.
    - Real-time session state management.
- **Security**: OAuth2 for user auth; encrypted secret management for payment keys.

---

## 4. Operational Workflow

1. **User Request**: User sends "Find me a waterproof hiking backpack under $150."
2. **Parsing**: **Intent Parser** identifies attributes (Waterproof, Backpack, Max Price: $150).
3. **Discovery**: **Product Discovery Agent** queries Shopify stores and merchant APIs.
4. **Comparison**: **Option Comparison Agent** compiles a "Top 3" list with pros/cons.
5. **UI Update**: Frontend displays options; User selects one and says "Buy this one."
6. **Execution**: **Transaction Executor** initializes payment flow via Stripe.
7. **Confirmation**: Final receipt is generated and stored in PostgreSQL.

---

## 5. Deployment Strategy
- **Containerization**: Docker for all services.
- **Orchestration**: Kubernetes for scaling agent workers.
- **Monitoring**: OpenTelemetry for tracing agent decision logs.
