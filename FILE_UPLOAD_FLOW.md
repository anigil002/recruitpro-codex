# File Upload Flow in RecruitPro - Comprehensive Documentation

## Overview

When a file is uploaded to a project in RecruitPro, it triggers a complete workflow from the frontend UI through backend processing, database operations, and asynchronous AI analysis. This document provides a detailed walkthrough of every component involved.

---

## 1. FRONTEND UPLOAD INITIATION

### Location
- **File**: `/home/user/recruitpro-codex/templates/project_page.html`
- **Lines**: 383-840 (JavaScript event handlers)

### Upload Components

#### 1.1 Document Upload Form
**HTML Element ID**: `document-upload-form` (lines 383-414)

```html
<form id="document-upload-form" enctype="multipart/form-data">
  <input id="document-upload-file" name="file" type="file" required>
  <input id="document-upload-name" name="display_name" type="text" placeholder="Project brief.pdf">
  <button type="submit">Upload to project</button>
</form>
```

**User Action**:
1. Click "Upload document" link (line 229)
2. Scroll to form in project sidebar
3. Select file from file picker
4. Optional: Enter display name
5. Click "Upload to project" button

#### 1.2 Candidate CV Upload Form
**HTML Element ID**: `candidate-cv-form` (lines 464-540)

This form uploads a resume file and simultaneously creates a candidate record. It follows similar patterns but with additional fields.

### Frontend JavaScript Handler

**Event Listener**: `documentForm.addEventListener("submit", ...)` (lines 810-840)

**Process Flow**:

```
1. Form submit event triggered
2. Prevent default form submission
3. Validate: File selected && file exists
4. Extract file data:
   - displayName = form field or file.name
   - mimeType = file.type or "application/octet-stream"
5. Build FormData object:
   - filename: displayName
   - mime_type: mimeType
   - scope: "project"
   - scope_id: PROJECT_ID
   - file: file blob
6. Call apiFetch("/api/documents/upload", {method: "POST", body: formData})
7. On success:
   - Clear form
   - Show success feedback
   - Refresh document list via refreshDocuments()
8. On error:
   - Show error feedback message
```

**Key JavaScript Functions**:

- `apiFetch(path, options)` (lines 641-673): HTTP client with auth header management
- `setButtonLoading(button, loading)` (lines 784-805): UI state management
- `refreshDocuments(feedbackTarget)` (lines 773-782): Fetch latest documents
- `renderDocuments(docs)` (lines 745-771): Render document list to DOM

---

## 2. API ENDPOINT - FILE UPLOAD

### Location
- **File**: `/home/user/recruitpro-codex/app/routers/documents.py`
- **Endpoint**: `POST /api/documents/upload`
- **Lines**: 44-126

### Request Parameters

```python
@router.post("/documents/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    filename: str = Form(...),                    # Display name
    mime_type: str = Form(...),                   # MIME type
    scope: str = Form(...),                       # "project" or other scope
    scope_id: str | None = Form(None),            # Project ID if scope="project"
    file: UploadFile = File(...),                 # File binary data
    db: Session = Depends(get_db),                # Database session
    current_user=Depends(get_current_user),       # Authenticated user
) -> DocumentRead:
```

### Processing Steps

#### Step 1: Validate Scope & Permissions (Lines 54-59)
```python
storage_dir = ensure_storage_dir()
project = None
if scope == "project":
    if not scope_id:
        raise HTTPException(status_code=400, detail="scope_id required")
    ensure_project_access(db.get(Project, scope_id), current_user)
```
- Ensures storage directory exists
- Validates that user has access to target project
- Raises 400 error if project scope without scope_id
- Raises 403/404 error if user lacks permission

#### Step 2: Save File to Disk (Lines 61-65)
```python
safe_name = Path(file.filename).name          # Sanitize original filename
file_id = generate_id()                        # Generate unique ID (UUID)
file_path = storage_dir / f"{file_id}_{safe_name}"  # Create path
with file_path.open("wb") as buffer:
    buffer.write(file.file.read())             # Write bytes to disk
```

**Storage Details**:
- **Directory**: Configured in `settings.storage_path` (default: `./storage`)
- **Path Resolution**: `/home/user/recruitpro-codex/app/utils/storage.py` handles path safety
- **Filename Format**: `{unique_id}_{original_filename}`
- **Purpose of ID**: Prevents collisions and enables unique tracking

