# Quick Start Guide

This guide will help you get the Agentic Cloud Service Validator up and running in just a few minutes.

## Prerequisites

Before you begin, ensure you have:

- Python 3.11 or higher installed
- pip package manager
- A GitHub account and Personal Access Token
- (Optional) Docker and Docker Compose for containerized deployment

## Step 1: Get a GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name like "Cloud Validator"
4. Select scopes: `repo` (for accessing GitHub Models)
5. Click "Generate token"
6. **Copy the token** - you'll need it in the next step

## Step 2: Install the Application

### Option A: Local Installation

```bash
# Clone the repository
git clone https://github.com/nairashu/AgenticCloudServiceValidator.git
cd AgenticCloudServiceValidator

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Agent Framework (with --pre flag as it's in preview)
pip install --pre agent-framework-azure-ai

# Install other dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GitHub token:
# GITHUB_TOKEN=your_token_here
```

### Option B: Docker Installation

```bash
# Clone the repository
git clone https://github.com/nairashu/AgenticCloudServiceValidator.git
cd AgenticCloudServiceValidator

# Configure environment
cp .env.example .env
# Edit .env and add your GitHub token:
# GITHUB_TOKEN=your_token_here

# Start with Docker Compose
docker-compose up -d
```

## Step 3: Start the Application

### Local:

```bash
python -m src.main
```

### Docker:

Already started in previous step!

## Step 4: Verify Installation

Open your browser and navigate to:
- Application: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

You should see the API documentation and be able to interact with it.

## Step 5: Run Your First Validation

We'll use the demo script that validates a sample API:

```bash
python config/demo_usage.py
```

This will:
1. ✅ Create a service configuration
2. 📋 List all configurations
3. 🚀 Start a validation
4. ⏱️ Wait for results
5. ✅ Display the outcome

## Step 6: Create Your Own Configuration

Create a file `my_config.json`:

```json
{
  "config_name": "My Service Validation",
  "primary_service": {
    "service_id": "my-api",
    "service_name": "My API",
    "service_type": "REST_API",
    "endpoint": "https://api.myservice.com",
    "auth_config": {
      "auth_type": "api_key",
      "credentials": {
        "api_key": "your_api_key_here"
      }
    },
    "timeout_seconds": 30
  },
  "dependent_services": [],
  "validation_rules": [
    {
      "rule_id": "health-check",
      "rule_name": "Service Health Check",
      "description": "Verify service is responding",
      "source_service": "my-api",
      "expected_fields": ["status"]
    }
  ],
  "validation_interval_minutes": 60,
  "enabled": true
}
```

Submit it via API:

```bash
curl -X POST "http://localhost:8000/api/v1/configs/" \
  -H "Content-Type: application/json" \
  -d @my_config.json
```

## Step 7: Monitor with Grafana (Docker only)

If using Docker Compose:

1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. Navigate to Dashboards
4. View your validation metrics

## Common Issues

### Issue: "Module not found" error

**Solution**: Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Issue: "GitHub token invalid"

**Solution**: Verify your token in `.env` file:
```bash
cat .env | grep GITHUB_TOKEN
```

Make sure there are no extra spaces or quotes.

### Issue: Port 8000 already in use

**Solution**: Change the port in `.env`:
```bash
API_PORT=8001
```

### Issue: Database connection error

**Solution**: The SQLite database will be created automatically. For Docker, check PostgreSQL is running:
```bash
docker-compose ps
```

## Next Steps

- 📖 Read the [full documentation](README.md)
- 🔧 Check [example configurations](config/example-config.json)
- ☸️ Learn about [Kubernetes deployment](k8s/README.md)
- 🤝 [Contribute](CONTRIBUTING.md) to the project

## Getting Help

- 🐛 [Report bugs](https://github.com/nairashu/AgenticCloudServiceValidator/issues)
- 💬 [Ask questions](https://github.com/nairashu/AgenticCloudServiceValidator/discussions)
- 📧 Check the documentation

---

**Congratulations!** 🎉 You now have a working AI-powered cloud service validator!
