# Project Context: Smart Purchasing Agent

We are building a smart purchasing agent that can find and buy things on a user’s behalf. Instead of manually browsing different websites and entering payment details, the user would simply tell the app what they want—like a product, service, or booking—and the built-in AI would search across many merchants, compare options based on price and preferences, and then complete the purchase using the user’s preferred payment method. 

Behind the scenes, it would connect to commerce platforms such as Shopify and payment systems like Stripe or Adyen to handle transactions securely. In essence, it combines shopping, decision-making, and checkout into one interface—so instead of just helping users find products, it actually completes the entire buying process for them.

### Security and Trust
To ensure user safety and financial control, the system implements:
- **Secure Authentication**: OAuth2 and passwordless login with JWT session management.
- **Encrypted Preferences**: User-specific filters (budget, brand, ethical) are stored using field-level encryption.
- **Payment Vaulting**: Full card details are never stored; only tokenized references from providers are used.
- **Spending Governance**: Explicit daily and per-transaction limits defined by the user.
- **Human-in-the-Loop (HITL)**: Every automated purchase generates a summary and requires explicit user approval before execution.
