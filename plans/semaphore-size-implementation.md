# Semaphore Size Implementation Plan

## Overview

This document outlines the implementation of a configurable `SEMAPHORE_SIZE` feature for the myaudible application. The semaphore will control the maximum number of concurrent TTS requests, with a default value of 10 (based on sweep test results) and the ability to be configured via the `.env` file.

## Design Decisions Confirmed

1. **Global Semaphore**: A single `asyncio.Semaphore` instance is created once per application lifecycle and shared across all processing operations
2. **Fail-Fast Behavior**: Invalid semaphore values (≤0 or >50) cause immediate application failure rather than silent clamping or warnings

## Current State Analysis

### Sweep Test Pattern
The sweep test (`sweep.py`) demonstrates the semaphore implementation pattern:

```python
async def run_sweep(chunks, concurrency, tts_client):
    sem = asyncio.Semaphore(concurrency)
    
    async def timed_generate(chunk):
        start = time.perf_counter()
        async with sem:
            await tts_client.generate_speech(chunk)
        end = time.perf_counter()
        return end - start
    
    latencies = await asyncio.gather(*(timed_generate(c) for c in chunks))
```

This pattern:
1. Creates an `asyncio.Semaphore` with the specified concurrency limit
2. Uses `async with sem:` to acquire/release the semaphore for each request
3. Wraps the TTS call to limit concurrent execution

### Current Processing Flow
The current `ProcessingPipeline.process_file()` method processes TTS requests **sequentially**:

```python
for i, chunk in enumerate(chunks):
    audio_data = await self.tts_client.generate_speech(chunk)
```

## Implementation Strategy

### Component Changes Required

#### 1. Configuration Layer (`myaudible/config.py`)

**Add `SemaphoreConfig` class** to handle the semaphore size configuration:

```python
class SemaphoreConfig(BaseSettings):
    """Semaphore configuration for controlling concurrency."""
    
    size: int = 10  # Default to optimal value from sweep test
    min_value: int = 1
    max_value: int = 50
    
    @model_validator(mode='after')
    def validate_semaphore_size(self):
        if self.size < self.min_value or self.size > self.max_value:
            raise ValueError(f"SEMAPHORE_SIZE must be between {self.min_value} and {self.max_value}")
        return self
    
    class Config:
        env_prefix = "SEMAPHORE_"
```

**Update `AppConfig`** to include the new `semaphore` configuration.

#### 2. Pipeline Layer (`myaudible/core/pipeline.py`)

**Update `ProcessingPipeline.__init__()`** to create the semaphore from config:

```python
def __init__(self, config: AppConfig):
    self.semaphore = asyncio.Semaphore(config.semaphore.size)
```

**Update `process_file()`** method to use the semaphore when processing TTS chunks:

**Current code (sequential):**
```python
async with self.tts_client:
    for i, chunk in enumerate(chunks):
        audio_data = await self.tts_client.generate_speech(chunk)
```

**New code (concurrent with semaphore):**
```python
async with self.tts_client:
    async def process_chunk(chunk):
        async with self.semaphore:
            return await self.tts_client.generate_speech(chunk)
    
    audio_chunks = await asyncio.gather(*(process_chunk(chunk) for chunk in chunks))
```

#### 3. CLI Layer (`myaudible/cli.py`)

**Add command-line override** for `--semaphore-size` to allow runtime configuration.

**Update `build_config()`** to pass semaphore size from CLI args.

#### 4. Environment Variables

**Add to `.env` and `.env.example`:**

```bash
# ── Concurrency Control ────────────────────────────────────────────────────
# Maximum concurrent TTS requests (based on sweep test, default: 10)
# Valid range: 1-50
SEMAPHORE_SIZE=10
```

## Configuration Flow

```
CLI arg (--semaphore-size) 
    → Environment variable (SEMAPHORE_SIZE) 
    → Default (10)
```

## Data Flow Diagram

