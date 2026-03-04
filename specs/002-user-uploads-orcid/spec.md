# Feature Specification: User Uploads with ORCID Authentication

**Feature Branch**: `002-user-uploads-orcid`  
**Created**: 2026-03-04  
**Status**: Draft  
**Input**: Enable users to upload their own h5ad files with ORCID OAuth authentication and visibility controls.

## Overview

This feature extends CellXGene Explorer to allow researchers to upload and manage their own single-cell datasets. Users authenticate via ORCID (standard academic identity) and can control whether their datasets are public, unlisted, or private.

### Why ORCID?

- **Standard in academia**: Most researchers already have an ORCID iD
- **No password management**: OAuth means we don't store credentials
- **Trusted identity**: ORCID verification provides accountability
- **Persistent identifier**: 16-digit ORCID iD is stable across institutions

### Design Principles

1. **Zero friction for existing users**: Public dataset browsing remains anonymous
2. **Auth only when needed**: ORCID login required only for uploads and managing private data
3. **SQLite storage**: Single-file database for users, datasets, and access control—simple to backup and manage
4. **Graceful degradation**: If ORCID is unreachable, existing functionality still works

---

## User Scenarios & Testing

### User Story 1 - ORCID Authentication (Priority: P1) 🎯 MVP

Researchers need to authenticate using their ORCID credentials to establish identity for uploads.

**Why this priority**: Authentication is the foundation for ownership—without identity, we can't attribute uploads or enforce visibility.

**Acceptance Scenarios**:

1. **Given** a user is on the landing page, **When** they click "Sign in with ORCID", **Then** they are redirected to ORCID's authorization page
2. **Given** a user has authorized the app on ORCID, **When** ORCID redirects back, **Then** the user is logged in and sees their ORCID iD displayed
3. **Given** a user is logged in, **When** they click "Sign out", **Then** their session is cleared and they return to anonymous browsing
4. **Given** a user denies authorization on ORCID, **When** redirected back, **Then** they see a clear message and can retry or continue anonymously

---

### User Story 2 - Dataset Upload (Priority: P1) 🎯 MVP

Authenticated researchers need to upload h5ad files that become associated with their ORCID identity.

**Why this priority**: This is the core new capability—without uploads, ORCID auth has no purpose.

**Acceptance Scenarios**:

1. **Given** a user is authenticated, **When** they navigate to "My Datasets", **Then** they see an upload form and list of their datasets
2. **Given** a user selects a valid h5ad file (≤10GB), **When** they submit the upload, **Then** the file is uploaded with progress indication and validated
3. **Given** a file passes validation, **When** upload completes, **Then** the user sees the dataset in their list with a success message
4. **Given** a file fails validation, **When** upload completes, **Then** the user sees specific error messages explaining what's wrong
5. **Given** a user uploads without authentication, **When** they try to submit, **Then** they are prompted to sign in with ORCID first

---

### User Story 3 - Visibility Controls (Priority: P1) 🎯 MVP

Dataset owners need to control who can access their uploaded datasets.

**Why this priority**: Visibility is essential for pre-publication data—researchers won't upload if they can't protect unpublished work.

**Visibility Levels**:
- **Public**: Listed in main catalog, accessible to everyone
- **Unlisted**: Not in catalog, but accessible via direct link (for sharing with collaborators/reviewers)
- **Private**: Only visible to the owner (for work in progress)

**Acceptance Scenarios**:

1. **Given** a user uploads a dataset, **When** the upload completes, **Then** the default visibility is "Private"
2. **Given** a user views their dataset, **When** they change visibility to "Public", **Then** the dataset appears in the main catalog
3. **Given** a dataset is "Unlisted", **When** the owner copies the share link, **Then** anyone with that link can view the dataset
4. **Given** a dataset is "Private", **When** an unauthenticated user tries the direct URL, **Then** they receive a 404 (not 403, to avoid revealing existence)

---

### User Story 4 - Dataset Management (Priority: P2)

Dataset owners need to manage their uploaded datasets (edit metadata, delete).

**Why this priority**: Management is important but not blocking—users can re-upload initially.

**Acceptance Scenarios**:

1. **Given** a user owns a dataset, **When** they click "Edit", **Then** they can modify display name, description, and metadata
2. **Given** a user owns a dataset, **When** they click "Delete" and confirm, **Then** the dataset and file are permanently removed
3. **Given** a user does not own a dataset, **When** they try to access edit/delete, **Then** they receive an authorization error

