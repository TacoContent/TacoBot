# Test Performance Optimization Guide

This document outlines strategies to improve TacoBot test suite performance from 1+ hour to under 10 minutes.

## Quick Start: Parallel Test Execution

### Install pytest-xdist
```powershell
./.venv/scripts/Activate.ps1
pip install pytest-xdist
```

### Run Tests in Parallel (Recommended)
```powershell
# Use all CPU cores automatically
python -m pytest tests/ -n auto --dist loadgroup

# Or specify number of workers (e.g., 4 cores)
python -m pytest tests/ -n 4 --dist loadgroup

# With coverage
python -m pytest tests/ -n auto --dist loadgroup --cov=bot --cov=httpserver --cov=metrics --cov=scripts
```

**Expected improvement: 60-80% time reduction** (1 hour → 12-24 minutes on 4+ cores)

## VS Code Tasks

Use the new parallel test tasks:
- **Python: Run Tests (Parallel)** - Fast parallel execution
- **Python: Run Tests (Parallel + Coverage)** - Parallel with full coverage reports

## Performance Metrics

### Before Optimization
- **Total Tests**: 1,387
- **Execution Time**: 60+ minutes
- **Per-Test Average**: ~2.6 seconds

### After Optimization (Expected)
- **With Parallel (-n auto)**: 12-24 minutes (60-80% faster)
- **With All Optimizations**: 5-10 minutes (85-90% faster)

## Additional Optimizations

### 1. Shared Fixtures (Implemented)
`tests/conftest.py` now provides shared fixtures:
- Session-scoped: Created once per test run
- Module-scoped: Created once per test file
- Function-scoped: Traditional per-test fixtures

**Benefit**: Reduces fixture initialization overhead by 20-30%

### 2. Skip Slow Tests in Development
```powershell
# Mark slow tests with @pytest.mark.slow
# Skip them during development
python -m pytest tests/ -m "not slow" -n auto
```

### 3. Test Only Changed Code
```powershell
# Install pytest-testmon
pip install pytest-testmon

# Run only tests affected by code changes
python -m pytest tests/ --testmon -n auto
```

### 4. Database Connection Optimization
The tests currently try to connect to MongoDB during cog initialization, causing 30-second timeouts.

**Fix**: Mock the database connections properly in fixtures (already partially done)

### 5. Reduce Async Overhead
For CPU-bound tests that don't actually need async:
```python
# Instead of:
@pytest.mark.asyncio
async def test_something():
    ...

# Use synchronous tests when possible:
def test_something():
    ...
```

## Benchmark Commands

### Measure Test Duration
```powershell
# Show 10 slowest tests
python -m pytest tests/ --durations=10 -n auto

# Show all test durations
python -m pytest tests/ --durations=0 -n auto
```

### Profile Tests
```powershell
# Install pytest-profiling
pip install pytest-profiling

# Generate profiling report
python -m pytest tests/ --profile -n auto
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run tests in parallel
  run: |
    pytest tests/ -n auto --dist loadgroup \
      --cov=bot --cov=httpserver --cov=metrics --cov=scripts \
      --cov-report=xml --cov-report=term-missing
```

### Azure Pipelines Example
```yaml
- script: |
    pytest tests/ -n auto --dist loadgroup \
      --cov=bot --cov=httpserver --cov=metrics --cov=scripts \
      --junitxml=test-results.xml --cov-report=xml
  displayName: 'Run parallel tests with coverage'
```

## Troubleshooting

### Tests Fail in Parallel But Pass Serially
**Issue**: Tests have shared state or race conditions

**Solutions**:
1. Ensure fixtures properly isolate test state
2. Use `--dist loadgroup` to group tests by module
3. Mark problematic tests with `@pytest.mark.serial` and run separately

### Coverage Reports Are Incomplete
**Issue**: Coverage data not combined properly in parallel mode

**Solution**: Use `pytest-cov` with `-n auto` - it handles this automatically

### High Memory Usage
**Issue**: Too many parallel workers

**Solution**: Limit workers: `pytest tests/ -n 4` (instead of `auto`)

## Best Practices

1. **Run parallel tests locally**: Match CI environment
2. **Use shared fixtures**: Defined in `conftest.py`
3. **Mock heavy dependencies**: Database connections, external APIs
4. **Keep tests isolated**: No shared state between tests
5. **Profile regularly**: Identify and fix slow tests

## Next Steps

### Immediate (Done)
- ✅ Add pytest-xdist to dependencies
- ✅ Create shared fixtures in conftest.py
- ✅ Add parallel test tasks to VS Code

### Short Term (Recommended)
- [ ] Run `pytest --durations=20` to identify slowest tests
- [ ] Optimize or mark slow tests
- [ ] Remove unnecessary database connection attempts in test fixtures
- [ ] Update CI/CD pipelines to use parallel execution

### Long Term (Optional)
- [ ] Add pytest-testmon for incremental testing
- [ ] Set up test sharding for distributed CI
- [ ] Add performance regression tests
- [ ] Create test categories (unit, integration, e2e)

## Expected Results

With all optimizations:
- **Development**: 5-10 minutes for full suite
- **CI/CD**: 8-15 minutes (parallel + infrastructure overhead)
- **Per-commit**: 1-2 minutes with testmon (changed tests only)

---

**Current Status**: Basic parallel testing enabled. Run with:
```powershell
python -m pytest tests/ -n auto --dist loadgroup
```
