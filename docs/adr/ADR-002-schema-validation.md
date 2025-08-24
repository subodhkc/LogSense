# ADR-002: Schema Validation at Input Boundaries

## Status
Accepted

## Context
The LogSense application processes user-uploaded log files and accepts form data through various endpoints. Without proper input validation, the application is vulnerable to malformed data, injection attacks, and processing failures. We need consistent validation at all input boundaries.

## Decision
We will implement comprehensive schema validation using:
- FastAPI's built-in Pydantic models for request validation
- Custom validation functions in `infra/security.py`
- Content-Type enforcement for all endpoints
- File size and type validation for uploads
- Input sanitization to prevent XSS attacks

## Rationale
1. **Security**: Prevent injection attacks and malformed input processing
2. **Reliability**: Catch invalid data early before processing
3. **User Experience**: Provide clear error messages for invalid inputs
4. **Compliance**: Meet enterprise security requirements
5. **Maintainability**: Centralized validation logic

## Implementation
### Request Validation
- JSON endpoints enforce `Content-Type: application/json`
- Upload endpoints enforce `Content-Type: multipart/form-data`
- Request size limits: 25MB for uploads, 1MB for JSON
- Standardized error codes (E.REQ.001, E.REQ.002, etc.)

### File Validation
- Allowed extensions: `.log`, `.txt`, `.zip`
- Maximum file size: 25MB
- Content scanning for malicious patterns
- Temporary file cleanup after processing

### Input Sanitization
- HTML/script tag removal from text inputs
- Email and token redaction in logs
- Path traversal prevention
- SQL injection pattern detection

## Consequences
### Positive
- Improved security posture
- Better error handling and user feedback
- Consistent validation across all endpoints
- Reduced processing failures from bad data

### Negative
- Additional processing overhead for validation
- More complex error handling logic
- Stricter input requirements may affect usability

## Error Code Taxonomy
- `E.REQ.001`: Invalid Content-Type
- `E.REQ.002`: File too large
- `E.REQ.003`: Invalid file type
- `E.REQ.004`: Missing required field
- `E.SRV.001`: Processing failed
- `E.SEC.001`: Unauthorized access

## Date
2025-08-24
