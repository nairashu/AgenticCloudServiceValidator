# Contributing to Agentic Cloud Service Validator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/nairashu/AgenticCloudServiceValidator/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Detailed description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Relevant logs or screenshots

### Suggesting Enhancements

1. Check existing issues and discussions
2. Create a new issue with:
   - Clear description of the enhancement
   - Use cases and benefits
   - Potential implementation approach
   - Any alternative solutions considered

### Pull Requests

1. **Fork the repository** and create a branch from `main`

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes** following the code style guidelines

3. **Add tests** for new functionality

4. **Update documentation** as needed

5. **Run tests and linting**

```bash
# Format code
black src/ agents/
ruff check src/ agents/

# Run tests
pytest --cov

# Type checking
mypy src/ agents/
```

6. **Commit your changes** with clear messages

```bash
git commit -m "Add feature: your feature description"
```

7. **Push to your fork** and submit a pull request

```bash
git push origin feature/your-feature-name
```

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Setup Steps

1. Clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/AgenticCloudServiceValidator.git
cd AgenticCloudServiceValidator
```

2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies

```bash
pip install --pre agent-framework-azure-ai
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If you create one
```

4. Set up environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run tests

```bash
pytest
```

## Code Style Guidelines

### Python

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting (line length: 120)
- Use [Ruff](https://github.com/astral-sh/ruff) for linting
- Use type hints where possible
- Write docstrings for all public functions and classes

### Example

```python
"""Module docstring."""

from typing import Optional


class ExampleClass:
    """Class docstring.
    
    Attributes:
        name: Description of attribute
    """
    
    def __init__(self, name: str) -> None:
        """Initialize the class.
        
        Args:
            name: The name parameter
        """
        self.name = name
    
    async def process(self, data: dict) -> Optional[str]:
        """Process the data.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed result or None
            
        Raises:
            ValueError: If data is invalid
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        return data.get("result")
```

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source structure (e.g., `tests/test_agents/test_data_fetcher_agent.py`)
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Use fixtures for common setup
- Mock external dependencies

### Example Test

```python
import pytest
from src.models import ServiceConfig


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return ServiceConfig(
        config_name="Test Config",
        # ... other fields
    )


async def test_create_config_success(sample_config):
    """Test successful configuration creation."""
    # Arrange
    # ... setup
    
    # Act
    result = await create_config(sample_config)
    
    # Assert
    assert result is not None
    assert result.config_name == "Test Config"
```

## Documentation

- Update README.md for significant changes
- Add docstrings to all public APIs
- Update API documentation if endpoints change
- Include examples for new features

## Commit Messages

Use clear, descriptive commit messages:

- `feat: Add new anomaly detection algorithm`
- `fix: Correct authentication error handling`
- `docs: Update deployment guide`
- `test: Add tests for verification agent`
- `refactor: Simplify orchestrator logic`
- `style: Format code with black`
- `chore: Update dependencies`

## Review Process

1. All PRs require at least one review
2. CI checks must pass
3. Code coverage should not decrease
4. Documentation must be updated
5. Breaking changes need discussion

## Getting Help

- Join discussions in [GitHub Discussions](https://github.com/nairashu/AgenticCloudServiceValidator/discussions)
- Ask questions in issues with the `question` label
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Agentic Cloud Service Validator! 🎉