---

### User Story 5 - My Datasets Dashboard (Priority: P2)

Authenticated users need a unified view of all their datasets with status information.

**Acceptance Scenarios**:

1. **Given** a user is authenticated, **When** they visit "/my-datasets", **Then** they see all their uploads with visibility status
2. **Given** a user has datasets, **When** viewing the dashboard, **Then** they see upload date, view count, and current visibility
3. **Given** a user has no datasets, **When** viewing the dashboard, **Then** they see a helpful prompt to upload their first dataset

---

### Edge Cases

- What if a user's ORCID account is deactivated? (Datasets remain, ownership based on stored ORCID iD)
- What if the same file is uploaded twice? (Allow it—user might want different visibility settings)
- What if ORCID OAuth is temporarily unavailable? (Show error, allow anonymous browsing)
- What if upload fails mid-stream? (Clean up partial files, show retry option)
- What happens to datasets if we need to migrate users? (ORCID iD is portable)
- How do we handle very large files during upload? (Chunked upload with progress)

---

## Requirements

### Functional Requirements

- **FR-100**: System MUST support OAuth 2.0 authentication with ORCID using the `/authenticate` scope
- **FR-101**: System MUST store user identity as ORCID iD (16-digit format: 0000-0001-2345-6789)
- **FR-102**: System MUST maintain user sessions using secure, signed Flask sessions
- **FR-103**: System MUST allow sign-out that clears all session data
- **FR-104**: System MUST gracefully handle ORCID OAuth failures without breaking anonymous access
- **FR-105**: System MUST allow anonymous (unauthenticated) browsing and exploration of all public and curated datasets
- **FR-106**: System MUST NOT require login to view, filter, search, or launch CellXGene for public datasets

- **FR-110**: System MUST accept h5ad file uploads up to 10GB in size
- **FR-111**: System MUST validate uploaded files are valid AnnData objects before accepting
- **FR-112**: System MUST associate uploaded datasets with the uploader's ORCID iD
- **FR-113**: System MUST store uploaded files in a user-namespaced directory structure
- **FR-114**: System MUST show upload progress for large files
- **FR-115**: System MUST clean up partial uploads on failure
- **FR-116**: System MUST support chunked uploads for files >1GB to handle network interruptions
- **FR-117**: System SHOULD support resumable uploads (resume from last successful chunk)

- **FR-120**: System MUST support three visibility levels: public, unlisted, private
- **FR-121**: System MUST default new uploads to "private" visibility
- **FR-122**: System MUST include public user datasets in the main catalog
- **FR-123**: System MUST generate shareable links for unlisted datasets
- **FR-124**: System MUST return 404 (not 403) for unauthorized private dataset access
- **FR-125**: System MUST allow only dataset owners to change visibility

- **FR-130**: System MUST allow dataset owners to edit metadata (name, description)
- **FR-131**: System MUST allow dataset owners to delete their datasets
- **FR-132**: System MUST require confirmation before dataset deletion
- **FR-133**: System MUST provide a "My Datasets" dashboard for authenticated users

### Database Requirements

- **FR-140**: System MUST use SQLite for all metadata, users, and access control
- **FR-141**: System MUST store the database at `data/cellxgene.db`
- **FR-142**: System MUST auto-create database and tables on first startup
- **FR-143**: System MUST migrate existing JSON data (access_grants.json, shareable_links.json) to SQLite on upgrade
- **FR-144**: System MUST use transactions for all multi-step operations
- **FR-145**: System MUST support schema versioning for future migrations

### Non-Functional Requirements

- **NFR-100**: OAuth flow MUST complete within 30 seconds under normal conditions
- **NFR-101**: Upload progress MUST update at least every 5 seconds
- **NFR-102**: File validation MUST complete within 5 minutes for 10GB files
- **NFR-103**: System MUST support at least 5 concurrent uploads

### Security Requirements

- **SR-100**: System MUST NOT store ORCID access tokens beyond the session
- **SR-101**: System MUST validate OAuth state parameter to prevent CSRF
- **SR-102**: System MUST use HTTPS for all ORCID OAuth communication
- **SR-103**: System MUST sanitize uploaded filenames to prevent path traversal
- **SR-104**: System MUST scan uploaded files for basic structural validity (not arbitrary code execution)

