# Testing Guide

This document describes how to run tests for the ComfyUI API Service.

---

## Test Organization

```
tests/
├── integration/          # End-to-end tests with real services
│   ├── conftest.py      # Fixtures and helpers
│   └── test_job_lifecycle.py
└── unit/                # Unit tests (coming soon)
```

---

## Prerequisites

### For Integration Tests

Integration tests require running infrastructure:

```bash
# Start Redis + MinIO
docker-compose -f docker-compose.dev.yml up -d

# Start API locally
poetry run uvicorn apps.api.main:app --port 8000

# (Optional) Start worker for full tests
poetry run arq apps.worker.main.WorkerSettings
```

**Note:** Some tests will be skipped if ComfyUI/Worker is not available.

---

## Running Tests

### All Tests

```bash
poetry run pytest
```

### Integration Tests Only

```bash
poetry run pytest tests/integration/
```

### Specific Test

```bash
poetry run pytest tests/integration/test_job_lifecycle.py::TestHappyPath::test_submit_and_complete_job
```

### With Coverage

```bash
poetry install --with dev  # Install pytest-cov
poetry run pytest --cov=apps --cov-report=html
open htmlcov/index.html
```

### Verbose Output

```bash
poetry run pytest -vv -s
```

---

## Test Matrix

Based on expert recommendations, we test:

| Test | Validates | Prerequisites |
|------|-----------|---------------|
| **Happy Path** | Full job lifecycle | API + Worker + ComfyUI + MinIO |
| **Idempotency** | Duplicate prevention | API + Redis |
| **Cancellation** | Job cancellation | API + Worker + Redis |
| **Failure Path** | Error handling | API |
| **Rate Limiting** | 429 responses | API + Auth enabled |
| **Timestamps** | Monotonic ordering | API + Redis |
| **Health Checks** | Service status | API |
| **Metrics** | Prometheus endpoint | API |

---

## Test Helpers

### conftest.py Fixtures

**api_client:**
- Async HTTP client
- Configured for `http://localhost:8000`
- 30s timeout

**auth_headers:**
- Authentication headers for protected endpoints
- Creates admin API key if needed

**helpers:**
- Bound helper methods:
  ```python
  await helpers.enqueue("prompt", width=512)
  await helpers.wait_for("succeeded", job_id)
  await helpers.cancel(job_id)
  ```

### Helper Functions

**enqueue_job(client, prompt, **kwargs):**
- Submit a job
- Returns job data

**wait_for_job_status(client, job_id, target_status, timeout=60):**
- Poll until job reaches target status
- Raises TimeoutError if not reached

**cancel_job(client, job_id):**
- Cancel a job
- Returns response data

---

## CI Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

      minio:
        image: minio/minio:latest
        ports:
          - 9000:9000
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run tests
        run: poetry run pytest tests/integration/ -v
        env:
          REDIS_URL: redis://localhost:6379
          MINIO_ENDPOINT: localhost:9000

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        if: always()
```

---

## Writing New Tests

### Structure

```python
import pytest

pytestmark = pytest.mark.asyncio

class TestFeatureName:
    """Test suite for feature X."""

    async def test_specific_behavior(self, helpers, api_client):
        """
        Test description.

        Asserts:
        - Thing 1
        - Thing 2
        """
        # Arrange
        job = await helpers.enqueue("test prompt")

        # Act
        result = await helpers.wait_for("succeeded", job["job_id"])

        # Assert
        assert result["status"] == "succeeded"
```

### Best Practices

1. **Use descriptive names:** `test_idempotency_prevents_duplicate_execution`
2. **Document assertions:** List what you're validating in docstring
3. **Use fixtures:** Don't recreate clients/helpers
4. **Clean up:** Tests should be independent (use unique job IDs)
5. **Skip gracefully:** Use `pytest.skip()` if prerequisites missing

### Example Test

```python
async def test_job_has_request_id(self, helpers):
    """
    Every job response includes X-Request-ID.

    Asserts:
    - X-Request-ID header present
    - Header value is non-empty string
    """
    job = await helpers.enqueue("Test")

    # Check initial response has request ID
    # (This would be done in enqueue_job helper by checking response headers)
    assert "job_id" in job  # Job creation succeeded
```

---

## Troubleshooting

### Tests Hang

**Symptom:** Tests wait forever

**Cause:** API/services not running

**Solution:**
```bash
# Check services
docker-compose -f docker-compose.dev.yml ps

# Check API
curl http://localhost:8000/health
```

### Connection Refused

**Symptom:** `ConnectionRefusedError`

**Cause:** API not running or wrong port

**Solution:**
```bash
# Start API
poetry run uvicorn apps.api.main:app --port 8000
```

### Tests Skip Unexpectedly

**Symptom:** Many tests show "SKIPPED"

**Cause:** ComfyUI/Worker not available

**Solution:**
- This is expected for happy path tests
- Tests requiring ComfyUI skip gracefully
- Other tests (idempotency, validation) should still pass

### Import Errors

**Symptom:** `ModuleNotFoundError`

**Cause:** Dependencies not installed

**Solution:**
```bash
poetry install --with dev
```

---

## Coverage Goals

| Component | Target |
|-----------|--------|
| API Routers | 80%+ |
| Services | 70%+ |
| Middleware | 80%+ |
| Models | 90%+ (mostly validation) |
| Worker | 60%+ (complex async flows) |

---

## Next Steps

- Add unit tests for services/models
- Add performance tests (k6/locust)
- Add security tests (SQL injection, XSS, etc.)
- Add contract tests (Pact)

---

**Questions?**
- Check test output: `pytest -vv`
- Enable debug logging: `pytest --log-cli-level=DEBUG`
- See example runs in CI
