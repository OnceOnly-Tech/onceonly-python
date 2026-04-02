# Contributing

Thanks for contributing to OnceOnly Python SDK.

## Scope

This repository contains the Python SDK for OnceOnly API.
Please keep changes focused on:

- SDK correctness and API compatibility
- clear errors and predictable behavior
- tests, examples, and docs aligned with code

## Prerequisites

- Python 3.9+
- `venv` (recommended)

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

If editable install is not needed:

```bash
pip install -r requirements-dev.txt
```

## Development Commands

Run unit tests:

```bash
pytest -q
```

Run integration smoke tests (live API):

```bash
export TEST_API_KEY="once_live_..."
export TEST_BASE_URL="https://api.onceonly.tech"
pytest -q -m integration
```

## Coding Guidelines

- Preserve backward compatibility for public SDK methods when possible.
- Keep naming and behavior aligned with backend API contracts.
- Prefer explicit typing and simple, readable control flow.
- Do not silently swallow errors that should reach SDK users.
- Update examples/docs when public behavior changes.

## Pull Request Checklist

- [ ] Tests added or updated for behavior changes.
- [ ] `pytest -q` passes locally.
- [ ] Public API changes documented in `README.md`.
- [ ] `CHANGELOG.md` updated for user-visible changes.
- [ ] No unrelated refactors bundled into the same PR.

## Commit Guidance

- Use focused commits with clear titles.
- Keep one logical change per commit when possible.

## Reporting Issues

When opening an issue, include:

- SDK version
- Python version
- minimal reproducible snippet
- expected vs actual behavior
- backend response/status (if available)

For security-sensitive reports, contact: `support@onceonly.tech`.
