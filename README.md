# AgenticCloudServiceValidator

> AI-powered multi-agent system for validating cloud service dependencies using Microsoft Agent Framework

Cloud services today are built around goal states with multiple dependencies between services to maintain consistency. This project provides an intelligent AI application that deploys specialized agents to perform automated validations across your service dependencies, ensuring data consistency and detecting anomalies before they become critical issues.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Agent Framework](https://img.shields.io/badge/Agent%20Framework-Preview-orange.svg)](https://github.com/microsoft/agent-framework)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Key Features

### 🤖 **Intelligent Multi-Agent Architecture**
- **Data Fetcher Agent**: Intelligently retrieves data from multiple services with various authentication methods
- **Cross-Verification Agent**: Uses AI to validate data consistency across service dependencies
- **Anomaly Detection Agent**: Identifies data anomalies, assigns severity levels, and generates actionable reports
- **Alert Agent**: Monitors thresholds and sends intelligent alerts via email, Slack, or webhooks

### 🔧 **Comprehensive Service Support**
- ✅ Multiple authentication types: API Keys, Bearer Tokens, OAuth2, Basic Auth, Azure Service Principals
- ✅ Configurable validation rules with custom comparison logic
- ✅ Automated periodic validation scheduling with cron support
- ✅ Real-time validation status tracking

### 📊 **Enterprise-Ready Monitoring**
- 📈 Grafana dashboards for visualization
- 📉 Prometheus metrics integration
- 🔍 Detailed anomaly reports with recommendations
- 🚨 Multi-channel alerting (Email, Slack, Webhooks)

### ☸️ **Cloud-Native Deployment**
- 🐳 Docker and Docker Compose support
- ☸️ Kubernetes manifests for managed deployment
- 🔄 Horizontal pod autoscaling ready
- 💾 PostgreSQL for production, SQLite for development

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI REST API                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Configs     │  │ Validations  │  │   Scheduler     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Orchestration Workflow                   │
│                (Microsoft Agent Framework)                   │
└─────────────────────────────────────────────────────────────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Data    │──▶ │  Cross   │──▶ │ Anomaly  │──▶ │  Alert   │
    │ Fetcher  │    │Verifier  │    │ Detector │    │  Agent   │
    └──────────┘    └──────────┘    └──────────┘    └──────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────┐
    │        Service Dependencies                      │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
    │  │Service A│  │Service B│  │Service C│   ...   │
    │  └─────────┘  └─────────┘  └─────────┘         │
    └──────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (optional)
- GitHub Personal Access Token (for GitHub Models)
- Kubernetes cluster (for production deployment)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/nairashu/AgenticCloudServiceValidator.git
cd AgenticCloudServiceValidator
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install --pre agent-framework-azure-ai
pip install -r requirements.txt
```

> **Note**: The `--pre` flag is required while Agent Framework is in preview.

4. **Configure environment**

```bash
cp .env.example .env
# Edit .env and add your GitHub token
```

Get your GitHub token from: https://github.com/settings/tokens

5. **Initialize database**

```bash
# Database will be automatically created on first run
```

### Running Locally

**Option 1: Direct Python**

```bash
python -m src.main
```

**Option 2: Using Uvicorn**

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Option 3: Using Docker Compose**

```bash
docker-compose up --build
```

Access the application:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Grafana: http://localhost:3000 (admin/admin)

## 📖 Usage

### Creating a Service Configuration

```python
import httpx
import asyncio

async def create_config():
    config = {
        "config_name": "E-Commerce Validation",
        "primary_service": {
            "service_id": "order-service",
            "service_name": "Order Management",
            "service_type": "REST_API",
            "endpoint": "https://api.orders.example.com",
            "auth_config": {
                "auth_type": "bearer_token",
                "credentials": {"token": "your_token"}
            }
        },
        "dependent_services": [
            {
                "service_id": "payment-service",
                "service_name": "Payment Service",
                "service_type": "REST_API",
                "endpoint": "https://api.payments.example.com",
                "auth_config": {
                    "auth_type": "api_key",
                    "credentials": {"api_key": "your_key"}
                }
            }
        ],
        "validation_rules": [
            {
                "rule_id": "order-payment-check",
                "rule_name": "Order-Payment Consistency",
                "description": "Verify orders have corresponding payments",
                "source_service": "order-service",
                "target_service": "payment-service",
                "expected_fields": ["order_id", "amount", "status"]
            }
        ],
        "validation_interval_minutes": 60,
        "enabled": True
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/configs/",
            json=config
        )
        return response.json()

asyncio.run(create_config())
```

### Starting a Validation

```bash
# Using the demo script
python config/demo_usage.py
```

Or via API:

```bash
curl -X POST "http://localhost:8000/api/v1/validations/start" \
  -H "Content-Type: application/json" \
  -d '{"config_id": "your-config-id"}'
```

### Checking Validation Status

```bash
curl "http://localhost:8000/api/v1/validations/{validation_id}"
```

## ☸️ Kubernetes Deployment

### Quick Deploy

```bash
# Create namespace
kubectl apply -f k8s/ingress.yaml

# Deploy PostgreSQL
kubectl apply -f k8s/postgres.yaml

# Configure secrets
kubectl create secret generic validator-secrets \
  --from-literal=github-token=YOUR_TOKEN \
  --from-literal=database-url=postgresql+asyncpg://... \
  -n validator

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml
```

For detailed deployment instructions, see [k8s/README.md](k8s/README.md).

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# GitHub Models (Free Tier for Development)
GITHUB_TOKEN=your_github_personal_access_token
MODEL_NAME=openai/gpt-4.1-mini

# Database
DATABASE_URL=sqlite+aiosqlite:///./validator.db
# For production:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Scheduler
SCHEDULER_ENABLED=true
DEFAULT_VALIDATION_INTERVAL_MINUTES=60

# Alerts
ALERT_SLACK_ENABLED=true
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Authentication Types

Supported authentication methods:

- **API Key**: Simple API key authentication
- **Bearer Token**: JWT or OAuth bearer tokens
- **Basic Auth**: Username/password authentication
- **OAuth2**: Full OAuth2 client credentials flow
- **Service Principal**: Azure service principal authentication
- **Custom**: Custom authentication headers

## 🤖 AI Models

This project uses **Microsoft Agent Framework** with **GitHub Models** (free tier) for development:

- **Default Model**: `openai/gpt-4.1-mini` - Lightweight, fast, cost-effective
- **Alternative**: `openai/gpt-4.1` - Higher quality for complex validations
- **Production**: Can switch to Microsoft Foundry (Azure AI Foundry) models

The agents use AI for:
- Intelligent data extraction and structuring
- Cross-service data consistency verification
- Anomaly detection and severity assessment
- Alert message generation with actionable recommendations

## 📊 Monitoring & Observability

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (Docker Compose) with default credentials `admin/admin`.

Pre-configured dashboards show:
- Validation success/failure rates
- Anomaly trends over time
- Service health status
- Alert distribution

### Prometheus Metrics

Metrics exposed at `http://localhost:9090/metrics`:
- `validations_total` - Total validations run
- `validations_success` - Successful validations
- `validations_failed` - Failed validations
- `anomalies_detected` - Total anomalies found
- `alerts_sent` - Alerts sent

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src --cov=agents --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 🛠️ Development

### Code Quality

```bash
# Format code
black src/ agents/

# Lint
ruff check src/ agents/

# Type checking
mypy src/ agents/
```

### Project Structure

```
AgenticCloudServiceValidator/
├── agents/                    # AI agents
│   ├── data_fetcher_agent.py
│   ├── verification_agent.py
│   ├── anomaly_agent.py
│   └── alert_agent.py
├── src/
│   ├── api/                   # FastAPI routes
│   ├── auth/                  # Authentication handlers
│   ├── storage/               # Database layer
│   ├── config.py              # Configuration
│   ├── models.py              # Data models
│   ├── orchestrator.py        # Workflow orchestration
│   ├── scheduler.py           # Job scheduling
│   └── main.py                # FastAPI application
├── k8s/                       # Kubernetes manifests
├── monitoring/                # Grafana & Prometheus configs
├── config/                    # Example configurations
├── tests/                     # Test suite
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 📚 API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/configs/` - Create service configuration
- `GET /api/v1/configs/` - List configurations
- `POST /api/v1/validations/start` - Start validation
- `GET /api/v1/validations/{id}` - Get validation status
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Uses [GitHub Models](https://github.com/marketplace/models) for AI capabilities
- Powered by [FastAPI](https://fastapi.tiangolo.com/)

## 📞 Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/nairashu/AgenticCloudServiceValidator/issues)
- Review the documentation in `/docs`
- Check example configurations in `/config`

---

**Built with ❤️ using Microsoft Agent Framework and GitHub Models**
