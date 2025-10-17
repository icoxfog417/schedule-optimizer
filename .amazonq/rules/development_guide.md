# Development Rules

## Python Execution
- Use `uv run` for all Python commands instead of direct `python` calls
- Examples:
  ```bash
  uv run python main.py
  uv run pytest tests/test_datastore.py -v
  ```

## Testing
- Store all test cases in `tests/` directory
- Use `pytest` for testing framework
- Run tests with: `uv run pytest tests/ -v`

## Temporary Work
- Use `.workspace/` directory for temporary work, analysis, and design documents
- This directory is for development artifacts, not production code
