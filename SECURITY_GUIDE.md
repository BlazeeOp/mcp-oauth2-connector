# Security Guide

## Overview

This MCP server implements comprehensive security measures to protect against common web vulnerabilities and ensure secure authentication and data handling. This guide documents all security features and best practices.

## Table of Contents

1. [Authentication & Authorization](#authentication--authorization)
2. [Security Middleware](#security-middleware)
3. [Input Validation](#input-validation)
4. [Rate Limiting](#rate-limiting)
5. [Configuration Security](#configuration-security)
6. [Security Headers](#security-headers)
7. [CORS Protection](#cors-protection)
8. [Error Handling](#error-handling)
9. [Logging Security](#logging-security)
10. [Security Best Practices](#security-best-practices)

## Authentication & Authorization

### AWS Cognito Integration

The server uses AWS Cognito for robust OAuth2 authentication with multiple security layers:

#### JWT Token Validation (`auth/cognito.py`)

**Security Features:**
- **Format Validation**: Validates JWT structure before processing
- **Signature Verification**: Uses RSA keys from AWS JWKS endpoint
- **Expiration Checks**: Validates token expiry and not-before claims
- **Issuer Validation**: Ensures tokens come from the correct Cognito pool
- **Audience Validation**: Validates client_id when present
- **Subject Validation**: Ensures token has a valid subject
- **Token Age Limits**: Rejects tokens older than 24 hours
- **Scope Validation**: Checks required scopes for access tokens

**Key Security Implementation:**
```python
# Comprehensive token validation
payload = jwt.decode(
    token,
    rsa_key,
    algorithms=["RS256"],
    issuer=issuer,
    options={
        "verify_signature": True,
        "verify_exp": True,
        "verify_nbf": True,
        "verify_iat": True,
        "verify_aud": has_audience
    }
)
```

#### OAuth2 Flow (`auth/oauth.py`)

**Security Features:**
- **Dynamic Client Registration**: Secure client detection and registration
- **PKCE Support**: Code Challenge/Verifier for enhanced security
- **Multiple Client Support**: Separate configurations for Claude, Julius, etc.
- **Secure Redirects**: Validated redirect URIs
- **Metadata Endpoints**: Standard OAuth2 discovery

**Supported Grant Types:**
- Authorization Code Flow
- Refresh Token Flow
- PKCE (Proof Key for Code Exchange)

### User Information Extraction

The authentication system extracts and validates user information:

```python
async def get_current_user(credentials, request):
    # Validates bearer token
    # Returns user info: username, email, sub, scopes
    # Provides proper WWW-Authenticate headers
```

## Security Middleware

### Security Headers (`middleware/security.py`)

The server automatically adds comprehensive security headers to all responses:

#### Implemented Headers:

| Header | Value | Purpose |
|--------|--------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS protection |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `Content-Security-Policy` | See CSP section | Prevent code injection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Disable dangerous features |
| `Cache-Control` | `no-store, no-cache, must-revalidate, private` | Prevent caching |

#### Content Security Policy (CSP)

**Production CSP:**
```
default-src 'self'; 
script-src 'self'; 
style-src 'self' 'unsafe-inline'; 
connect-src 'self' https:; 
img-src 'self' data: https:; 
font-src 'self'; 
object-src 'none'; 
media-src 'none'; 
frame-src 'none';
```

**Development CSP:** (More relaxed for development)
```
default-src 'self'; 
script-src 'self' 'unsafe-inline' 'unsafe-eval'; 
style-src 'self' 'unsafe-inline'; 
connect-src 'self' ws: wss:; 
img-src 'self' data: https:; 
font-src 'self' data: https:;
```

## Input Validation

### JWT Token Validation (`utils/validation.py`)

**Format Validation:**
- Validates 3-part structure (header.payload.signature)
- Checks base64url encoding of each part
- Limits token size to 10KB (DoS prevention)

```python
def validate_jwt_token_format(token: str) -> bool:
    # Validates JWT structure and encoding
    # Prevents oversized tokens
    # Returns True/False
```

### MCP Method Validation

**Allowed MCP Methods:**
- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`
- `prompts/list`
- `prompts/get`
- `resources/list`
- `resources/read`

### String Sanitization

```python
def sanitize_string_input(input_str: str, max_length: int = 1000) -> str:
    # Removes control characters
    # Limits string length
    # Strips whitespace
```

## Rate Limiting

### Implementation (`middleware/rate_limiting.py`)

The server implements sophisticated rate limiting using SlowAPI:

#### Default Limits:
- **Global**: 100 requests/minute, 1000 requests/hour
- **OAuth endpoints**: 10 requests/minute
- **Registration**: 5 requests/minute
- **MCP handlers**: 30 requests/minute
- **Health checks**: 100 requests/minute

#### IP Detection:
The rate limiter correctly identifies client IPs through proxies:

```python
def get_real_client_ip(request):
    # Checks X-Forwarded-For header
    # Checks X-Real-IP header
    # Falls back to direct connection IP
```

#### Per-Endpoint Limits:

| Endpoint Type | Rate Limit | Reason |
|---------------|------------|---------|
| OAuth/Auth | 10/min | Prevent brute force |
| Registration | 5/min | Prevent abuse |
| MCP Metadata | 20/min | Moderate usage |
| MCP Handler | 30/min | Normal operations |
| Health Check | 100/min | Monitoring needs |
| Test Endpoints | 5/min | Security testing |

## Configuration Security

### Environment-Based Configuration (`config/settings.py`)

**Security Features:**
- **Required Variable Validation**: Ensures critical variables are set
- **Secure Defaults**: Safe fallback values
- **URL Validation**: Validates JWKS URLs are from AWS
- **Scope Parsing**: Safely parses comma-separated scopes
- **Client Detection**: Secure client identification

#### Required Variables:
- `COGNITO_USER_POOL_ID`
- `COGNITO_CLIENT_ID`
- `COGNITO_REGION`

#### Security Validations:
```python
# JWKS URL validation
if not jwks_url.startswith("https://cognito-idp.") or ".amazonaws.com" not in jwks_url:
    raise ValueError("Invalid JWKS URL")
```

### CORS Configuration

**Security Features:**
- **Whitelist-Only**: No wildcard origins allowed
- **HTTPS Enforcement**: Only HTTPS origins (except localhost in dev)
- **Method Restrictions**: Only GET, POST, OPTIONS
- **Header Restrictions**: Only required headers allowed

**Default Allowed Origins:**
- `https://claude.ai`
- `https://julius.ai`
- `https://api.julius.ai`
- `https://app.julius.ai`

**Development Additions:**
- `http://localhost:6274`
- `http://localhost:3000`
- `http://localhost:8000`
- `http://localhost:8080`

## Security Headers

### Comprehensive Protection

The security middleware adds multiple layers of protection:

1. **MIME Type Sniffing Prevention**: Prevents browsers from guessing content types
2. **Clickjacking Protection**: Prevents embedding in frames
3. **XSS Protection**: Browser-level XSS filtering
4. **HTTPS Enforcement**: Forces secure connections
5. **Content Security Policy**: Prevents code injection
6. **Cache Prevention**: Prevents caching of sensitive data
7. **Server Information Hiding**: Removes server version headers

## Error Handling

### Secure Error Responses (`utils/errors.py`)

**Security Features:**
- **Information Hiding**: Doesn't expose internal details
- **Consistent Responses**: Standardized error format
- **Proper HTTP Status Codes**: Correct status for each error type
- **Logging Integration**: Secure logging of security events

**Error Types Handled:**
- JWT Validation Errors
- Authentication Failures
- Authorization Failures
- Rate Limiting Violations
- Input Validation Errors

## Logging Security

### Secure Logging Practices (`utils/logging_utils.py`)

**Security Features:**
- **Sensitive Data Protection**: Configurable sensitive data logging
- **Request Sanitization**: Cleans log output
- **User Identification**: Safe user identification in logs
- **Security Event Logging**: Comprehensive security event tracking

**Log Levels:**
- **INFO**: Successful operations, user actions
- **WARNING**: Security concerns, invalid requests
- **ERROR**: Security failures, system errors
- **DEBUG**: Detailed debugging (development only)

**Sensitive Data Handling:**
```python
# Controlled by LOG_SENSITIVE_DATA environment variable
if not config["log_sensitive_data"]:
    # Sanitize tokens, user data, etc.
```

## Security Best Practices

### 1. Token Security
- Tokens validated on every request
- Short token lifetimes (24 hours max)
- Proper token format validation
- Secure token transmission (HTTPS only)

### 2. Network Security
- HTTPS enforcement via security headers
- Secure CORS configuration
- Rate limiting on all endpoints
- IP-based access control

### 3. Input Security
- All inputs validated and sanitized
- Method whitelisting for MCP operations
- String length limitations
- Control character removal

### 4. Configuration Security
- Environment-based configuration
- Required variable validation
- Secure defaults
- No hardcoded secrets

### 5. Error Security
- No information leakage in errors
- Consistent error responses
- Proper status codes
- Comprehensive logging

### 6. Operational Security
- Security event logging
- Rate limiting monitoring
- Failed authentication tracking
- Regular security header updates

## Security Monitoring

### Key Metrics to Monitor:

1. **Authentication Failures**: Track failed login attempts
2. **Rate Limit Violations**: Monitor excessive requests
3. **Invalid Token Attempts**: Track malformed tokens
4. **CORS Violations**: Monitor cross-origin violations
5. **Input Validation Failures**: Track malicious inputs

### Log Analysis:

**Security Events to Watch:**
- Multiple authentication failures from same IP
- Rate limit exceeded events
- Invalid JWT token formats
- CORS policy violations
- Unusual MCP method calls

## Security Updates

### Regular Security Maintenance:

1. **Dependency Updates**: Keep all dependencies current
2. **Security Header Review**: Update CSP and other headers
3. **Rate Limit Tuning**: Adjust limits based on usage patterns
4. **CORS Configuration**: Review and update allowed origins
5. **Log Analysis**: Regular review of security logs

### Security Incident Response:

1. **Detection**: Monitor logs for security events
2. **Analysis**: Investigate suspicious activities
3. **Response**: Implement appropriate countermeasures
4. **Recovery**: Restore normal operations
5. **Lessons Learned**: Update security measures

## Compliance and Standards

### Standards Compliance:

- **OAuth 2.0**: RFC 6749 compliance
- **OpenID Connect**: OIDC specification compliance
- **JWT**: RFC 7519 compliance
- **PKCE**: RFC 7636 compliance
- **Security Headers**: OWASP recommendations

### Security Frameworks:

- **OWASP Top 10**: Protection against common vulnerabilities
- **AWS Security**: AWS Cognito security best practices
- **Zero Trust**: Verify every request
- **Defense in Depth**: Multiple security layers

---

This security implementation provides comprehensive protection against common web vulnerabilities while maintaining usability and performance. Regular security reviews and updates ensure continued protection against evolving threats.