#### Step 3: Create Document Database Record (Lines 68-76)
```python
relative_path = file_path.relative_to(storage_dir)
document = Document(
    id=file_id,
    filename=filename,                    # User-provided display name
    mime_type=mime_type,
    file_url=str(relative_path),          # Relative path from storage root
    scope=scope,                          # "project"
    scope_id=scope_id,                    # Project ID
    owner_user=current_user.user_id,
)
db.add(document)
```

**Database Table**: `documents` table
**Key Fields**:
- `id`: Primary key, unique file identifier
- `filename`: Human-readable display name
- `file_url`: Relative filesystem path
- `scope`: Scope type ("project")
- `scope_id`: Associated project ID
- `owner_user`: User who uploaded
- `uploaded_at`: Timestamp (auto-set to current UTC time)

#### Step 4: Create Project-Specific Document Link (Lines 79-89)
```python
project_doc_id = None
if scope == "project" and scope_id:
    project_doc = ProjectDocument(
        doc_id=file_id,                   # Reference to document
        project_id=scope_id,              # Project association
        filename=filename,
        file_url=str(relative_path),
        mime_type=mime_type,
        uploaded_by=current_user.user_id,
    )
    db.add(project_doc)
    project_doc_id = project_doc.doc_id
```

**Database Table**: `project_documents` table
**Purpose**: Maintains many-to-many relationship and project-specific metadata
**Key Fields**:
- `doc_id`: Primary key, reference to document
- `project_id`: Foreign key to project
- `filename`, `file_url`, `mime_type`: Denormalized from document
- `uploaded_by`: User who performed upload
- `uploaded_at`: Timestamp

#### Step 5: Log Activity (Lines 91-97)
```python
log_activity(
    db,
    actor_type="user",
    actor_id=current_user.user_id,
    message=f"Uploaded document {document.filename}",
    event_type="document_uploaded",
)
```

**Database Table**: `activity_feed` table
**Purpose**: Audit trail and activity timeline in UI
**Recorded Information**:
- Who uploaded (user ID)
- What was uploaded (filename)
- When (timestamp)
- Event type: `"document_uploaded"`

#### Step 6: Create AI Analysis Job (Lines 99-111)
```python
job_request = {
    "document_id": file_id,
    "project_id": scope_id,
    "user_id": current_user.user_id,
}
if project_doc_id:
    job_request["project_document"] = True
job = create_ai_job(
    db,
    "file_analysis",
    project_id=scope_id,
    request=job_request,
)
```

**Database Table**: `ai_jobs` table
**Job Creation Details**:
- **Job Type**: `"file_analysis"`
- **Status**: Initially `"pending"`
- **Request JSON**: Contains document_id, project_id, user_id, and project_document flag
- **Created At**: Current UTC timestamp

#### Step 7: Commit Changes Before Queuing (Line 114)
```python
db.commit()
```

**Critical Step**: Documentation states this ensures the worker can access:
- The new document record
- The project-document linkage
- The job record
- All in a fresh database session

**Comment in Code**:
```python
# Commit before queuing the background job so the worker can access the
# new document, project linkage, and job record in a fresh session.
```

#### Step 8: Enqueue Background Job (Line 115)
```python
background_queue.enqueue("file_analysis", {"job_id": job.job_id})
```

**Queue Implementation**: `/home/user/recruitpro-codex/app/services/queue.py`
**Type**: In-process thread-based queue (emulates RQ/Celery)
**Payload**: Dictionary with `job_id`

#### Step 9: Return Response (Lines 117-126)
```python
return DocumentRead(
    id=document.id,
    filename=document.filename,
    mime_type=document.mime_type,
    file_url=document.file_url,
    scope=document.scope,
    scope_id=document.scope_id,
    owner_user=document.owner_user,
    uploaded_at=document.uploaded_at,
)
```

**Response Status**: `201 Created`
**Response Body**: DocumentRead schema with all document metadata

---

## 3. STORAGE MECHANISM

### Location
- **File**: `/home/user/recruitpro-codex/app/utils/storage.py`

### Storage Path Configuration