---

## Technical Design

### ORCID OAuth 2.0 Flow

```
┌─────────┐                    ┌─────────────┐                    ┌─────────┐
│  User   │                    │ Landing Page│                    │  ORCID  │
└────┬────┘                    └──────┬──────┘                    └────┬────┘
     │                                │                                 │
     │  1. Click "Sign in with ORCID" │                                 │
     │───────────────────────────────>│                                 │
     │                                │                                 │
     │                                │  2. Redirect to ORCID /authorize│
     │<──────────────────────────────────────────────────────────────────
     │                                │     (with client_id, scope,     │
     │                                │      redirect_uri, state)       │
     │                                │                                 │
     │  3. User authorizes app        │                                 │
     │────────────────────────────────────────────────────────────────>│
     │                                │                                 │
     │  4. Redirect to callback       │                                 │
     │<──────────────────────────────────────────────────────────────────
     │     (with authorization code)  │                                 │
     │                                │                                 │
     │                                │  5. Exchange code for token     │
     │                                │────────────────────────────────>│
     │                                │                                 │
     │                                │  6. Return access_token + orcid │
     │                                │<────────────────────────────────│
     │                                │                                 │
     │  7. Set session, redirect home │                                 │
     │<───────────────────────────────│                                 │
     │                                │                                 │
```

### ORCID Configuration

Register the application at https://orcid.org/developer-tools:

| Setting | Value |
|---------|-------|
| Redirect URI | `https://your-domain.com/auth/orcid/callback` |
| Scope | `/authenticate` (just need identity) |
| Environment | Sandbox (dev) → Production (live) |

Environment variables required:
```
ORCID_CLIENT_ID=APP-XXXXXXXXXXXXXXXX
ORCID_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ORCID_REDIRECT_URI=https://your-domain.com/auth/orcid/callback
ORCID_SANDBOX=true  # Use sandbox.orcid.org for development
```

### Database Schema (SQLite)

All metadata, users, and access control stored in `data/cellxgene.db`.

#### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────┐       ┌──────────────────┐
│     users       │       │      datasets       │       │  access_grants   │
├─────────────────┤       ├─────────────────────┤       ├──────────────────┤
│ orcid_id (PK)   │──┐    │ id (PK)             │──┐    │ id (PK)          │
│ display_name    │  │    │ filename            │  │    │ dataset_id (FK)  │
│ email           │  └───>│ owner_orcid (FK)    │  │    │ email            │
│ created_at      │       │ display_name        │  │    │ code_hash        │
│ last_login_at   │       │ description         │  └───>│ created_at       │
│ storage_quota   │       │ organism            │       │ expires_at       │
└─────────────────┘       │ tissue              │       │ verified         │
                          │ assay               │       │ revoked          │
                          │ cell_count          │       └──────────────────┘
                          │ gene_count          │
                          │ file_size_bytes     │       ┌──────────────────┐
                          │ visibility          │       │ shareable_links  │
                          │ source              │       ├──────────────────┤
                          │ filepath            │       │ id (PK)          │
                          │ created_at          │  ┌───>│ dataset_id (FK)  │
                          │ updated_at          │──┘    │ token_hash       │
                          └─────────────────────┘       │ created_by (FK)  │
                                                        │ label            │
                                                        │ expires_at       │
                                                        │ max_uses         │
                                                        │ use_count        │
                                                        │ revoked          │
                                                        └──────────────────┘
```

#### Table Definitions

```sql
-- Users table (ORCID-authenticated users)
CREATE TABLE users (
    orcid_id TEXT PRIMARY KEY,           -- "0000-0001-2345-6789"
    display_name TEXT NOT NULL,
    email TEXT,                           -- Optional, from ORCID
    created_at TEXT NOT NULL,             -- ISO 8601
    last_login_at TEXT NOT NULL,
    storage_quota_bytes INTEGER DEFAULT 53687091200,  -- 50GB default
    storage_used_bytes INTEGER DEFAULT 0
);

