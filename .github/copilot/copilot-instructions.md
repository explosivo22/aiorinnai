# GitHub Copilot Instructions

## Project Overview

**aiorinnai** is an async Python library for the Rinnai Control-R water heater API. It uses AWS Cognito for authentication and communicates with Rinnai's cloud services via GraphQL and REST endpoints.

## Priority Guidelines

When generating code for this repository:

1. **Version Compatibility**: Strictly adhere to Python 3.11+ features only
2. **Async First**: All I/O operations must be async using `aiohttp` and `asyncio`
3. **Type Safety**: Use type hints throughout; the package is typed (`py.typed`)
4. **Codebase Patterns**: Match existing patterns from the codebase exactly
5. **Code Quality**: Prioritize maintainability, testability, and clear documentation

## Technology Stack

### Core Requirements

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | >=3.11 | Runtime |
| aiohttp | >=3.6.1 | Async HTTP client |
| pycognito | >=2024.5.1,<2025 | AWS Cognito authentication |
| boto3 | >=1.26.0 | AWS SDK |
| botocore | >=1.29.0 | AWS SDK core |
| attrs | >=21.0.0 | Class definitions |

### Development Requirements

| Dependency | Version | Purpose |
|------------|---------|---------|
| pytest | >=7.0.0 | Testing framework |
| pytest-asyncio | >=0.21.0 | Async test support |
| pytest-cov | >=4.0.0 | Coverage reporting |
| aioresponses | >=0.7.4 | HTTP mocking |
| mypy | >=1.0.0 | Type checking |

## Architectural Patterns

### Module Organization

```
aiorinnai/
├── __init__.py    # Public API exports with __all__
├── api.py         # Main API client with auth and request handling
├── device.py      # Device command handlers
├── user.py        # User data retrieval
├── errors.py      # Exception hierarchy
├── const.py       # Constants (endpoints, payloads, headers)
└── py.typed       # PEP 561 marker
```

### Class Design Patterns

1. **Use `attrs` for data classes** with `@attr.s` decorator:
   ```python
   @attr.s
   class API:
       session: ClientSession | None = attr.ib(default=None)
       timeout: float = attr.ib(default=DEFAULT_TIMEOUT)
       _internal_state: str = attr.ib(default=None, init=False)
   ```

2. **Handler classes** use constructor injection:
   ```python
   class Device:
       def __init__(self, request: RequestFunc) -> None:
           self._request: RequestFunc = request
   ```

3. **Type aliases** for callable types:
   ```python
   RequestFunc = Callable[..., Awaitable[dict[str, Any] | str]]
   ```

### Async Context Manager Pattern

Always support async context manager for resource cleanup:

```python
async def __aenter__(self) -> "API":
    return self

async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: Any,
) -> None:
    await self.close()
```

### Error Handling Pattern

1. **Exception hierarchy** with base class:
   ```python
   class RinnaiError(Exception):
       """Base exception for all Rinnai errors."""

   class RequestError(RinnaiError):
       """HTTP/connection failures."""

   class CloudError(RinnaiError):
       """AWS Cognito and cloud errors."""
   ```

2. **Exception mapping** from AWS errors:
   ```python
   AWS_EXCEPTIONS: dict[str, type[CloudError]] = {
       "UserNotFoundException": UserNotFound,
       "NotAuthorizedException": Unauthenticated,
   }
   ```

3. **Wrap external exceptions** with context:
   ```python
   except ClientError as err:
       raise _map_aws_exception(err) from err
   ```

### Retry Logic Pattern

Implement exponential backoff for transient errors:

```python
RETRYABLE_EXCEPTIONS = (ClientConnectorError, ServerConnectionError)

for attempt in range(self._retry_count):
    try:
        # Make request
    except RETRYABLE_EXCEPTIONS as err:
        if attempt < self._retry_count - 1:
            await asyncio.sleep(delay)
            delay *= self._retry_multiplier
            continue
        raise RequestError(...) from err
```

## Code Style Standards

### Imports

1. **Future annotations** first:
   ```python
   from __future__ import annotations
   ```

2. **Standard library**, then **third-party**, then **local**:
   ```python
   import asyncio
   from typing import Any, Awaitable, Callable

   import attr
   from aiohttp import ClientSession

   from .const import LOGGER
   from .errors import RequestError
   ```

### Type Hints

1. **Use union syntax** (`|`) instead of `Union`:
   ```python
   session: ClientSession | None = None
   response: dict[str, Any] | str
   ```

2. **Use `dict[K, V]`** instead of `Dict[K, V]` (Python 3.9+ style):
   ```python
   def get_info(self) -> dict[str, Any] | None:
   ```

3. **Annotate all function parameters and returns**:
   ```python
   async def set_temperature(
       self,
       dev: dict[str, Any],
       temp: int,
   ) -> dict[str, Any] | str:
   ```

### Docstrings

Use Google-style docstrings with all sections:

