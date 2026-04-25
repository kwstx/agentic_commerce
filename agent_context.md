# Project Context: Smart Purchasing Agent

Autonomous purchasing.

### Security and Trust
To ensure user safety and financial control, the system implements:
- **Secure Authentication**: OAuth2 and passwordless login with JWT session management.
- **Encrypted Preferences**: User-specific filters (budget, brand, ethical) are stored using field-level encryption.
- **Payment Vaulting**: Full card details are never stored; only tokenized references from providers are used.
- **Spending Governance**: Explicit daily and per-transaction limits defined by the user.
- **Human-in-the-Loop (HITL)**: Every automated purchase generates a summary and requires explicit user approval before execution.
- **Secure Payment Processing**: Integration with Stripe and Adyen using official SDKs, supporting 3D Secure flows and real-time status updates via webhooks.
- **Fraud Detection & Anomaly Analysis**: Multi-layered risk assessment combining provider-side tools (Stripe Radar) with internal anomaly detection based on historical purchase patterns and velocity.
