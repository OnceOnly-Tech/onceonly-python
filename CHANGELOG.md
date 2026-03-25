# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [3.0.4] - 2026-03-25
- Added run debug SDK methods:
  - `post_event(...)` / `post_event_async(...)` -> `POST /v1/events`
  - `get_run_timeline(...)` / `get_run_timeline_async(...)` -> `GET /v1/runs/{run_id}`
- Added high-level wrappers `ai_run(...)` / `ai_run_async(...)` on `OnceOnly`.
- Added `run_id` support in AI high-level calls (`ai.run*`, `ai.run_tool*`, `ai.run_and_wait*`):
  - key mode -> auto-injected into `metadata.run_id`
  - tool mode -> auto-injected into `args.run_id`
- Extended `events(...)` / `events_async(...)` with optional `offset`.
- Added run-debug example: `examples/ai/run_debug_timeline.py`.
- Added failure-debug SDK example: `examples/ai/run_debug_failure.py`.

## [3.0.3] - 2026-03-10
- Updated repository links after migration to GitHub org `OnceOnly-Tech/onceonly-python`.
- Updated package metadata repository URL used by PyPI project links.

## [3.0.2] - 2026-02-07
- Documentation updates (README links and references).
- Minor client compatibility improvements (base_url normalization, clearer 403 feature gating).

## [3.0.1] - 2026-02-04
- Added Tools Registry methods to the SDK (create/list/get/toggle/delete).
- Added tool-runner and full LLM agent flow examples.
- Added plan limits and Pro vs Agency notes in docs.
- Added integration smoke tests and tools registry tests.
- Added release checks script.

## [3.0.0] - 2026-02-04
- Initial 3.0.0 release.
