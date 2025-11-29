# Contributing to aiorinnai

Thank you for your interest in contributing to aiorinnai! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/explosivo22/aiorinnai.git
   cd aiorinnai
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aiorinnai --cov-report=term-missing

# Run specific test file
pytest tests/test_base.py -v
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Type checking
mypy aiorinnai
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/). Each commit message should be structured as:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD configuration changes
- `chore`: Other maintenance tasks

### Examples

```
feat(device): add support for scheduling

fix(api): correct token refresh timing

docs: update installation instructions

test(user): add tests for get_info method
```

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Make your changes following the coding standards
3. Add or update tests as needed
4. Ensure all tests pass and code quality checks succeed
5. Update documentation if necessary
6. Submit a pull request with a clear description of changes

## Code Style

- Follow PEP 8 guidelines (enforced by Ruff)
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and concise
- Prefer descriptive variable names

## Questions?

If you have questions, feel free to open an issue for discussion.
