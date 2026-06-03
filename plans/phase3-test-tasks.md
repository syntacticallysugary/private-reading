# Phase 3: Integration - Test Task List

## Document Information

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0.0 | 2026-04-22 | QA Lead | Draft |

## Phase 3 Scope Summary

Phase 3 assembles all Phase 2 core components into a cohesive processing pipeline with:
- **Task 3.1**: [`ProcessingPipeline`](private_reading/core/pipeline.py) - Orchestration layer
- **Task 3.2**: [`JobTracker`](private_reading/core/job_tracker.py) - Job state management
- **Task 3.3**: [`PrivateReadingApp`](private_reading/app.py) - Application entry point
- **Task 3.4**: [`CLI Interface`](private_reading/cli.py) - Command-line interface
- **Task 3.5**: Integration tests in [`test_pipeline_integration.py`](tests/core/test_pipeline_integration.py)
- **Task 3.6**: Error handling in [`exceptions.py`](private_reading/exceptions.py)

## Pre-Conditions (Definition of Ready)

- [x] Phase 1 complete (project setup, dependencies, configuration)
- [x] Phase 2 complete (all 6 core components implemented and unit-tested)
- [x] All Phase 2 unit tests passing
- [x] Code structure exists for all Phase 3 files

## Critical Bugs Found During Discovery (Pre-Testing)

During my code audit, I identified the following **pre-existing defects** that will cause test failures:

| Bug ID | File | Line | Severity | Description |
|--------|------|------|----------|-------------|
| D-001 | [`pipeline.py`](private_reading/core/pipeline.py:156) | 156 | CRITICAL | `_retry_with_backoff` uses undefined type variable `T` - will raise `NameError` |
| D-002 | [`pipeline.py`](private_reading/core/pipeline.py:154) | 154 | CRITICAL | `job_tracker` is `None` placeholder - `PrivateReadingApp` never injects it into pipeline |
| D-003 | [`app.py`](private_reading/app.py:43) | 43 | CRITICAL | `config.get()` called on Pydantic model - `AppConfig` has no `.get()` method |
| D-004 | [`app.py`](private_reading/app.py:50) | 50 | CRITICAL | Same `.get()` issue for `watch_mode` |
| D-005 | [`app.py`](private_reading/app.py:245-250) | 245-250 | CRITICAL | `_parse_arguments` uses dict-style access on Pydantic model |
| D-006 | [`app.py`](private_reading/app.py:260) | 260 | HIGH | `self.config.get("version")` - same dict access issue |
| D-007 | [`cli.py`](private_reading/cli.py:178-189) | 178-189 | HIGH | CLI stores voice/watch as `_voice`/`_watch_mode` private attrs - app doesn't read them |
| D-008 | [`pipeline.py`](private_reading/core/pipeline.py:327) | 327 | MEDIUM | Sidecar metadata uses `len(audio_chunks)` for duration - counts chunks not seconds |
| D-009 | [`pipeline.py`](private_reading/core/pipeline.py:319) | 319 | HIGH | `audio_chunks[0]` used for `save_wav` - should use stitched output |
| D-010 | [`app.py`](private_reading/app.py:169) | 169 | MEDIUM | `result.__dict__` passes internal fields (`success`, `error`) to job result |
| D-011 | [`app.py`](private_reading/app.py:98-99) | 98-99 | CRITICAL | Single file mode checks `self.config.get()` then `self.config["single_file"]` - inconsistent access |
| D-012 | [`pipeline.py`](private_reading/core/pipeline.py:502-530) | 502-530 | LOW | Health checks use bare `try/except` that masks real errors |

## Test Task Assignments

### Task 3T1: Verify ProcessingPipeline Integration (Task 3.1)

**Assignee:** @QA_Tester
**Dependencies:** None
**Estimated Duration:** 2 hours

**Test Objectives:**
1. Verify `ProcessingPipeline` class instantiation with `AppConfig`
2. Verify all 6 Phase 2 components are properly instantiated
3. Verify `process_file()` 7-step workflow
4. Verify `process_directory()` batch processing
5. Verify `get_status()` returns `PipelineStatus`
6. Verify retry decorator functionality
7. Verify `ProcessingResult` dataclass behavior
8. Verify `PipelineStatus` dataclass behavior

**Acceptance Criteria:**
- All pipeline component initialization tests pass
- End-to-end file processing works with mocked TTS
- Directory processing returns correct result list
- Status reporting returns valid state

**Known Defects Affecting This Task:** D-001, D-002, D-008, D-009, D-012

---

### Task 3T2: Verify JobTracker Implementation (Task 3.2)

**Assignee:** @QA_Tester
**Dependencies:** None
**Estimated Duration:** 1.5 hours

**Test Objectives:**
1. Verify `JobTracker` instantiation with/without persistence
2. Verify `create_job()` returns unique UUIDs
3. Verify state transitions: PENDING → PROCESSING → COMPLETED
4. Verify state transitions: PENDING → PROCESSING → FAILED
5. Verify invalid state transitions are rejected
6. Verify `get_job()`, `list_jobs()`, `get_jobs_by_status()`
7. Verify persistence: `save_history()` and `load_history()`
8. Verify thread safety with concurrent access