**Default Path**: `./storage`
**Environment Variable**: `RECRUITPRO_STORAGE_PATH`
**Configuration**: `/home/user/recruitpro-codex/app/config.py` (lines 49, 98-104)

```python
storage_path: str = Field(default="storage")

@field_validator("storage_path", mode="before")
@classmethod
def _normalize_storage_path(cls, value: str | None) -> str:
    candidate = Path(value) if value else APP_ROOT / "storage"
    if not candidate.is_absolute():
        candidate = (APP_ROOT / candidate).resolve()
    return str(candidate)
```

**Resolution**:
- Relative paths are resolved relative to app root
- Absolute paths are used as-is
- Directory is automatically created if missing

### File Safety Functions

#### `ensure_storage_dir()`
```python
def ensure_storage_dir() -> Path:
    base = Path(settings.storage_path).resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base
```
**Purpose**: Ensures storage directory exists, creates if needed

#### `resolve_storage_path(file_path)`
```python
def resolve_storage_path(file_path: str) -> Path:
    base = Path(settings.storage_path).resolve()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = base / candidate
    # ... path validation ...
    resolved.relative_to(base)  # Raises ValueError if outside storage
    return resolved
```
**Purpose**: 
- Safely resolve file paths
- Prevent directory traversal attacks
- Validate path stays within storage directory

### Static File Serving

**Location**: `/home/user/recruitpro-codex/app/main.py` (lines 105-113)

```python
from .utils.storage import ensure_storage_dir

storage_dir = ensure_storage_dir()
storage_path = storage_dir
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")
```

**URL Pattern**: `/storage/{relative_path}`
**Example**: `/storage/abc123def_project_brief.pdf`

---

## 4. BACKGROUND QUEUE SYSTEM

### Queue Implementation

**Location**: `/home/user/recruitpro-codex/app/services/queue.py`
**Type**: Thread-based in-process queue
**Purpose**: Emulate RQ/Celery for background job processing

### BackgroundQueue Class

```python
class BackgroundQueue:
    def __init__(self):
        self._queue: "Queue[tuple[str, Dict[str, Any]]]" = Queue()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._thread: Optional[Thread] = None
        self._stop = Event()
```

**Key Methods**:
- `register_handler(job_type, handler)`: Register job type handler
- `enqueue(job_type, payload)`: Queue a job
- `start()`: Start worker thread
- `shutdown()`: Stop worker thread
- `stats()`: Get queue statistics

### Worker Thread

**Operation**: Daemon thread named "recruitpro-worker"

```python
def _run(self):
    while not self._stop.is_set():
        try:
            job_type, payload = self._queue.get(timeout=0.5)
        except Empty:
            continue
        handler = self._handlers.get(job_type)
        if not handler:
            logging.warning("No handler registered for job type %s", job_type)
            continue
        try:
            handler(payload)
            # Update stats: increment processed count
        except Exception:
            logging.exception("Background job %s failed", job_type)
            # Update stats: increment failed count
```

**Behavior**:
1. Continuously polls queue with 0.5s timeout
2. Retrieves job_type and payload
3. Looks up registered handler
4. Executes handler
5. Tracks success/failure statistics
6. Updates last_job and last_error

### Job Statistics

Accessible via `background_queue.stats()`:
```python
{
    "queued": int,          # Jobs in queue
    "handlers": [str],      # Registered handler names
    "is_running": bool,
    "processed": int,       # Total successful jobs
    "failed": int,          # Total failed jobs
    "last_job": dict,       # Last job executed
    "last_error": str,      # Last error message
    "last_updated": str,    # ISO timestamp
}
```

### Queue Initialization

**Location**: `/home/user/recruitpro-codex/app/services/queue.py` (lines 118-119)

```python
background_queue = BackgroundQueue()
background_queue.start()
```

**Startup**: Singleton instance created and started when module loads

---

## 5. AI FILE ANALYSIS JOB

### Handler Registration

**Location**: `/home/user/recruitpro-codex/app/services/ai.py` (line 321)

```python
background_queue.register_handler("file_analysis", _handle_file_analysis_job)
```

### Handler Function

**Location**: `/home/user/recruitpro-codex/app/services/ai.py` (lines 88-171)
**Function**: `_handle_file_analysis_job(payload)`

