# CI/CD Fixes Required

## Current Issues

### 1. Test Failures - Import Errors
**Status**: FIXED in conftest.py
- Added `services/landing-page` to `sys.path` in conftest.py
- Tests can now import from `src` package

### 2. Missing Dependencies in CI Environment
**Status**: NEEDS GITHUB ACTIONS UPDATE

The CI workflow needs to install all dependencies before running tests.

**Fix Required in `.github/workflows/ci.yml`:**

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install pytest pytest-cov pytest-timeout pytest-mock
    # Install ALL requirements, not just test tools
    pip install -r services/landing-page/requirements.txt
```

### 3. Linting Setup
**Status**: READY TO TEST

Flake8 shows no critical errors locally. The linting job should pass once dependencies are installed.

## To Fix CI/CD

1. Update `.github/workflows/ci.yml` to install full requirements.txt
2. Push changes
3. CI should pass

## Local Testing

To run tests locally:

```bash
# Install dependencies
pip install -r services/landing-page/requirements.txt

# Run unit tests
pytest -m unit

# Run linting
flake8 services/landing-page/src --count --select=E9,F63,F7,F82
black --check services/landing-page/src
```
