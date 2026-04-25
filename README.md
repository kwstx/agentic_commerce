# Agentic Commerce: Smart Purchasing System

Agentic Commerce is a modular, multi-agent platform designed to automate the end-to-end shopping experience. By leveraging large language models and specialized agentic workflows, the system enables users to delegate natural language requests—such as product discovery, comparison, and purchase execution—to an autonomous AI system.

The platform integrates directly with commerce providers and payment gateways to handle the entire lifecycle of a transaction, from intent parsing to order confirmation, while maintaining strict security and human-in-the-loop governance.

## Key Features

- **Autonomous Discovery**: Multi-source product retrieval across APIs (Shopify, Amazon, Google Shopping) and web-based merchants using robots.txt-compliant automation.
- **Intelligent Comparison**: Multi-criteria ranking engine that evaluates products based on price, technical specifications, delivery speed, and customer sentiment.
- **Secure Transaction Execution**: Fault-tolerant checkout orchestration with integrated support for Stripe and Adyen.
- **Human-in-the-Loop (HITL)**: Mandatory user authorization for all financial expenditures, providing transparent reasoning and detailed cost breakdowns before execution.
- **Comprehensive Security**: PCI-DSS compliant architecture with tokenized payment vaulting, field-level encryption for sensitive user data, and protection against prompt injection.
- **Real-time Observability**: Distributed tracing and monitoring for agent decision-making, latency, and system health.

## System Architecture

The project is built on a modular multi-agent ecosystem where a central Supervisor Agent orchestrates specialized workers.

### Multi-Agent Ecosystem
- **Supervisor Agent**: Manages state transitions and routes tasks using LangGraph.
- **Intent Parser**: Extracts structured constraints (budget, brand, specs) from natural language input.
- **Discovery Agent**: Executes parallel searches across multiple merchant sources.
- **Comparison Agent**: Normalizes attributes and scores candidates using a multi-criteria decision model.
- **Transaction Agent**: Handles the secure checkout lifecycle, including inventory verification and payment orchestration.
- **Monitoring Agent**: Tracks agent reasoning and provides real-time status updates via WebSockets.

### Technical Stack
- **Backend**: FastAPI (Python), LangGraph, LangChain, SQLAlchemy.
- **Frontend**: Next.js, React, Tailwind CSS (optional).
- **AI Models**: Gemini 3 Flash, OpenAI GPT-4o.
- **Database**: PostgreSQL (Structured data), Redis (Caching and Session State).
- **Security**: OAuth2, JWT, AES-256 Encryption, Guardrails-AI.
- **Infrastructure**: Docker, Kubernetes, Prometheus, Grafana, OpenTelemetry.

## Getting Started

### Prerequisites
- Docker and Docker Compose
- API Keys for:
    - Google Gemini or OpenAI
    - Stripe (for payment testing)
    - (Optional) Merchant-specific APIs

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kwstx/agentic_commerce.git
   cd agentic_commerce
   ```

2. **Configure environment variables**:
   Create a `.env` file in the root directory based on `.env.example`:
   ```env
   # Database
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=password
   POSTGRES_DB=agentic_commerce

   # AI Providers
   GEMINI_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here

   # Payments
   STRIPE_API_KEY=your_stripe_key

   # Security
   SECRET_KEY=your_secret_key
   ```

3. **Launch the platform**:
   ```bash
   docker-compose up --build
   ```

The backend API will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Safety and Governance

The system implements multiple layers of protection to ensure financial safety and data privacy:

- **Spending Limits**: Users define per-transaction and daily spending caps enforced at the core logic level.
- **Atomic Transactions**: The Transaction Agent uses a coordinator pattern to ensure multi-step purchases (inventory, payment, verification) are atomic or correctly rolled back on failure.
- **Audit Trails**: Every decision made by an agent is logged in an immutable audit trail within PostgreSQL, including the LLM reasoning and the raw tool output.
- **Least Privilege**: API keys and agent permissions are restricted to the minimum required scopes for their specific role.

## Monitoring and Observability

The platform utilizes a modern observability stack to monitor both system performance and agent reasoning:

- **OpenTelemetry**: Distributed tracing for tracking requests through the multi-agent graph.
- **Prometheus**: Real-time metrics for search success rates, purchase completion, and LLM token usage.
- **Grafana**: Pre-configured dashboards for visualizing system health and agent performance.
- **Structured Logging**: JSON-formatted logs for automated analysis and anomaly detection.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