### Process Flow

#### Phase 1: Setup & Validation (Lines 89-105)

```python
job_id = payload["job_id"]
with get_session() as session:
    job = session.get(AIJob, job_id)
    if not job:
        return
    mark_job_running(session, job)  # Set job status to "running"
    
    # Extract request parameters
    request = job.request_json or {}
    document_id = request.get("document_id")
    
    # Fetch document from appropriate table
    document = session.get(ProjectDocument, document_id) if request.get("project_document") else None
    if not document:
        document = session.get(Document, document_id)
    if not document:
        mark_job_failed(session, job, "Document not found")
        return
```

**Status Updates**:
- `mark_job_running()`: Changes job status from "pending" to "running"
- `mark_job_failed()`: Sets status to "failed" with error message

#### Phase 2: Load Project Context (Lines 106-109)

```python
project_id = request.get("project_id") or getattr(document, "project_id", None)
if not project_id and getattr(document, "scope", None) == "project":
    project_id = getattr(document, "scope_id", None)
project = session.get(Project, project_id) if project_id else None
```

**Purpose**: Retrieve project for contextual analysis

#### Phase 3: Resolve File Path (Lines 110-114)

```python
try:
    path = resolve_storage_path(document.file_url)
except ValueError:
    mark_job_failed(session, job, "Document path outside storage directory")
    return
```

**Security Check**: Validates path safety before analysis

#### Phase 4: AI Analysis (Lines 115-128)

```python
analysis = gemini.analyze_file(
    path,
    original_name=document.filename,
    mime_type=document.mime_type,
    project_context={
        "name": getattr(project, "name", None),
        "summary": getattr(project, "summary", None),
        "sector": getattr(project, "sector", None),
        "location_region": getattr(project, "location_region", None),
        "client": getattr(project, "client", None),
    } if project else {},
)
```

