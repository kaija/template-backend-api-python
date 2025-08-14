# Testing Framework Documentation

This document provides comprehensive documentation for the testing framework implemented for the Production API Framework project.

## Overview

The testing framework provides a complete solution for testing FastAPI applications with:

- **Async Support**: Full support for testing async functions and endpoints
- **Database Testing**: Transaction-based test isolation with automatic rollback
- **Test Data Factories**: Consistent and reproducible test data generation
- **Mock Utilities**: Comprehensive mocking support for external dependencies
- **Coverage Reporting**: Detailed code coverage analysis with configurable thresholds
- **Multiple Test Types**: Support for unit, integration, and end-to-end tests

## Framework Components

### 1. Core Configuration (`conftest.py`)

The main pytest configuration file that provides:

- **Event Loop Management**: Proper async event loop handling for tests
- **Database Fixtures**: Test database setup with transaction isolation
- **Application Fixtures**: FastAPI app instances with dependency overrides
- **Authentication Fixtures**: Mock user authentication for testing protected endpoints
- **Environment Setup**: Automatic test environment configuration

Key fixtures:
- `db_session`: Database session with automatic transaction rollback
- `app`: FastAPI application with test dependencies
- `client`: Synchronous test client
- `async_client`: Asynchronous test client
- `mock_user`: Mock authenticated user data
- `authenticated_app`: App with authenticated user override

### 2. Test Data Factories (`factories.py`)

Factory classes for generating consistent test data:

- **UserFactory**: Creates realistic user objects
- **AdminUserFactory**: Creates users with admin privileges
- **PostFactory**: Creates blog post objects
- **CommentFactory**: Creates comment objects
- **Request/Response Factories**: API request and response data

Features:
- Automatic sequence generation for unique values
- Faker integration for realistic data
- Customizable attributes
- Relationship handling

### 3. Test Utilities (`utils.py`)

Comprehensive utility classes for testing:

#### APITestHelper
- Response status validation
- JSON response parsing
- Success/error response assertions
- Header validation
- Schema validation

#### DatabaseTestHelper
- Record creation and retrieval
- Count assertions
- Existence validation
- Test data management

#### AsyncTestHelper
- Timeout handling for async functions
- Exception testing for async code
- Async generator result collection

#### MockHelper
- Async mock creation
- HTTP response mocking
- Database session mocking

#### TestDataValidator
- UUID format validation
- Email format validation
- Timestamp parsing and validation
- Response structure validation

### 4. Test Configuration (`test_config.py`)

Centralized test configuration and constants:

- **TestConfig**: Environment-specific test settings
- **TestData**: Common test data constants
- **TestEndpoints**: API endpoint constants
- **TestHeaders**: HTTP header utilities
- **TestAssertions**: Reusable assertion helpers

### 5. Pytest Configuration (`pytest.ini`)

Comprehensive pytest configuration:

- Test discovery patterns
- Coverage reporting settings
- Async test mode configuration
- Custom markers for test categorization
- Logging configuration
- Warning filters

## Usage Examples

### Basic Unit Test

```python
import pytest
from tests.factories import UserFactory
from tests.utils import TestDataValidator

class TestUserModel:
    def test_user_creation(self):
        """Test user creation with factory."""
        user = UserFactory()
        
        assert user.id is not None
        assert user.username is not None
        TestDataValidator.validate_email(user.email)
```

### Async Database Test

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_user_database_operations(db_session: AsyncSession):
    """Test user database operations."""
    user_data = UserFactory()
    
    # In a real implementation:
    # user = await create_user(db_session, user_data)
    # retrieved_user = await get_user(db_session, user.id)
    # assert retrieved_user.username == user.username
    
    assert db_session is not None
```

### API Endpoint Test

```python
import pytest
from fastapi.testclient import TestClient
from tests.utils import APITestHelper
from tests.test_config import TestEndpoints

def test_health_check_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get(TestEndpoints.HEALTH_CHECK)
    
    data = APITestHelper.assert_success_response(response)
    APITestHelper.assert_response_schema(data, ["status", "timestamp"])
```

### Authenticated Endpoint Test

```python
import pytest
from tests.factories import UserFactory

def test_protected_endpoint(authenticated_app, client):
    """Test protected endpoint with authentication."""
    response = client.get("/api/v1/profile")
    
    data = APITestHelper.assert_success_response(response)
    assert "user_id" in data
```

### Mock External Service Test

```python
import pytest
from unittest.mock import patch
from tests.utils import MockHelper

