# ADR-001: Async I/O & httpx Choice

## Status
Accepted

## Context
The LogSense application requires efficient handling of file I/O operations, HTTP requests to external APIs (OpenAI), and concurrent processing of log analysis tasks. The original implementation used synchronous I/O which caused blocking operations and poor performance under load.

## Decision
We will use async/await patterns throughout the application with:
- `aiofiles` for non-blocking file operations
- `httpx.AsyncClient` for HTTP requests instead of `requests`
- `asyncio.sleep()` instead of `time.sleep()`
- FastAPI's native async support for all endpoints

## Rationale
1. **Performance**: Async I/O prevents blocking the event loop during file operations
2. **Scalability**: Concurrent request handling improves throughput
3. **Resource Efficiency**: Better memory and CPU utilization under load
4. **Modal Compatibility**: Modal's serverless environment benefits from async patterns
5. **Error Handling**: Async patterns allow better timeout and retry control

## Consequences
### Positive
- Non-blocking file uploads and processing
- Improved response times for concurrent users
- Better resource utilization in Modal containers
- Consistent async patterns across the codebase

### Negative
- Increased code complexity with async/await syntax
- All I/O operations must be properly awaited
- Debugging async code can be more challenging

## Implementation Notes
- All file operations use `infra/storage.py` async wrappers
- HTTP requests use `infra/http.py` with retry logic
- Error handling includes proper async cleanup
- Temp files are cleaned up in finally blocks

## Date
2025-08-24