**Analysis Service**: `/home/user/recruitpro-codex/app/services/gemini.py`
**AI Model**: Gemini (Google's Generative Language API)

**Analysis Returns**:
```python
{
    "document_type": str,           # e.g., "job_description", "project_brief"
    "project_info": {               # Extracted project metadata
        "name": str,
        "summary": str,
        "sector": str,
        "location_region": str,
        "client": str,
    },
    "positions": [                  # Extracted job positions
        {
            "title": str,
            "department": str,
            "experience": str,
            "responsibilities": [str],
            "requirements": [str],
            "location": str,
            "description": str,
            "status": str,
        },
    ],
    "market_research_recommended": bool,
}
```

#### Phase 5: Update Project Metadata (Lines 129-136)

```python
if project and analysis["project_info"]:
    info = analysis["project_info"]
    for field in ("name", "summary", "sector", "location_region", "client"):
        value = info.get(field)
        if value:
            setattr(project, field, value)
    session.add(project)
```

**Updates**: Project table with extracted information
**Fields Modified**: name, summary, sector, location_region, client
**Condition**: Only updates if analysis provided values

#### Phase 6: Create Draft Positions (Lines 137-159)

```python
if project:
    from ..models import Position
    
    existing_titles = {pos.title.lower() for pos in project.positions if pos.title}
    for role in analysis["positions"]:
        title = (role.get("title") or "").strip()
        if not title or title.lower() in existing_titles:
            continue
        position = Position(
            position_id=generate_id(),
            project_id=project.project_id,
            title=title,
            department=role.get("department"),
            experience=role.get("experience"),
            responsibilities=role.get("responsibilities") or [],
            requirements=role.get("requirements") or [],
            location=role.get("location"),
            description=role.get("description"),
            status=role.get("status") or "draft",
        )
        session.add(position)
```

**Database Table**: `positions` table
**Status**: All created positions have status = "draft"
**Deduplication**: Checks existing titles to prevent duplicates

#### Phase 7: Mark Job Complete (Line 160)

```python
mark_job_completed(session, job, analysis)
```

**Update Details**:
- Sets job status to "completed"
- Stores analysis results in `response_json`
- Sets `updated_at` timestamp
- Publishes realtime event

#### Phase 8: Log Activity (Lines 162-169)

```python
if project:
    log_activity(
        session,
        actor_type="ai",
        actor_id=request.get("user_id"),
        project_id=project.project_id,
        message=f"Analyzed {analysis.get('document_type', 'document')} {document.filename}",
        event_type="file_analyzed",
    )
```

**Database Table**: `activity_feed` table
**Purpose**: Record AI analysis in project activity timeline

#### Phase 9: Trigger Market Research (Lines 170-171)

```python
if analysis.get("market_research_recommended") and not project.research_done:
    enqueue_market_research_job(session, project.project_id, request.get("user_id"))
```

**Trigger Condition**: Only if AI recommends and not already done
**Next Queue Job**: "market_research" job enqueued
**Purpose**: Generate market research insights for the project

---

## 6. DATABASE OPERATIONS SUMMARY

### Tables Involved

#### `documents`
**Purpose**: Global document registry
**Fields**:
- `id` (PK): Unique identifier
- `filename`: Display name
- `file_url`: Relative filesystem path
- `mime_type`: Content type
- `owner_user` (FK): User who uploaded
- `scope`: Scope type ("project")
- `scope_id`: Associated entity ID
- `uploaded_at`: Timestamp

#### `project_documents`
**Purpose**: Project-specific document association
**Fields**:
- `doc_id` (PK): Document reference
- `project_id` (FK): Associated project
- `filename`: Display name (denormalized)
- `file_url`: Filesystem path (denormalized)
- `mime_type`: Content type (denormalized)
- `uploaded_by` (FK): User who uploaded
- `uploaded_at`: Timestamp

#### `projects`
**Purpose**: Project metadata
**Fields Modified by Upload**:
- `name`: Updated from analysis
- `summary`: Updated from analysis
- `sector`: Updated from analysis
- `location_region`: Updated from analysis
- `client`: Updated from analysis

#### `positions`
**Purpose**: Job position records
**Records Created**: For each position extracted from document
**Status**: Always "draft" initially
**Fields Populated**:
- `title`, `department`, `experience`
- `responsibilities`, `requirements`
- `location`, `description`

#### `ai_jobs`
**Purpose**: Background job tracking
**Fields**:
- `job_id` (PK): Unique job ID
- `job_type`: "file_analysis"
- `project_id` (FK): Associated project
- `status`: "pending" → "running" → "completed"/"failed"
- `request_json`: Input parameters
- `response_json`: Analysis results
- `error`: Error message if failed
- `created_at`, `updated_at`: Timestamps

#### `activity_feed`
**Purpose**: Audit trail and activity timeline
**Records Created**: Two entries
1. Upload event: `event_type="document_uploaded"`
2. Analysis event: `event_type="file_analyzed"`

---

## 7. SIDE EFFECTS & TRIGGERED PROCESSES

### Immediate Effects (Synchronous)

1. **File Saved to Disk**
   - Location: `{storage_path}/{file_id}_{original_filename}`
   - Permissions: Default file system permissions
   - Accessibility: Served via `/storage/` static file mount

2. **Database Records Created**
   - Document entry in `documents` table
   - ProjectDocument entry in `project_documents` table
   - AIJob entry in `ai_jobs` table
   - ActivityFeed entry (upload event)

3. **API Response Returned**
   - Status: 201 Created
   - Body: DocumentRead with all document metadata

### Delayed Effects (Asynchronous)

1. **Background Job Queued**
   - Type: "file_analysis"
   - Payload: `{"job_id": <ai_job_id>}`
   - Execution: Seconds to minutes later (depends on queue)

2. **AI Analysis Performed**
   - Model: Google Gemini
   - Input: File content + project context
   - Output: Document analysis with extracted metadata

3. **Project Metadata Updated**
   - Fields: name, summary, sector, location_region, client
   - Source: AI extraction from document
   - Condition: Only if AI found values

4. **Positions Created**
   - One position per role found in document
   - Status: "draft"
   - Fields: title, department, experience, responsibilities, requirements, location, description

5. **Activity Recorded**
   - Event: "file_analyzed"
   - Actor: AI service
   - Purpose: Audit trail

6. **Market Research Triggered** (Conditional)
   - Condition: AI recommends AND not already done
   - Type: "market_research" background job
   - Purpose: Generate market insights

---

## 8. ERROR HANDLING

### Frontend Validation

**File Selection**: Required field validation
```javascript
if (!fileInput || !fileInput.files || !fileInput.files.length) {
    showFeedback(documentFeedback, "error", "Choose a file before uploading.");
    return;
}
```

### API Validation

**Missing Scope ID**:
```python
if not scope_id:
    raise HTTPException(status_code=400, detail="scope_id required")
```

**Unauthorized Access**:
```python
ensure_project_access(db.get(Project, scope_id), current_user)
# Raises 403 if no permission, 404 if project not found
```

### Background Job Error Handling

**Document Not Found**:
```python
if not document:
    mark_job_failed(session, job, "Document not found")
    return
```

**Invalid File Path**:
```python
try:
    path = resolve_storage_path(document.file_url)
except ValueError:
    mark_job_failed(session, job, "Document path outside storage directory")
    return
```

**AI Analysis Failure**:
```python
except Exception:  # In queue handler
    logging.exception("Background job %s failed", job_type)
    # Job status set to "failed", error logged
```

---

## 9. SECURITY CONSIDERATIONS

### File Storage Security
- **Path Safety**: All paths validated to stay within storage directory
- **Directory Traversal Prevention**: `resolve_storage_path()` validates relative_to()
- **Unique Naming**: UUIDs prevent collision and enumeration attacks

### Access Control
- **Authentication**: All endpoints require authenticated user
- **Project Authorization**: `ensure_project_access()` verifies user has project access
- **File Ownership**: Document tied to uploader via `owner_user`

### File Handling
- **Filename Sanitization**: `Path(file.filename).name` extracts safe name
- **MIME Type Tracking**: Stored for content type validation
- **Safe Reading**: File read via secure context manager

### AI Processing
- **Path Validation**: File path validated before passing to AI service
- **Sandboxing**: Analysis performed in isolated job process

---

## 10. TESTING & MONITORING

### Queue Statistics
Monitor via `background_queue.stats()`:
- `queued`: Current queue depth
- `processed`: Total successful jobs
- `failed`: Total failed jobs
- `last_job`: Last job executed with status
- `last_error`: Latest error if any

### Activity Timeline
View in UI via `activity_feed` table:
- Upload events (actor_type="user")
- Analysis events (actor_type="ai")
- All with timestamps and messages

### Job Status Tracking
Monitor via `ai_jobs` table:
- `status`: pending/running/completed/failed
- `error`: Error message if failed
- `response_json`: Analysis results if completed
- `updated_at`: Last status change

---

## 11. CANDIDATE CV UPLOAD VARIANT

The candidate CV upload flow (`candidate-cv-form`) extends the document upload:

1. **Upload Resume**: Same `/api/documents/upload` endpoint
2. **Extract URL**: `uploaded.file_url` → `/storage/...`
3. **Create Candidate**: POST `/api/candidates` with:
   - `name`: Provided by user
   - `project_id`: Current project
   - `position_id`: Optional, from form
   - `resume_url`: File URL
   - `source`: "Resume upload"
   - `status`: "new"

This creates an initial candidate record linked to the uploaded resume file.

---

## 12. DOCUMENT RETRIEVAL & SERVING

### List Project Documents
**Endpoint**: `GET /api/projects/{project_id}/documents`
**Returns**: Array of DocumentRead objects for project

### Download Document
**Endpoint**: `GET /api/documents/{doc_id}/download`
**Returns**: FileResponse with file blob
**Security**: Validates ownership/project access

### Stream Document
**Endpoint**: `GET /api/documents/{doc_id}/file`
**Returns**: StreamingResponse with chunked reading (8KB chunks)
**Use Case**: View inline (PDFs, images)

### Delete Document
**Endpoint**: `DELETE /api/documents/{doc_id}`
**Actions**:
1. Resolves file path
2. Deletes from filesystem
3. Deletes ProjectDocument record
4. Deletes Document record
5. Logs activity

---

## 13. CONFIGURATION & DEPLOYMENT

### Environment Variables
- `RECRUITPRO_STORAGE_PATH`: File storage directory (default: `./storage`)
- `RECRUITPRO_GEMINI_API_KEY`: Google Gemini API key
- `RECRUITPRO_DATABASE_URL`: Database connection string

### Storage Directory Setup
- Created automatically if missing
- Must be writable by application process
- Recommended: Persistent volume if containerized

### Queue Initialization
- Automatically started on app startup (main.py lifespan)
- Handlers registered when services.ai module loads
- Shutdown gracefully on app termination

---

## 14. COMPLETE SEQUENCE DIAGRAM

```
User (Browser)
    │
    ├─→ [1] Click "Upload document"
    │
    ├─→ [2] Select file & enter name
    │
    ├─→ [3] Submit form
    │
    └─→ [4] POST /api/documents/upload (FormData)
         │
         └─→ Backend (documents.py: upload_document)
              │
              ├─→ [5] Validate auth & project access
              │
              ├─→ [6] Save file to disk
              │       Location: {storage_path}/{uuid}_{filename}
              │
              ├─→ [7] Insert Document record
              │
              ├─→ [8] Insert ProjectDocument record
              │
              ├─→ [9] Insert ActivityFeed record (upload)
              │
              ├─→ [10] Insert AIJob record (pending)
              │
              ├─→ [11] db.commit()
              │
              ├─→ [12] Enqueue "file_analysis" background job
              │
              └─→ [13] Return 201 DocumentRead
                       ↑
    ┌──────────────────┘
    │
    └─→ [14] Show success message & refresh document list
         │
         └─→ GET /api/projects/{project_id}/documents
              │
              └─→ Render updated document list in UI


Background Worker Thread (Async)
    │
    ├─→ [15] Dequeue "file_analysis" job
    │
    ├─→ [16] Fetch AIJob (status: pending)
    │
    ├─→ [17] Set status to "running"
    │
    ├─→ [18] Fetch Document from disk
    │
    ├─→ [19] Call gemini.analyze_file()
    │        │
    │        ├─→ [20] Send file to Gemini API
    │        │
    │        └─→ [21] Receive analysis results
    │                 - document_type
    │                 - project_info
    │                 - positions[]
    │                 - market_research_recommended
    │
    ├─→ [22] Update Project metadata (name, summary, sector, etc.)
    │
    ├─→ [23] Create Position records for extracted roles
    │        Each with status="draft"
    │
    ├─→ [24] Set AIJob status to "completed", store response_json
    │
    ├─→ [25] Insert ActivityFeed record (file_analyzed)
    │
    ├─→ [26] Publish realtime event (job completed)
    │
    └─→ [27] If market_research_recommended:
             Enqueue "market_research" background job
```

---

## 15. KEY FILES REFERENCE

| Component | File | Key Functions/Classes |
|-----------|------|----------------------|
| **Frontend** | `/templates/project_page.html` | Document upload form (lines 383-414), submit handler (lines 810-840) |
| **API Endpoint** | `/app/routers/documents.py` | `upload_document()` (lines 44-126) |
| **Storage** | `/app/utils/storage.py` | `ensure_storage_dir()`, `resolve_storage_path()` |
| **Queue** | `/app/services/queue.py` | `BackgroundQueue` class, worker thread |
| **AI Handler** | `/app/services/ai.py` | `_handle_file_analysis_job()` (lines 88-171) |
| **AI Service** | `/app/services/gemini.py` | `gemini.analyze_file()` |
| **Models** | `/app/models/__init__.py` | `Document`, `ProjectDocument`, `AIJob`, `Position` |
| **Configuration** | `/app/config.py` | Storage path setup (lines 49, 98-104) |
| **Main App** | `/app/main.py` | Storage mounting (lines 105-113), queue handler registration |

---

## Summary

The file upload flow in RecruitPro is a comprehensive workflow that:

1. **Captures** user file selection and metadata on frontend
2. **Validates** authentication and authorization
3. **Persists** file to disk with safety checks and unique naming
4. **Records** document metadata in database
5. **Tracks** in project-specific relationships
6. **Queues** background AI analysis job
7. **Commits** transaction before async work
8. **Executes** AI analysis in separate thread
9. **Extracts** project info, job positions, and recommendations
10. **Updates** project records with insights
11. **Creates** draft positions for recruiting
12. **Records** audit trail throughout
13. **Triggers** follow-up tasks (market research)
14. **Provides** file access through secure endpoints

All with comprehensive error handling, security validation, and activity logging.
