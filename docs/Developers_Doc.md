Developer Engineering Guidelines (Mandatory for This Application)
This application handles financial account integrations + AI reasoning over portfolio data, so it must be designed with production-grade reliability, modularity, observability, and security from day one.
These guidelines define coding expectations for all contributors.
________________________________________
1. Code Architecture Principles
Modular Design (Required)
The system must be organized into independent modules:
Example structure:
app/
 ├── auth/
 ├── broker_integrations/
 ├── portfolio_engine/
 ├── analytics_engine/
 ├── ai_agent/
 ├── alerting/
 ├── scenario_simulator/
 ├── api/
 ├── database/
 └── utils/
Each module must:
•	have a single responsibility 
•	expose clean interfaces 
•	avoid tight coupling 
•	support independent testing 
Avoid monolithic logic files.
________________________________________
Object-Oriented Design (Required)
Follow OOP best practices:
Use:
•	encapsulation 
•	abstraction 
•	inheritance (where appropriate) 
•	polymorphism (for broker adapters) 
Example:
BrokerAdapter (base class)

RobinhoodAdapter
PlaidAdapter
FidelityAdapter
This allows easy expansion later.
________________________________________
Interface-Based Broker Integration
Never hardcode Robinhood-specific logic across the app.
Instead:
class BrokerInterface:

    get_positions()

    get_transactions()

    get_cash_balance()
Then implement:
RobinhoodAdapter(BrokerInterface)
PlaidAdapter(BrokerInterface)
This enables multi-broker expansion later.
________________________________________
2. Error Handling Strategy
Financial APIs fail frequently.
Your system must assume:
•	network timeouts 
•	partial responses 
•	stale market data 
•	authentication expiry 
•	API rate limits 
Required:
try / catch everywhere external calls exist
Example:
try:
    positions = broker.get_positions()
except BrokerTimeoutError:
    fallback_to_cached_positions()
Never crash UI due to upstream API failure.
________________________________________
3. Logging Strategy (Mandatory)
Logging must exist at:
INFO level
User connected broker
Portfolio refreshed
Scenario simulation triggered
WARNING level
Partial API response received
Fallback triggered
Cache used instead of live data
ERROR level
Broker authentication failed
Portfolio sync failure
LLM response parsing failed
Example logging pattern:
logger.info("Robinhood portfolio sync started")
Use structured logging:
JSON logs preferred
Example:
{
 "event": "portfolio_sync",
 "status": "success",
 "user_id": 1832
}
________________________________________
4. Fallback Mechanisms (Critical Requirement)
System must never depend on a single data source.
Example hierarchy:
Primary:
Robinhood API

Fallback:
Cached portfolio snapshot

Secondary fallback:
Manual CSV import
For market data:
Primary:
Polygon

Fallback:
Yahoo Finance

Fallback:
Cached historical data
LLM fallback example:
Primary:
OpenAI

Fallback:
Local Ollama model
________________________________________
5. API Design Standards
Follow REST conventions:
GET /portfolio
GET /portfolio/health-score
POST /simulate/scenario
POST /ask-agent
Responses must include:
status
data
error_message
timestamp
Example:
{
 "status": "success",
 "data": {...},
 "timestamp": "2026-04-03T15:02:11"
}
Never return raw exceptions to frontend.
________________________________________
6. Security Requirements (Fintech-Level)
Mandatory protections:
No plaintext credentials anywhere
Never store:
Robinhood password
API tokens
session cookies
Instead:
Use:
OAuth where possible
encrypted token storage
________________________________________
Secrets Management
Secrets must live in:
.env (development only)
AWS Secrets Manager
Vault
GCP Secret Manager
Never commit:
API keys
tokens
credentials
________________________________________
Encryption Requirements
Encrypt:
tokens
portfolio snapshots
user identifiers
At:
•	rest 
•	transit 
________________________________________
7. Database Design Best Practices
Separate tables:
users
broker_connections
portfolio_snapshots
positions
transactions
alerts
ai_queries
scenario_results
Never store raw LLM responses without metadata.
Instead:
query
response
confidence
timestamp
model_used
________________________________________
8. AI Agent Engineering Guidelines
LLM must NEVER operate blindly.
Always provide:
portfolio context
allocation breakdown
risk metrics
user preferences
Example prompt format:
SYSTEM:
You are a portfolio assistant analyzing user's holdings.

CONTEXT:
portfolio_allocation.json
risk_score.json
performance_metrics.json
This ensures grounded responses.
________________________________________
9. Observability Requirements
System must include:
Metrics tracking
Track:
portfolio refresh latency
broker sync success rate
LLM response latency
scenario simulation runtime
Example stack:
Prometheus
Grafana
OpenTelemetry
________________________________________
Health Monitoring Endpoints
Example:
/health
/status
/metrics
Used for deployment reliability.
________________________________________
10. Testing Strategy (Mandatory)
Required coverage:
Unit tests
Test:
allocation calculations
risk scoring
overlap detection
scenario simulation math
________________________________________
Integration tests
Test:
broker sync pipeline
portfolio ingestion
LLM agent interface
________________________________________
Regression tests
Prevent errors like:
incorrect allocation %
wrong gain/loss values
duplicate holdings
________________________________________
11. Performance Optimization Guidelines
Portfolio queries must return:
< 500 ms response time
Scenario simulations:
< 2 seconds
LLM responses:
< 4 seconds target
Use:
Redis caching
portfolio snapshot caching
precomputed analytics
________________________________________
12. Documentation Standards
Each module must include:
README.md
interface description
input/output examples
Functions must include:
docstrings
parameter descriptions
return types
edge cases
Example:
def calculate_sector_allocation(portfolio):

    """
    Calculates sector exposure percentages.

    Parameters:
        portfolio (PortfolioModel)

    Returns:
        Dict[str, float]
    """
________________________________________
13. Deployment Architecture Expectations
Application must support:
Docker deployment
local development mode
cloud deployment mode
Preferred architecture:
Frontend:
Next.js

Backend:
FastAPI

Worker:
Celery / background jobs

Cache:
Redis

DB:
PostgreSQL
________________________________________
14. Feature Flagging Support (Future-Proofing)
Enable toggling:
experimental scenario engine
local LLM mode
crypto analytics module
tax-loss harvesting assistant
Example tool:
LaunchDarkly
Unleash
simple config flags
________________________________________
15. Developer Experience Requirements
Project must support:
linting
type checking
formatting
pre-commit hooks
Recommended stack:
black
ruff
mypy
pytest
________________________________________
Final Engineering Philosophy
This system should be built like:
Stripe-level reliability
+
Notion-level UX simplicity
+
Bloomberg-lite intelligence
+
ChatGPT-style interaction
If built correctly with these standards, the architecture will naturally support:
multi-broker expansion
mobile apps
autonomous agent workflows
enterprise analytics tier
and eventually subscription monetization.

