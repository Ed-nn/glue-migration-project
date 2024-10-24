# Tests Documentation

## Structure
- `unit/`: Unit tests for CDK constructs and configuration
- `integration/`: Integration tests for Glue scripts
- `conftest.py`: Common test fixtures and configurations

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit/
```

### Integration Tests Only
```bash
pytest tests/integration/
```

### With Coverage Report
```bash
pytest --cov=glue_migration_project --cov-report=html
```

## Test Categories

### Unit Tests
- CDK Stack Tests: Verify infrastructure definition
- Config Loader Tests: Verify configuration management
- Utility Function Tests: Verify helper functions

### Integration Tests
- Glue Script Tests: Verify ETL functionality
- End-to-End Tests: Verify complete data flow

## Writing Tests

### Unit Test Example
```python
def test_something():
    # GIVEN
    input_data = ...
    
    # WHEN
    result = function_under_test(input_data)
    
    # THEN
    assert result == expected_result
```

### Integration Test Example
```python
def test_integration(mock_aws_services):
    # GIVEN
    setup_test_data()
    
    # WHEN
    run_process()
    
    # THEN
    verify_results()
```
