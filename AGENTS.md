# AGENTS.md - AI News Lambda Project

## Project Overview

This is an AWS Lambda function project for processing AI news. The project uses Python runtime and follows serverless architecture patterns.

## Required Reading

Before working on this codebase, agents MUST read the following documentation files:

- **`Lambda 依赖安装和Layers.md`** - Dependency installation, Lambda Layers usage, deployment package creation
- **`Lambda 环境配置注意事项.md`** - Environment variables, VPC config, cold start optimization, ephemeral storage
- **`Lambda 部署和运行方法.md`** - Deployment methods (SAM/CLI), local testing, versioning, error handling

---

## Commands

### Local Testing

```bash
# Install SAM CLI first: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html

# Test Lambda locally with SAM
sam build
sam local invoke AiNewsFunction --event event.json

# Start local API Gateway
sam local start-api

# Invoke with Docker (requires Docker Desktop running)
sam local invoke AiNewsFunction --event event.json --docker-network host
```

### Deployment

```bash
# Using AWS CLI
aws lambda update-function-code \
  --function-name ai-news-function \
  --zip-file fileb://function.zip \
  --publish

# Using SAM (if template.yaml exists)
sam deploy --guided
```

### Code Quality

```bash
# Python linting
pip install pylint flake8
pylint lambda_function.py
flake8 lambda_function.py

# Format code
pip install black
black lambda_function.py

# Type checking
pip install mypy
mypy lambda_function.py
```

---

## Code Style Guidelines

### General Principles

- Keep functions small and focused on single responsibility
- Use clear, descriptive variable and function names
- Add docstrings for all public functions
- Handle errors explicitly, never silently

### Imports

```python
# Standard library first
import json
import os
import logging
from datetime import datetime

# Third-party libraries (e.g., boto3, requests)
import boto3
from botocore.exceptions import ClientError

# Local application modules last
from utils import helpers
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `lambda_handler`, `process_news_item` |
| Classes | PascalCase | `NewsProcessor`, `S3Uploader` |
| Constants | UPPER_SNAKE_CASE | `MAX_BATCH_SIZE`, `DEFAULT_TIMEOUT` |
| Variables | snake_case | `news_items`, `api_response` |
| Private functions | prefix with `_` | `_validate_input()` |

### Type Annotations

```python
from typing import Dict, List, Optional, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function.
    
    Args:
        event: Lambda event object
        context: Lambda context object
    
    Returns:
        Dict with statusCode and body
    """
    result: List[Dict] = process_items(event.get('items', []))
    return {
        'statusCode': 200,
        'body': json.dumps(result),
        'headers': {'Content-Type': 'application/json'}
    }

def process_items(items: List[Dict]) -> List[Dict]:
    """Process news items."""
    return [item for item in items if _validate_item(item)]

def _validate_item(item: Dict) -> bool:
    """Validate single news item."""
    required_fields = ['title', 'url', 'published_at']
    return all(field in item for field in required_fields)
```

### Error Handling

```python
import logging
import json
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    try:
        # Main logic here
        result = process_event(event)
        return {'statusCode': 200, 'body': json.dumps(result)}
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid input'})}
    
    except ClientError as e:
        logger.error(f"AWS error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'Internal error'})}
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'Internal error'})}
```

### Response Format

Always return Lambda-compatible responses:

```python
def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Create successful API response."""
    return {
        'statusCode': status_code,
        'body': json.dumps(data),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }

def error_response(message: str, status_code: int = 500) -> Dict[str, Any]:
    """Create error response."""
    return {
        'statusCode': status_code,
        'body': json.dumps({'error': message}),
        'headers': {'Content-Type': 'application/json'}
    }
```

### Logging

```python
import logging

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Event received: {json.dumps(event)}")
    logger.info(f"Lambda request ID: {context.request_id}")
    
    # Use structured logging for CloudWatch Insights
    logger.info(json.dumps({
        'event_type': 'processing',
        'items_count': len(event.get('items', [])),
        'request_id': context.request_id
    }))
```

---

## Project Structure

Recommended structure for Lambda projects:

```
.
├── lambda_function.py      # Main handler (entry point)
├── requirements.txt         # Python dependencies
├── src/                     # Source code
│   ├── __init__.py
│   ├── handlers/           # Event handlers
│   ├── services/           # Business logic
│   └── utils/              # Helper functions
├── tests/                  # Unit tests
│   ├── __init__.py
│   └── test_handlers.py
├── events/                 # Sample event files
│   └── event.json
├── template.yaml           # SAM template
└── .gitignore
```

---

## Dependencies

### Required Dependencies

Install in local `package/` directory:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt -t ./package

# Create deployment package
cd package && zip -r ../function.zip . && cd ..
zip -r function.zip lambda_function.py
```

### Using Lambda Layers

For shared dependencies across multiple Lambda functions:

1. Create a Layer with common packages
2. Attach the Layer to your function
3. Import packages normally in your code

See `Lambda 依赖安装和Layers.md` for detailed instructions.

---

## Environment Variables

Store sensitive configuration in environment variables or AWS Secrets Manager:

```python
import os

# Environment variables
API_KEY = os.environ.get('API_KEY')
TABLE_NAME = os.environ.get('TABLE_NAME', 'default-table')

# Secrets Manager (recommended for sensitive data)
import boto3

def get_secret(secret_name: str) -> dict:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

---

## Testing

### Unit Tests

```python
# tests/test_handlers.py
import pytest
import json
from lambda_function import lambda_handler

def test_lambda_handler_success():
    """Test successful Lambda invocation."""
    event = {'key': 'value'}
    context = type('Context', (), {'request_id': 'test-123'})()
    
    response = lambda_handler(event, context)
    
    assert response['statusCode'] == 200
    assert 'body' in response

def test_lambda_handler_invalid_input():
    """Test invalid input returns 400."""
    event = {}
    context = type('Context', (), {'request_id': 'test-123'})()
    
    response = lambda_handler(event, context)
    
    assert response['statusCode'] == 400
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run single test file
pytest tests/test_handlers.py

# Run single test
pytest tests/test_handlers.py::test_lambda_handler_success -v
```

---

## Important Notes

1. **Cold Start**: Lambda functions may experience cold starts. Minimize initialization code and use Lambda Layers for shared dependencies.

2. **Timeout**: Set appropriate timeout (max 15 minutes). For long-running tasks, consider Step Functions.

3. **Memory**: Higher memory also increases CPU. Test to find optimal memory setting.

4. **Logging**: Use JSON format for structured logging in CloudWatch. Include `request_id` for tracing.

5. **Error Handling**: Always return proper HTTP status codes. Use Dead Letter Queue (DLQ) for failed invocations.

6. **Security**: Never commit secrets. Use IAM roles with least privilege principle.
