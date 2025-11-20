# CRITICAL (P0) SECURITY & COMPLIANCE TICKETS

## Ticket #1: Implement Password Complexity Validation
**Priority:** P0 - CRITICAL
**Standard:** STANDARD-AUTH-002
**Deadline:** 15 minutes from assignment
**Status:** OPEN

### Description
The system currently does not enforce password complexity requirements during user registration, violating security best practices and compliance requirements.

### Requirements
Implement password validation with the following rules:
- Minimum 8 characters
- Maximum 64 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character (recommended)

### Implementation Details
- Location: `app/routers/auth.py` or create `app/schemas/auth.py`
- Use Pydantic validator
- Provide clear error messages for each validation rule

### Acceptance Criteria
- [ ] Password validator implemented with all requirements
- [ ] Clear error messages for each validation failure
- [ ] Unit tests added for all password validation scenarios
- [ ] Invalid passwords rejected during registration
- [ ] Valid passwords accepted and hashed correctly

### Test Cases
1. Password with <8 chars → Rejected
2. Password without uppercase → Rejected
3. Password without lowercase → Rejected
4. Password without number → Rejected
5. Valid password (8+ chars, upper, lower, number) → Accepted

---

## Ticket #2: Fix Nullable Foreign Keys
**Priority:** P0 - CRITICAL
**Standard:** STANDARD-DB-003
**Deadline:** 15 minutes from assignment
**Status:** OPEN

### Description
Critical data integrity issue: Foreign keys `projects.created_by` and `candidates.created_by` are nullable, which can lead to orphaned records and data integrity violations.

### Current Violations
1. `projects.created_by` (nullable=True) ❌
2. `candidates.created_by` (nullable=True) ❌

### Requirements
- Set `nullable=False` for all foreign key columns
- Add database migration using Alembic
- Handle existing NULL values (either set to system user or admin)

### Implementation Details
- Location: `app/models/__init__.py`
- Create Alembic migration
- Update existing NULL values before applying NOT NULL constraint

### Acceptance Criteria
- [ ] All foreign keys have `nullable=False`
- [ ] Alembic migration created and tested
- [ ] Existing NULL values handled
- [ ] Database constraints enforced
- [ ] Integration tests updated

### Migration Strategy
1. Add default "system" user for orphaned records
2. Update NULL values to system user ID
3. Apply NOT NULL constraint
4. Test rollback procedure

---

## Ticket #3: Implement Soft Delete for Candidates
**Priority:** P0 - CRITICAL
**Standard:** STANDARD-DB-005
**Deadline:** 15 minutes from assignment
**Status:** OPEN

### Description
GDPR compliance violation: The system currently uses hard delete for candidates, which violates data retention and audit trail requirements.

### Requirements
Implement soft delete mechanism for candidates with:
- `deleted_at` (DateTime, nullable=True)
- `deleted_by` (String, FK to users)
- Default filter `WHERE deleted_at IS NULL` on all queries

### Implementation Details
- Location: `app/models/__init__.py` (Candidate model)
- Location: `app/routers/candidates.py` (update delete endpoint)
- Add query filters to exclude soft-deleted records

### Acceptance Criteria
- [ ] Candidate model has `deleted_at` and `deleted_by` fields
- [ ] Alembic migration created
- [ ] Delete endpoint updates `deleted_at` instead of hard delete
- [ ] All list/get queries filter out soft-deleted records
- [ ] Admin endpoint to view deleted candidates (audit trail)
- [ ] GDPR "right to be forgotten" endpoint for hard delete
- [ ] Tests for soft delete functionality

### GDPR Compliance
- Soft delete for audit trail (7 years retention)
- Hard delete endpoint for "right to be forgotten" requests
- Log all deletion events

---

## Ticket #4: Add File Upload Virus Scanning
**Priority:** P0 - CRITICAL
**Standard:** STANDARD-SEC-003
**Deadline:** 15 minutes from assignment
**Status:** OPEN

### Description
Critical security vulnerability: Resume uploads are not scanned for viruses or malware, potentially allowing malicious files into the system.

### Requirements
Implement virus scanning for all file uploads:
- Validate file type (PDF, DOCX only)
- Validate file size (max 5MB)
- Scan with ClamAV or VirusTotal API
- Generate secure random filenames
- Store files with no execution permissions

### Implementation Details
- Location: `app/services/file_upload.py` (create new service)
- Integration: ClamAV daemon or VirusTotal API
- Update: `app/routers/candidates.py` resume upload

### Acceptance Criteria
- [ ] File type validation (MIME type check)
- [ ] File size validation (max 5MB)
- [ ] Virus scanning integration
- [ ] Infected files rejected with error
- [ ] Secure filename generation
- [ ] Files stored with no exec permissions
- [ ] Virus scan results logged
- [ ] Tests for file validation and scanning

### Security Measures
```python
def secure_filename(original_name: str) -> str:
    ext = original_name.split('.')[-1]
    random_name = secrets.token_hex(16)
    return f"{random_name}.{ext}"
```

---

## Ticket #5: Implement HTTPS Enforcement
**Priority:** P0 - CRITICAL
**Standard:** STANDARD-SEC-004
**Deadline:** 15 minutes from assignment
**Status:** OPEN

### Description
Security vulnerability: Production environment does not enforce HTTPS, allowing unencrypted traffic and exposing sensitive data.

### Requirements
- HTTP → HTTPS redirect (301)
- HSTS header (max-age=31536000)
- Secure cookie flag
- Update CORS settings for HTTPS

### Implementation Details
- Location: `app/main.py` (middleware)
- Add HTTPS redirect middleware
- Add security headers
- Update cookie settings

### Acceptance Criteria
- [ ] HTTPS redirect middleware implemented
- [ ] HSTS header added
- [ ] Secure cookie flag enabled
- [ ] CORS updated for HTTPS origins
- [ ] Development environment exception (HTTP allowed)
- [ ] Tests for HTTPS enforcement

### Implementation Example
```python
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

# In main.py
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
```

---

## Summary
- **Total Tickets:** 5
- **Priority:** P0 - CRITICAL
- **Deadline:** 15 minutes per ticket
- **Total Estimated Time:** 75 minutes
- **Blocking Issues:** All tickets block production release
- **Compliance Impact:** GDPR, Security Standards, Data Integrity

## Next Steps
1. Assign developer subagent to each ticket
2. Set up code review checklist
3. Run compliance audit after fixes
4. Update traceability matrix
5. Execute integration tests
