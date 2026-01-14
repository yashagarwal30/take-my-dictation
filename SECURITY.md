# Security Documentation

## Overview

This document outlines the security measures implemented in the Take My Dictation application to protect user data, prevent unauthorized access, and ensure secure payment processing.

## Authentication Security

### Password Security

1. **Password Hashing**
   - Uses bcrypt with cost factor of 12 (strong computational cost)
   - Salted hashing prevents rainbow table attacks
   - Constant-time comparison prevents timing attacks
   - **Location**: `app/core/security.py`

2. **Password Policy**
   - Minimum 8 characters
   - Maximum 128 characters
   - Must contain at least one letter
   - Must contain at least one number
   - **Location**: `app/core/security.py:validate_password_strength()`

3. **Password Storage**
   - Never stored in plain text
   - Only bcrypt hashes stored in database
   - Hashes are one-way (cannot be reversed)

### JWT Token Security

1. **Token Configuration**
   - Algorithm: HS256 (HMAC with SHA-256)
   - Expiration: 7 days
   - Includes claims: `exp` (expiration), `iat` (issued at), `jti` (JWT ID)
   - **Location**: `app/core/security.py`

2. **Secret Key Requirements**
   - Minimum 32 characters enforced
   - Must be cryptographically random
   - Generate using: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Never committed to version control

3. **Token Validation**
   - Signature verification
   - Expiration checking
   - Issuing time validation
   - User ID presence validation

### Rate Limiting

1. **Login Protection**
   - **By IP**: 10 attempts per 15 minutes
   - **By Email**: 5 attempts per 15 minutes
   - Prevents brute force attacks
   - **Location**: `app/api/auth.py:check_rate_limit()`

2. **Registration Protection**
   - **By IP**: 3 attempts per 60 minutes
   - Prevents account creation abuse
   - **Location**: `app/api/auth.py`

3. **Production Recommendation**
   - Current implementation uses in-memory storage
   - For production, use Redis or similar for distributed rate limiting
   - Prevents bypass via multiple servers

### Input Validation

1. **Email Validation**
   - Regex pattern validation
   - Format checking before database operations
   - Case-insensitive storage (lowercased)
   - **Location**: `app/api/auth.py:validate_email()`

2. **Input Sanitization**
   - Removes null bytes
   - Length limiting (max 255 characters)
   - Prevents SQL injection via ORM usage
   - **Location**: `app/api/auth.py:sanitize_input()`

### Security Against Common Attacks

1. **User Enumeration Prevention**
   - Same error message for invalid email and invalid password
   - Constant-time password verification
   - Same response time for existing and non-existing users

2. **Timing Attack Prevention**
   - Bcrypt uses constant-time comparison
   - Password verification doesn't leak information about validity

3. **SQL Injection Prevention**
   - SQLAlchemy ORM with parameterized queries
   - No raw SQL execution with user input

## Payment Security (Stripe)

### Webhook Signature Verification

1. **Critical Security Feature**
   - All webhooks MUST be signature-verified
   - Prevents fraudulent subscription activation
   - Uses Stripe's webhook secret
   - **Location**: `app/api/payments.py:stripe_webhook()`

2. **Implementation**
   ```python
   stripe.Webhook.construct_event(
       payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
   )
   ```

3. **Validation Steps**
   - Verifies webhook secret is configured (min 10 chars)
   - Checks signature header exists
   - Validates signature matches
   - Rejects requests with invalid signatures

### Payment Data Validation

1. **Plan Validation**
   - Whitelisted plan names only
   - Input sanitization (lowercase, strip)
   - Prevents injection of arbitrary data

2. **User Verification**
   - Requires authentication for checkout
   - Validates user exists in database
   - Checks for existing active subscriptions

3. **Stripe Customer Management**
   - Verifies customer exists before reuse
   - Creates new customer if invalid
   - Stores customer ID securely

### PCI Compliance

1. **No Card Data Storage**
   - All card processing handled by Stripe
   - Card data never touches our servers
   - PCI DSS compliance delegated to Stripe

2. **Secure Communication**
   - All Stripe API calls use HTTPS
   - Webhook endpoint should use HTTPS in production
   - API keys stored in environment variables

## Data Protection

### Sensitive Data Handling

1. **User Data**
   - Passwords: bcrypt hashed, never logged
   - Email: stored lowercase, indexed for quick lookup
   - Personal info: sanitized before storage

2. **Stripe Data**
   - Customer IDs: stored but not exposed in API responses
   - Subscription IDs: stored for management
   - Payment methods: never stored, handled by Stripe

3. **API Keys**
   - Stored in environment variables
   - Never exposed in API responses
   - Never logged or committed to git

### Database Security

1. **Connection Security**
   - Uses async PostgreSQL with asyncpg
   - Connection strings stored in environment
   - No hardcoded credentials

2. **Query Security**
   - SQLAlchemy ORM prevents SQL injection
   - Parameterized queries throughout
   - No raw SQL with user input

## API Security

### CORS Configuration

1. **Allowed Origins**
   - Configurable via `CORS_ORIGINS` setting
   - Default: `["http://localhost:3000", "http://localhost:8000"]`
   - Update for production domains
   - **Location**: `app/core/config.py`