**Acceptance Criteria:**
- All state transitions follow valid paths
- UUIDs are unique across jobs
- Persistence round-trips correctly
- Thread-safe operations

**Known Defects Affecting This Task:** D-002 (pipeline never injects job_tracker)

---

### Task 3T3: Verify PrivateReadingApp Implementation (Task 3.3)

**Assignee:** @QA_Tester
**Dependencies:** Task 3T1, Task 3T2
**Estimated Duration:** 1.5 hours

**Test Objectives:**
1. Verify `PrivateReadingApp` initialization with `AppConfig`
2. Verify pipeline and job_tracker initialization
3. Verify `run()` method startup flow
4. Verify `process_single_file()` job lifecycle
5. Verify `health_check()` returns correct structure
6. Verify signal handler setup
7. Verify `_parse_arguments()` argument parsing
8. Verify `_setup_logging()` configuration

**Acceptance Criteria:**
- Application initializes all components
- Single file processing creates job lifecycle
- Health check returns expected structure
- Signal handlers registered correctly

**Known Defects Affecting This Task:** D-003, D-004, D-005, D-006, D-010, D-011

---

### Task 3T4: Verify CLI Interface (Task 3.4)

**Assignee:** @QA_Tester
**Dependencies:** Task 3T3
**Estimated Duration:** 1 hour

**Test Objectives:**
1. Verify `--help` output contains all arguments
2. Verify `-i/--input` required argument validation
3. Verify `-o/--output` required argument validation
4. Verify `-c/--config` optional config file
5. Verify `--voice` voice ID override
6. Verify `--chunk-size` override with validation
7. Verify `--overlap-ratio` override with validation
8. Verify `-v/--verbose` enables debug logging
9. Verify `-w/--watch` enables watch mode
10. Verify input path existence validation
11. Verify output directory writability validation

**Acceptance Criteria:**
- `python -m private_reading --help` shows usage
- Invalid inputs show helpful error messages
- CLI arguments override config defaults
- Path validation works correctly

**Known Defects Affecting This Task:** D-007

---

### Task 3T5: Verify Error Handling & Exception Hierarchy (Task 3.6)

**Assignee:** @QA_Tester
**Dependencies:** None
**Estimated Duration:** 1 hour

**Test Objectives:**
1. Verify exception hierarchy: `PrivateReadingError` base class
2. Verify `ExtractionError`, `TextExtractionError`, `UnsupportedFormatError`
3. Verify `ChunkingError`
4. Verify `TTSError`, `TTSAPIError`
5. Verify `AudioError`, `AudioProcessingError`
6. Verify `OutputError`
7. Verify `PipelineError`
8. Verify pipeline catches component-specific exceptions
9. Verify error logging with context
10. Verify retry logic for transient errors

**Acceptance Criteria:**
- All exception classes properly defined
- Exception inheritance hierarchy correct
- Pipeline handles each exception type appropriately
- Error messages are actionable

**Known Defects Affecting This Task:** None directly, but tests will reveal D-001, D-008, D-009

---

### Task 3T6: Run Full Integration Test Suite

**Assignee:** @QA_Tester
**Dependencies:** Tasks 3T1-3T5
**Estimated Duration:** 2 hours

**Test Objectives:**
1. Run existing integration tests: `tests/core/test_pipeline_integration.py`
2. Run all existing tests: `pytest tests/ -v`
3. Verify test coverage report
4. Identify all test failures and categorize by root cause
5. Document which failures are due to pre-existing defects vs. test gaps

**Acceptance Criteria:**
- All tests that can pass are passing
- All failures are documented with root cause analysis
- Test coverage meets minimum thresholds

**Known Defects Affecting This Task:** All previously identified defects

---

## Execution Strategy

| Phase | Tasks | Estimated Duration | Notes |
|-------|-------|-------------------|-------|
| T1 | 3T1: ProcessingPipeline | 2 hours | Foundation - test first |
| T2 | 3T2: JobTracker | 1.5 hours | Can run in parallel with T1 |
| T3 | 3T3: PrivateReadingApp | 1.5 hours | Depends on T1, T2 |
| T4 | 3T4: CLI Interface | 1 hour | Depends on T3 |
| T5 | 3T5: Error Handling | 1 hour | Can run in parallel with T1-T4 |
| T6 | 3T6: Full Suite | 2 hours | Depends on T1-T5 |

**Recommended Order:** T1 + T2 (parallel) → T3 + T5 (parallel) → T4 → T6

## Defect Tracking Template

When bugs are found, log them using this format:

```
Bug ID: [auto-increment]
File: [file path]
Line: [line number]
Severity: [CRITICAL/HIGH/MEDIUM/LOW]
Category: [Bug/Design/Performance/Security]
Description: [what's wrong]
Expected: [what should happen]
Actual: [what actually happens]
Reproduction: [how to reproduce]
```