-- Datasets table (both curated and user-uploaded)
CREATE TABLE datasets (
    id TEXT PRIMARY KEY,                  -- Unique identifier
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,               -- Relative path to h5ad file
    display_name TEXT NOT NULL,
    description TEXT,
    organism TEXT DEFAULT 'Unknown',
    tissue TEXT DEFAULT 'Unknown',
    assay TEXT DEFAULT 'Unknown',
    cell_count INTEGER,
    gene_count INTEGER,
    file_size_bytes INTEGER,
    doi TEXT,
    publication TEXT,
    owner_orcid TEXT,                     -- NULL = curated dataset
    visibility TEXT DEFAULT 'public' CHECK(visibility IN ('public', 'unlisted', 'private')),
    source TEXT DEFAULT 'curated' CHECK(source IN ('curated', 'user_upload')),
    is_valid BOOLEAN DEFAULT 1,
    validation_errors TEXT,               -- JSON array if invalid
    additional_metadata TEXT,             -- JSON object for extra fields
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    view_count INTEGER DEFAULT 0,
    FOREIGN KEY (owner_orcid) REFERENCES users(orcid_id)
);

CREATE INDEX idx_datasets_owner ON datasets(owner_orcid);
CREATE INDEX idx_datasets_visibility ON datasets(visibility);
CREATE INDEX idx_datasets_source ON datasets(source);

-- Access grants (email-verified access to private datasets)
CREATE TABLE access_grants (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    verified BOOLEAN DEFAULT 0,
    verified_at TEXT,
    revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE INDEX idx_grants_email ON access_grants(email);
CREATE INDEX idx_grants_dataset ON access_grants(dataset_id);

-- Access log (tracks grant usage)
CREATE TABLE access_grant_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grant_id TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (grant_id) REFERENCES access_grants(id) ON DELETE CASCADE
);

-- Shareable links (token-based access)
CREATE TABLE shareable_links (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    created_by_orcid TEXT NOT NULL,
    label TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    max_uses INTEGER,                     -- NULL = unlimited
    use_count INTEGER DEFAULT 0,
    last_used_at TEXT,
    revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_orcid) REFERENCES users(orcid_id)
);

CREATE INDEX idx_links_token ON shareable_links(token_hash);
CREATE INDEX idx_links_dataset ON shareable_links(dataset_id);

-- Shareable link access log
CREATE TABLE shareable_link_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (link_id) REFERENCES shareable_links(id) ON DELETE CASCADE
);

-- Schema version for migrations
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);
INSERT INTO schema_version VALUES (1, datetime('now'), 'Initial schema with user uploads');
```

### File Storage Structure

With SQLite, we only store **h5ad files** on disk. All metadata lives in the database.

```
data/
├── cellxgene.db            # SQLite database (all metadata)
├── datasets/               # Curated datasets (h5ad only)
│   └── pbmc3k.h5ad
│
└── user-uploads/           # User-uploaded h5ad files
    └── 0000-0001-2345-6789/    # Organized by ORCID
        ├── my-experiment.h5ad
        └── collaborative-study.h5ad
```

### Data Models (Python Dataclasses)

The dataclasses remain similar but are now backed by SQLite:

```python
@dataclass
class User:
    """ORCID-authenticated user."""
    orcid_id: str
    display_name: str
    email: Optional[str]
    created_at: str
    last_login_at: str
    storage_quota_bytes: int = 50 * 1024**3  # 50GB
    storage_used_bytes: int = 0

@dataclass  
class Dataset:
    """Extended with ownership and visibility."""
    id: str
    filename: str
    filepath: Path
    display_name: str
    description: str
    organism: str
    tissue: str
    assay: str
    # ... existing fields ...
    owner_orcid: Optional[str] = None      # NULL = curated
    visibility: str = "public"              # public | unlisted | private
    source: str = "curated"                 # curated | user_upload
    view_count: int = 0
```

### New API Endpoints

#### Authentication Routes (`/auth`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/orcid` | Initiate ORCID OAuth flow |
| GET | `/auth/orcid/callback` | Handle ORCID redirect |
| POST | `/auth/logout` | Clear session |
| GET | `/auth/me` | Get current user info (or null) |

#### User Dataset Routes (`/api/my-datasets`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/my-datasets` | List authenticated user's datasets |
| GET | `/api/my-datasets/{id}` | Get specific dataset details |
| PATCH | `/api/my-datasets/{id}` | Update metadata/visibility |
| DELETE | `/api/my-datasets/{id}` | Delete dataset |

#### Chunked Upload Routes (`/api/upload`)