@patch('src.services.external_api')
def test_external_service_integration(mock_external_api):
    """Test integration with external service."""
    # Setup mock
    mock_response = MockHelper.create_mock_response(
        status_code=200,
        json_data={"result": "success"}
    )
    mock_external_api.get.return_value = mock_response
    
    # Test your code that uses the external service
    # result = your_function_that_calls_external_api()
    # assert result["result"] == "success"
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage
make test-coverage

# Run fast tests only
make test-fast

# Run in parallel
make test-parallel
```

### Test Selection

```bash
# Run specific test file
pytest tests/unit/test_user.py

# Run specific test class
pytest tests/unit/test_user.py::TestUserModel

# Run specific test method
pytest tests/unit/test_user.py::TestUserModel::test_user_creation

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run tests by keyword
pytest -k "user and create"
```

### Coverage Reporting

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Generate XML coverage for CI
pytest --cov=src --cov-report=xml
```

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Main pytest configuration
├── factories.py             # Test data factories
├── utils.py                 # Test utilities
├── test_config.py           # Test configuration
├── README.md                # This documentation
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   └── test_database.py
└── fixtures/                # Test fixtures and data
    ├── __init__.py
    └── sample_data.json
```

### Test Markers

The framework defines several test markers for categorization:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.fast`: Fast tests
- `@pytest.mark.auth`: Authentication-related tests
- `@pytest.mark.database`: Database-dependent tests
- `@pytest.mark.api`: API endpoint tests

### Naming Conventions

- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test methods: `test_*`
- Factory classes: `*Factory`
- Mock objects: `mock_*`

## Best Practices

### 1. Test Isolation

- Each test should be independent and not rely on other tests
- Use database transaction rollback for data isolation
- Clean up any external resources in test teardown

### 2. Test Data Management

- Use factories for consistent test data generation
- Avoid hardcoded test data in test methods
- Use meaningful test data that reflects real-world scenarios

### 3. Async Testing

- Always use `@pytest.mark.asyncio` for async tests
- Use `async with` for async context managers
- Properly await all async operations

### 4. Mocking

- Mock external dependencies to ensure test isolation
- Use realistic mock data that matches actual API responses
- Verify mock interactions when testing integration points

### 5. Assertions

- Use descriptive assertion messages
- Test both positive and negative cases
- Use the provided assertion helpers for consistency

### 6. Coverage

- Aim for 80%+ code coverage
- Focus on testing critical business logic
- Don't sacrifice test quality for coverage percentage

## Troubleshooting

### Common Issues

1. **Async Test Failures**
   - Ensure `@pytest.mark.asyncio` is used
   - Check that all async operations are awaited
   - Verify event loop configuration

2. **Database Test Issues**
   - Ensure database session fixture is used
   - Check transaction rollback configuration
   - Verify database URL in test environment

3. **Import Errors**
   - Check PYTHONPATH includes src directory
   - Verify all required dependencies are installed
   - Check for circular imports

4. **Mock Issues**
   - Ensure mocks are properly configured
   - Check mock patch targets are correct
   - Verify mock return values match expected types

### Debug Mode

Run tests in debug mode for troubleshooting:

```bash
# Run with debug output
pytest -s --pdb

# Run with verbose output
pytest -v

# Run with extra verbose output
pytest -vv
```

## Continuous Integration

The testing framework is designed to work with CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run tests
        run: |
          poetry run pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Performance Considerations

### Test Performance

- Use `@pytest.mark.fast` for quick tests in development
- Run slow tests separately in CI
- Use parallel test execution for large test suites
- Consider test database optimization for integration tests

### Memory Management

- Clean up large test objects after use
- Use appropriate fixture scopes (function, class, module, session)
- Monitor memory usage in long-running test suites

## Extension Points

The framework is designed to be extensible:

### Custom Factories

```python
class CustomModelFactory(factory.Factory):
    class Meta:
        model = CustomModel
    
    field1 = factory.Faker('text')
    field2 = factory.Sequence(lambda n: f"value_{n}")
```

### Custom Assertions

```python
class CustomAssertions:
    @staticmethod
    def assert_custom_format(value: str) -> None:
        # Custom validation logic
        assert custom_validation(value), f"Invalid format: {value}"
```

### Custom Fixtures

```python
@pytest.fixture
def custom_fixture():
    # Setup
    resource = create_resource()
    yield resource
    # Teardown
    cleanup_resource(resource)
```

This testing framework provides a solid foundation for testing FastAPI applications with comprehensive coverage, proper isolation, and maintainable test code.