```python
"""Short description of the function.

Longer description if needed, explaining behavior,
side effects, or important details.

Args:
    param1: Description of first parameter.
    param2: Description of second parameter.

Returns:
    Description of return value.

Raises:
    ExceptionType: When this exception is raised.

Example:
    ```python
    result = await function(arg1, arg2)
    ```
"""
```

### Module Docstrings

Each module must have a docstring explaining its purpose:

```python
"""Device endpoint handlers for Rinnai water heater commands.

This module provides the Device class for sending commands to Rinnai
water heaters via the shadow PATCH endpoint.
"""
```

### Constants

1. **Define at module level** with UPPER_CASE:
   ```python
   DEFAULT_RETRY_COUNT = 3
   DEFAULT_RETRY_DELAY = 1.0
   GRAPHQL_ENDPOINT = "https://..."
   ```

2. **Group related constants** with comments:
   ```python
   # Retry configuration
   DEFAULT_RETRY_COUNT = 3
   DEFAULT_RETRY_DELAY = 1.0
   ```

### Private vs Public

1. **Single underscore** for internal implementation:
   ```python
   _id_token: str | None
   async def _request(self, ...):
   ```

2. **Export public API via `__all__`**:
   ```python
   __all__ = [
       "API",
       "Device",
       "RinnaiError",
   ]
   ```

## Testing Standards

### Test Organization

```python
"""Tests for the aiorinnai library.

This module contains unit tests for the API client, device commands,
and user data retrieval with mocked HTTP responses.
"""
```

### Test Class Pattern

Group related tests in classes:

```python
class TestAPILogin:
    """Tests for API authentication."""

    @pytest.mark.asyncio
    async def test_login_success(self, mock_cognito: MagicMock) -> None:
        """Test successful login flow."""
        ...

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self) -> None:
        """Test login with invalid credentials raises Unauthenticated."""
        ...
```

### Fixtures

Use pytest fixtures for shared test resources:

```python
@pytest.fixture
def mock_cognito() -> MagicMock:
    """Create a mock Cognito client."""
    cognito = MagicMock()
    cognito.id_token = "mock_id_token"
    return cognito
```

### Async Tests

1. **Always use `@pytest.mark.asyncio`**
2. **Always add return type `-> None`**
3. **Clean up resources** (call `await api.close()`)

```python
@pytest.mark.asyncio
async def test_example(self) -> None:
    """Test description."""
    api = API()
    try:
        # Test logic
        assert result == expected
    finally:
        await api.close()
```

### Mock Patterns

Mock external services, not internal logic:

```python
with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
    api = API()
    await api.async_login("test@example.com", "password")
```

### Sample Data

Define sample responses as module-level constants:

```python
SAMPLE_USER_RESPONSE: dict[str, Any] = {
    "data": {
        "getUserByEmail": {
            "items": [{"id": "user-123", ...}]
        }
    }
}
```

## pytest Configuration

Tests use these settings (from `pytest.ini`):

```ini
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

## Common Patterns to Follow

### API Request Method

```python
async def _request(
    self,
    method: str,
    url: str,
    **kwargs: Any,
) -> dict[str, Any] | str:
    """Make authenticated request with retry logic."""
    await self.async_check_token()

    kwargs.setdefault("headers", {})
    if self._id_token:
        kwargs["headers"]["Authorization"] = f"Bearer {self._id_token}"

    session = self._get_session()
    # ... retry logic
```

### Device Command Method

```python
async def command_name(
    self,
    dev: dict[str, Any],
    param: int,
) -> dict[str, Any] | str:
    """Command description.

    Args:
        dev: Device dictionary containing 'thing_name'.
        param: Parameter description.

    Returns:
        API response confirming the command.

    Raises:
        RequestError: If the API request fails.
    """
    return await self._set_shadow(dev, {"setting_key": param})
```

### GraphQL Query Execution

```python
async def get_info(self, id: str) -> dict[str, Any]:
    payload = GET_PAYLOAD_TEMPLATE % (id)

    response = await self._request(
        "post",
        GRAPHQL_ENDPOINT,
        data=payload,
        headers=GET_PAYLOAD_HEADERS,
    )

    if isinstance(response, str):
        return {}
    return response
```

## Things to Avoid

1. **Don't use blocking I/O** - Use `run_in_executor` for sync operations:
   ```python
   cognito = await loop.run_in_executor(
       None,
       partial(self._create_cognito_client, username=email),
   )
   ```

2. **Don't leak resources** - Always close sessions properly

3. **Don't use `Union` or `Optional`** - Use `X | None` syntax

4. **Don't use `Dict`, `List`, `Tuple`** from typing - Use built-in generics

5. **Don't catch generic `Exception`** - Be specific about exception types

6. **Don't hardcode values** - Use constants from `const.py`

7. **Don't skip type annotations** - Every function needs full type hints

## Version Control

- Follow Semantic Versioning
- Current version: `0.4.0a2` (alpha release)
- Version defined in both `setup.py` and `__init__.py`

## License

Apache Software License - Ensure all new files include appropriate headers if required.