```mermaid
graph TD
    A[User/Config] -->|SEMAPHORE_SIZE| B[Config Loading]
    B -->|10 or env value| C[SemaphoreConfig]
    C --> D[AppConfig]
    D --> E[ProcessingPipeline.__init__]
    E -->|Creates| F[asyncio.Semaphore(semaphore_size)]
    F --> G[ProcessingPipeline.process_file]
    G -->|Uses| F
    G -->|Controls| H[TTS Chunk Processing]
    H -->|Semaphore-acquire| I[generate_speech]
    I -->|Semaphore-release| H
```

## Implementation Steps

### Phase 1: Configuration Changes
1. Add `SemaphoreConfig` to `myaudible/config.py` with validation
2. Update `AppConfig` to include semaphore configuration
3. Add `SEMAPHORE_SIZE` to `.env` and `.env.example`

### Phase 2: Pipeline Changes
1. Update `ProcessingPipeline.__init__()` to create semaphore from config
2. Refactor `process_file()` to use semaphore for concurrent TTS calls
3. Add CLI argument `--semaphore-size` to `cli.py`

### Phase 3: Testing
1. Verify semaphore limits concurrent TTS calls
2. Test with various semaphore sizes
3. Confirm backward compatibility with default value

## Error Handling Considerations

### Input Validation
- Validate semaphore size is between 1 and 50 (inclusive)
- Invalid values cause application to fail immediately (fail-fast)
- No silent clamping or default fallback for invalid inputs

### Error Scenarios
1. **Semaphore size 0 or negative**: Fail immediately with error message
2. **Semaphore size > 50**: Fail immediately with error message
3. **TTS service unavailable**: Semaphore should still limit retry attempts

## Testing Strategy

### Unit Tests
- Verify semaphore is created with correct size from config
- Verify semaphore limits concurrent operations
- Test CLI argument parsing
- Test validation of invalid values

### Integration Tests
- Test with semaphore_size=1 (sequential, baseline)
- Test with semaphore_size=10 (expected optimal)
- Test with semaphore_size=50 (stress test)
- Verify concurrent request limiting

### Performance Tests
- Compare total processing time with different semaphore values
- Verify throughput scales appropriately up to optimal point

## Migration Notes

### Backward Compatibility
- Default value of 10 ensures existing behavior from sweep test
- No breaking changes to existing APIs
- Optional CLI override maintains flexibility

### Deployment Notes
- Update `.env.example` with new variable
- Document semaphore tuning guidelines
- Consider TTS service rate limits when choosing value

## Future Enhancements

1. **Dynamic semaphore adjustment**: Monitor TTS service health and adjust concurrency
2. **Per-endpoint semaphore**: Different limits for different TTS endpoints
3. **Resource-based limiting**: Adjust based on CPU/memory usage
4. **Circuit breaker**: Automatically reduce concurrency on service degradation

## Success Criteria

1. ✅ Semaphore can be configured via `.env` file
2. ✅ Default value is 10 (optimal from sweep test)
3. ✅ CLI override works for runtime testing
4. ✅ Concurrent TTS requests are properly limited
5. ✅ Application stability maintained across different semaphore values
6. ✅ Invalid values (≤0 or >50) cause fail-fast behavior

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `myaudible/config.py` | Add | `SemaphoreConfig` class with validation |
| `myaudible/config.py` | Modify | Integrate `semaphore` into `AppConfig` |
| `myaudible/core/pipeline.py` | Modify | Create `asyncio.Semaphore` in `__init__()` |
| `myaudible/core/pipeline.py` | Modify | Refactor `process_file()` for concurrent TTS |
| `myaudible/cli.py` | Modify | Add `--semaphore-size` argument |
| `myaudible/cli.py` | Modify | Update `build_config()` to pass semaphore size |
| `.env` | Add | `SEMAPHORE_SIZE=10` |
| `.env.example` | Add | `SEMAPHORE_SIZE=10` with documentation |
