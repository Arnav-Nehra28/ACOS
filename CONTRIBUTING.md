# Contributing to ACOS

Thank you for your interest in contributing to the Automative Cognitive Orchestration System!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Arnav-Nehra28/ACOS.git
   cd ACOS
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r test-requirements.txt
   ```

3. Create your `.env` file with at least one LLM API key.

4. Run tests:
   ```bash
   pytest -q acos_api/test_service.py acos_models/test_schema.py
   ```

## Pull Request Guidelines

- Ensure all tests pass before submitting a PR
- Follow existing code style and conventions
- Update documentation for any new features
- Keep commits focused and well-described

## Reporting Issues

Open a GitHub issue with:
- A clear description of the bug or feature request
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Environment details (OS, Python version, Docker version)

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.