Uses [Resumable.js](https://github.com/23/resumable.js) protocol for chunked, resumable uploads.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/upload` | Check if chunk exists (resume support) |
| POST | `/api/upload` | Upload a chunk |
| POST | `/api/upload/complete` | Finalize upload, trigger validation |
| DELETE | `/api/upload/{identifier}` | Cancel upload, cleanup chunks |

**Query/Form Parameters (Resumable.js standard):**

| Parameter | Description |
|-----------|-------------|
| `resumableChunkNumber` | Current chunk number (1-indexed) |
| `resumableTotalChunks` | Total number of chunks |
| `resumableChunkSize` | Size of each chunk (bytes) |
| `resumableTotalSize` | Total file size (bytes) |
| `resumableIdentifier` | Unique file identifier |
| `resumableFilename` | Original filename |

### Chunked Upload Implementation (Resumable.js)

#### Why Resumable.js?

- **No additional services**: Works directly with Flask
- **Automatic retry**: Failed chunks retry automatically
- **Resume support**: Can continue after browser close/network loss
- **Progress tracking**: Built-in progress events
- **Proven**: Used by many large-scale applications

#### Upload Flow (Detailed)

```
┌─────────────┐                         ┌─────────────┐                    ┌───────────┐
│  Browser    │                         │   Flask     │                    │ Validator │
│ (Resumable) │                         │   Server    │                    │           │
└──────┬──────┘                         └──────┬──────┘                    └─────┬─────┘
       │                                       │                                  │
       │  1. User selects 8GB file             │                                  │
       │  (Resumable splits into 1600 chunks)  │                                  │
       │                                       │                                  │
       │  2. GET /api/upload?chunk=1           │                                  │
       │     (check if chunk exists)           │                                  │
       │─────────────────────────────────────->│                                  │
       │<───────────── 204 (not found) ────────│                                  │
       │                                       │                                  │
       │  3. POST /api/upload (chunk 1)        │                                  │
       │─────────────────────────────────────->│                                  │
       │     [5MB data]                        │──> Save to temp/               │
       │<───────────── 200 OK ─────────────────│    {identifier}/chunk.001       │
       │                                       │                                  │
       │  ... repeat for chunks 2-1600 ...     │                                  │
       │  (parallel: 3 simultaneous uploads)   │                                  │
       │                                       │                                  │
       │  [Network interruption at chunk 800]  │                                  │
       │                                       │                                  │
       │  4. Resume: GET /api/upload?chunk=800 │                                  │
       │─────────────────────────────────────->│                                  │
       │<───────────── 200 (exists) ───────────│                                  │
       │                                       │                                  │
       │  5. GET /api/upload?chunk=801         │                                  │
       │─────────────────────────────────────->│                                  │
       │<───────────── 204 (not found) ────────│                                  │
       │                                       │                                  │
       │  6. Continue from chunk 801...        │                                  │
       │                                       │                                  │
       │  7. All chunks complete               │                                  │
       │  POST /api/upload/complete            │                                  │
       │─────────────────────────────────────->│                                  │
       │                                       │──> Reassemble chunks            │
       │                                       │──> Move to user-uploads/        │
       │                                       │                                  │
       │                                       │  8. Validate h5ad               │
       │                                       │─────────────────────────────────>│
       │                                       │<─────────────────────────────────│
       │                                       │                                  │
       │<──── 201 {dataset_id, status} ────────│                                  │
       │                                       │                                  │
```

#### Frontend Integration

```javascript
// static/js/upload.js
const r = new Resumable({
    target: '/api/upload',
    chunkSize: 5 * 1024 * 1024,        // 5MB chunks
    simultaneousUploads: 3,             // 3 parallel chunks
    testChunks: true,                   // Enable resume
    chunkRetryInterval: 500,            // Retry delay (ms)
    maxChunkRetries: 5,                 // Max retries per chunk
    headers: {
        'X-CSRF-Token': csrfToken       // CSRF protection
    },
    query: {
        visibility: 'private',           // Default visibility
        display_name: '',                // Set by user
        description: ''
    }
});

r.on('fileAdded', (file) => {
    // Validate file extension
    if (!file.fileName.endsWith('.h5ad')) {
        r.removeFile(file);
        showError('Only .h5ad files are supported');
        return;
    }
    // Check file size
    if (file.size > 10 * 1024 * 1024 * 1024) {
        r.removeFile(file);
        showError('File exceeds 10GB limit');
        return;
    }
    r.upload();
});

r.on('fileProgress', (file) => {
    updateProgressBar(file.progress() * 100);
});

r.on('fileSuccess', (file, response) => {
    const result = JSON.parse(response);
    showSuccess(`Dataset uploaded! ID: ${result.dataset_id}`);
    window.location.href = '/my-datasets';
});

r.on('fileError', (file, message) => {
    showError(`Upload failed: ${message}`);
});
```

#### Backend Endpoints

```python
# routes/upload.py
import os
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app

upload_bp = Blueprint('upload', __name__)

CHUNK_DIR = Path('/tmp/uploads')

@upload_bp.route('/api/upload', methods=['GET'])
@require_auth
def check_chunk():
    \"\"\"Check if chunk exists (for resume support).\"\"\"
    identifier = request.args.get('resumableIdentifier')
    chunk_number = request.args.get('resumableChunkNumber')
    
    chunk_path = CHUNK_DIR / identifier / f'chunk.{chunk_number:05d}'
    
    if chunk_path.exists():
        return '', 200  # Chunk exists, skip upload
    return '', 204      # Chunk not found, upload needed

@upload_bp.route('/api/upload', methods=['POST'])
@require_auth
def upload_chunk():
    \"\"\"Receive and store a chunk.\"\"\"
    identifier = request.form.get('resumableIdentifier')
    chunk_number = int(request.form.get('resumableChunkNumber'))
    chunk_data = request.files.get('file')
    
    # Create chunk directory
    chunk_dir = CHUNK_DIR / identifier
    chunk_dir.mkdir(parents=True, exist_ok=True)
    
    # Save chunk
    chunk_path = chunk_dir / f'chunk.{chunk_number:05d}'
    chunk_data.save(chunk_path)
    
    return jsonify({'status': 'chunk_received'}), 200

@upload_bp.route('/api/upload/complete', methods=['POST'])
@require_auth
def complete_upload():
    \"\"\"Reassemble chunks and validate.\"\"\"
    identifier = request.form.get('resumableIdentifier')
    filename = secure_filename(request.form.get('resumableFilename'))
    total_chunks = int(request.form.get('resumableTotalChunks'))
    
    # Verify all chunks present
    chunk_dir = CHUNK_DIR / identifier
    chunks = sorted(chunk_dir.glob('chunk.*'))
    if len(chunks) != total_chunks:
        return jsonify({'error': 'Missing chunks'}), 400
    
    # Reassemble file
    user_dir = get_user_upload_dir(g.current_user.orcid_id)
    final_path = user_dir / filename
    
    with open(final_path, 'wb') as outfile:
        for chunk_path in chunks:
            with open(chunk_path, 'rb') as infile:
                outfile.write(infile.read())
    
    # Cleanup chunks
    shutil.rmtree(chunk_dir)
    
    # Validate h5ad (async or sync depending on size)
    validation_result = validate_h5ad(final_path)
    
    if not validation_result.valid:
        final_path.unlink()  # Delete invalid file
        return jsonify({
            'error': 'Validation failed',
            'details': validation_result.errors
        }), 422
    
    # Insert into database
    dataset = create_dataset_from_upload(
        filepath=final_path,
        owner_orcid=g.current_user.orcid_id,
        display_name=request.form.get('display_name', filename),
        description=request.form.get('description', ''),
        visibility=request.form.get('visibility', 'private'),
        validation_result=validation_result
    )
    
    return jsonify({
        'dataset_id': dataset.id,
        'status': 'complete'
    }), 201
```

#### Chunk Storage Structure

```
/tmp/uploads/                          # Temporary chunk storage
├── abc123-unique-identifier/          # One dir per upload
│   ├── chunk.00001
│   ├── chunk.00002
│   └── ...
└── def456-another-upload/
    └── ...

data/user-uploads/                     # Final storage (after assembly)
└── 0000-0001-2345-6789/
    └── experiment.h5ad
```

#### Cleanup Cron Job

Abandoned uploads should be cleaned up periodically:

```python
# scripts/cleanup-chunks.py
\"\"\"Remove chunk directories older than 24 hours.\"\"\"
import os
import time
from pathlib import Path

CHUNK_DIR = Path('/tmp/uploads')
MAX_AGE_HOURS = 24

for upload_dir in CHUNK_DIR.iterdir():
    if upload_dir.is_dir():
        age_hours = (time.time() - upload_dir.stat().st_mtime) / 3600
        if age_hours > MAX_AGE_HOURS:
            shutil.rmtree(upload_dir)
            print(f"Cleaned up: {upload_dir}")
```

Add to crontab: `0 * * * * python /app/scripts/cleanup-chunks.py`

### Original Upload Flow (Simplified View)

```
┌─────────┐                    ┌─────────────┐                    ┌───────────┐
│  User   │                    │ Landing Page│                    │ Validator │
└────┬────┘                    └──────┬──────┘                    └─────┬─────┘
     │                                │                                  │
     │  1. Select file + metadata     │                                  │
     │───────────────────────────────>│                                  │
     │                                │                                  │
     │  2. Upload progress events     │                                  │
     │<───────────────────────────────│                                  │
     │                                │                                  │
     │                                │  3. Validate h5ad structure      │
     │                                │─────────────────────────────────>│
     │                                │                                  │
     │                                │  4. Validation result            │
     │                                │<─────────────────────────────────│
     │                                │                                  │
     │  5a. Success: dataset ready    │                                  │
     │<───────────────────────────────│                                  │
     │                                │                                  │
     │  5b. Failure: error details    │                                  │
     │<───────────────────────────────│                                  │
```

---

## UI Changes

### Landing Page Header

Add authentication status to header:

```
┌────────────────────────────────────────────────────────────────────────┐
│  🧬 CellXGene Explorer                    [Sign in with ORCID] 🟢     │
├────────────────────────────────────────────────────────────────────────┤
│  ...existing content...                                                │
```

When logged in:

```
┌────────────────────────────────────────────────────────────────────────┐
│  🧬 CellXGene Explorer      [My Datasets] [▼ J. Smith (0000-0001...)] │
├────────────────────────────────────────────────────────────────────────┤
│  ...existing content...                                                │
```

### My Datasets Page

New page at `/my-datasets`:

```
┌────────────────────────────────────────────────────────────────────────┐
│  My Datasets                                        [+ Upload Dataset] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ 🔒 My Experiment v2                              Private  │ ⚙️ │ │
│  │ Homo sapiens • Lung • 10x 3' v3 • 45,231 cells                   │ │
│  │ Uploaded: 2026-03-01 • Views: 0                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ 🔗 Collaborative Study Data                      Unlisted │ ⚙️ │ │
│  │ Mus musculus • Brain • Smart-seq2 • 12,000 cells                 │ │
│  │ Uploaded: 2026-02-15 • Views: 23                                 │ │
│  │ Share link: https://example.com/d/abc123...           [Copy] 📋  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ 🌍 Published Dataset                             Public   │ ⚙️ │ │
│  │ Homo sapiens • Heart • 10x 5' • 89,000 cells                     │ │
│  │ Uploaded: 2026-01-10 • Views: 1,247                              │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Upload Modal

```
┌────────────────────────────────────────────────────────────────────────┐
│  Upload Dataset                                                   [×]  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                                                                  │ │
│  │     📁 Drag & drop your .h5ad file here                         │ │
│  │           or click to browse                                     │ │
│  │                                                                  │ │
│  │     Maximum file size: 10GB                                     │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  Display Name:  [________________________________]                     │
│  Description:   [________________________________]                     │
│                 [________________________________]                     │
│                                                                        │
│  Visibility:    ○ Private (only you)                                  │
│                 ○ Unlisted (anyone with link)                         │
│                 ○ Public (listed in catalog)                          │
│                                                                        │
│                                          [Cancel]  [Upload Dataset]   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Migration & Compatibility

### Backward Compatibility

- **Existing datasets**: Continue to work unchanged (no `owner_orcid` = curated)
- **Existing APIs**: All current endpoints remain functional
- **Anonymous browsing**: Still works for public + curated datasets

### Database Migration

On first startup with SQLite, the system will:

1. Create `data/cellxgene.db` if it doesn't exist
2. Run schema creation (all tables)
3. Detect existing JSON files and migrate data:
   - `access_grants.json` → `access_grants` table
   - `shareable_links.json` → `shareable_links` table
4. Scan curated datasets and insert into `datasets` table
5. Rename JSON files to `.json.migrated` (backup)

Migration script: `scripts/migrate-to-sqlite.py`

### Configuration Migration

Add to `docker-compose.yml`:
```yaml
services:
  landing-page:
    environment:
      - ORCID_CLIENT_ID=${ORCID_CLIENT_ID}
      - ORCID_CLIENT_SECRET=${ORCID_CLIENT_SECRET}
      - ORCID_REDIRECT_URI=${ORCID_REDIRECT_URI:-http://localhost/auth/orcid/callback}
      - ORCID_SANDBOX=${ORCID_SANDBOX:-true}
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}  # Required for sessions
      - DATABASE_PATH=${DATABASE_PATH:-/app/data/cellxgene.db}
    volumes:
      - ./data:/app/data  # Single volume for DB + all h5ad files
```

---

## Implementation Tasks

### Phase 0: Database Migration (Week 1)
- [ ] Create `services/database.py` with SQLite connection management
- [ ] Implement schema creation and versioning
- [ ] Create migration script for existing JSON → SQLite
- [ ] Refactor `AccessGrantStore` to use SQLite
- [ ] Refactor `ShareableLinkStore` to use SQLite
- [ ] Update `DatasetCatalog` to use SQLite
- [ ] Update `startup.py` to initialize database
- [ ] Write tests for database operations
- [ ] Test migration with existing data

### Phase 1: Authentication (Week 2)
- [ ] Register ORCID application (sandbox + production)
- [ ] Implement `UserStore` with SQLite backend
- [ ] Create `/auth` routes with ORCID OAuth flow
- [ ] Add session management with Flask-Login or similar
- [ ] Update UI header with login/logout
- [ ] Write tests for OAuth flow

### Phase 2: Upload Infrastructure (Week 3)
- [ ] Add Resumable.js to static assets (CDN or vendor)
- [ ] Create `/api/upload` routes (GET check, POST chunk, POST complete, DELETE cancel)
- [ ] Implement chunk storage in `/tmp/uploads/{identifier}/`
- [ ] Implement chunk reassembly on complete
- [ ] Add h5ad validation (reuse existing scanner logic)
- [ ] Insert uploaded datasets into SQLite
- [ ] Create upload UI component with drag-drop and progress bar
- [ ] Add cleanup cron job for abandoned chunks (24h expiry)
- [ ] Write tests for chunked upload flow
- [ ] Write tests for resume after interruption

### Phase 3: Visibility & Management (Week 4)
- [ ] Implement visibility filtering in queries
- [ ] Create "My Datasets" dashboard page
- [ ] Add edit/delete endpoints with ownership checks
- [ ] Generate shareable links for unlisted datasets
- [ ] Update main catalog to show public user datasets
- [ ] Write tests for visibility rules

### Phase 4: Polish & Security (Week 5)
- [ ] Security review (path traversal, CSRF, SQL injection prevention)
- [ ] Error handling and edge cases
- [ ] Rate limiting for uploads
- [ ] Backup documentation for SQLite
- [ ] End-to-end testing

---

## Open Questions

1. ~~**File size limit**: 2GB proposed—is this sufficient for your typical datasets?~~ **RESOLVED**: 10GB limit
2. **Retention policy**: Should we auto-delete datasets after N days of inactivity?
3. **Quota per user**: Limit number of datasets or total storage per ORCID?
4. **Moderation**: Any review process before user datasets go public?
5. **Terms of service**: Do users need to accept ToS before uploading?

---

## References

- [ORCID API Documentation](https://info.orcid.org/documentation/api-tutorials/)
- [ORCID OAuth Tutorial](https://info.orcid.org/documentation/api-tutorials/api-tutorial-get-and-authenticated-orcid-id/)
- [Flask-Dance (OAuth library)](https://flask-dance.readthedocs.io/)
- [Resumable.js Documentation](https://github.com/23/resumable.js)
- [Resumable.js Flask Example](https://github.com/23/resumable.js/tree/master/samples/Backend%20on%20Flask)
- [SQLite Python Documentation](https://docs.python.org/3/library/sqlite3.html)
- [SQLite Best Practices](https://www.sqlite.org/bestpractices.html)
- [Existing spec: 001-cellxgene-explorer](../001-cellxgene-explorer/spec.md)