2. **Credentials**
   - `allow_credentials=True` for cookie support
   - Only trusted origins should be allowed

### Error Handling

1. **Generic Error Messages**
   - Don't expose internal details
   - Same message for authentication failures
   - Prevents information leakage

2. **Exception Handling**
   - Catches all exceptions
   - Logs details internally
   - Returns safe messages to users

## Frontend Security

### Token Storage

1. **localStorage Usage**
   - JWT token stored in localStorage
   - Vulnerable to XSS attacks
   - **Recommendation**: Consider using httpOnly cookies for production

2. **Token Transmission**
   - Sent via Authorization header
   - Bearer token format
   - HTTPS required in production

### Input Validation

1. **Client-Side Validation**
   - Email format checking
   - Password strength indicators
   - Form validation before submission

2. **Server-Side Validation**
   - Never trust client input
   - All validation repeated on backend
   - Sanitization before processing

## Production Security Checklist

### Before Deployment

- [ ] Generate strong SECRET_KEY (min 32 chars)
- [ ] Use production Stripe keys (not test keys)
- [ ] Set up Stripe webhook endpoint with HTTPS
- [ ] Configure proper CORS_ORIGINS
- [ ] Enable HTTPS/TLS for all endpoints
- [ ] Set DEBUG=False
- [ ] Use strong database passwords
- [ ] Implement proper logging and monitoring
- [ ] Set up Redis for distributed rate limiting
- [ ] Configure backup and disaster recovery
- [ ] Enable database encryption at rest
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Implement intrusion detection
- [ ] Set up security headers (HSTS, CSP, X-Frame-Options)

### Environment Variables Security

**Required Secrets**:
```env
SECRET_KEY=<min-32-char-random-string>
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
STRIPE_SECRET_KEY=sk_live_<your-key>
STRIPE_PUBLISHABLE_KEY=pk_live_<your-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-secret>
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
```

**Security Measures**:
- Never commit .env to git
- Use secret management in production (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly
- Use different keys for dev/staging/production

## Known Limitations & Future Improvements

### Current Limitations

1. **Rate Limiting**
   - In-memory storage (not distributed)
   - Resets on server restart
   - Can be bypassed with multiple IPs

2. **Session Management**
   - No token revocation mechanism
   - Tokens valid until expiration
   - No logout invalidation

3. **Email Verification**
   - Not implemented
   - Users can use fake emails
   - No account activation flow

4. **2FA/MFA**
   - Not implemented
   - Single factor authentication only

5. **Password Reset**
   - Not implemented
   - Users cannot recover accounts

### Recommended Improvements

1. **Implement Token Blacklist**
   - Store revoked tokens in Redis
   - Check on each request
   - Enable proper logout

2. **Add Email Verification**
   - Send verification emails
   - Require activation before use
   - Verify email ownership

3. **Implement 2FA**
   - TOTP support (Google Authenticator)
   - SMS verification option
   - Backup codes

4. **Add Password Reset**
   - Secure token generation
   - Time-limited reset links
   - Email notification

5. **Enhanced Monitoring**
   - Failed login tracking
   - Suspicious activity alerts
   - Real-time security monitoring

6. **Implement HTTPS Everywhere**
   - Force HTTPS in production
   - HSTS headers
   - Secure cookie flags

7. **Add Security Headers**
   ```python
   app.add_middleware(
       SecureHeadersMiddleware,
       hsts=True,
       csp="default-src 'self'",
       x_frame_options="DENY"
   )
   ```

## Security Incident Response

### If Credentials Are Compromised

1. **SECRET_KEY Compromised**
   - Immediately rotate SECRET_KEY
   - Invalidate all active sessions
   - Force all users to re-login
   - Notify users of security incident

2. **Stripe Keys Compromised**
   - Rotate keys in Stripe dashboard
   - Update environment variables
   - Monitor for fraudulent transactions
   - Review all recent payments

3. **Database Breach**
   - Change all database credentials
   - Review access logs
   - Notify affected users
   - Reset all passwords
   - Report to authorities if required

### Contact

For security issues, please email: security@takemydictation.com
DO NOT open public GitHub issues for security vulnerabilities.

## Compliance

### GDPR Considerations

- User data deletion: Not yet implemented
- Data export: Partially implemented (via exports)
- Consent tracking: Not implemented
- Data retention policies: Not defined

### CCPA Considerations

- Data disclosure: Need to implement
- Data deletion requests: Need to implement
- Opt-out mechanisms: Not implemented

## Regular Security Audits

### Recommended Schedule

- **Daily**: Review failed login attempts
- **Weekly**: Check for suspicious activity
- **Monthly**: Review access logs
- **Quarterly**: Security audit and penetration testing
- **Annually**: Full security assessment

### Tools Recommendations

- **SAST**: Bandit, Safety (Python security)
- **DAST**: OWASP ZAP, Burp Suite
- **Dependency Scanning**: Snyk, Dependabot
- **Container Scanning**: Trivy, Clair

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Stripe Security Best Practices](https://stripe.com/docs/security/guide)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Password Hashing](https://passlib.readthedocs.io/)
