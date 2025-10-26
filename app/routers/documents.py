"""Document endpoints."""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Document, Project, ProjectDocument
from ..schemas import DocumentRead
from ..services.activity import log_activity
from ..services.ai import create_ai_job
from ..services.queue import background_queue
from ..utils.permissions import can_manage_workspace, ensure_project_access
from ..utils.security import generate_id
from ..utils.storage import ensure_storage_dir, resolve_storage_path

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=List[DocumentRead])
def list_documents(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[DocumentRead]:
    query = db.query(Document)
    if not can_manage_workspace(current_user):
        query = query.filter(Document.owner_user == current_user.user_id)
    documents = query.all()
    return [
        DocumentRead(
            id=doc.id,
            filename=doc.filename,
            mime_type=doc.mime_type,
            file_url=doc.file_url,
            scope=doc.scope,
            scope_id=doc.scope_id,
            owner_user=doc.owner_user,
            uploaded_at=doc.uploaded_at,
        )
        for doc in documents
    ]


@router.post("/documents/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    filename: str = Form(...),
    mime_type: str = Form(...),
    scope: str = Form(...),
    scope_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DocumentRead:
    storage_dir = ensure_storage_dir()
    project = None
    if scope == "project":
        if not scope_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope_id required for project uploads")
        ensure_project_access(db.get(Project, scope_id), current_user)

    safe_name = Path(file.filename).name
    file_id = generate_id()
    file_path = storage_dir / f"{file_id}_{safe_name}"
    with file_path.open("wb") as buffer:
        buffer.write(file.file.read())

    relative_path = file_path.relative_to(storage_dir)
    document = Document(
        id=file_id,
        filename=filename,
        mime_type=mime_type,
        file_url=str(relative_path),
        scope=scope,
        scope_id=scope_id,
        owner_user=current_user.user_id,
    )
    db.add(document)
    project_doc_id = None
    if scope == "project" and scope_id:
        project_doc = ProjectDocument(
            doc_id=file_id,
            project_id=scope_id,
            filename=filename,
            file_url=str(relative_path),
            mime_type=mime_type,
            uploaded_by=current_user.user_id,
        )
        db.add(project_doc)
        project_doc_id = project_doc.doc_id

    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        message=f"Uploaded document {document.filename}",
        event_type="document_uploaded",
    )

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
    background_queue.enqueue("file_analysis", {"job_id": job.job_id})
    db.flush()

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


@router.get("/projects/{project_id}/documents", response_model=List[DocumentRead])
def list_project_documents(
    project_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[DocumentRead]:
    ensure_project_access(db.get(Project, project_id), current_user)
    documents = (
        db.query(ProjectDocument)
        .filter(ProjectDocument.project_id == project_id)
        .order_by(ProjectDocument.uploaded_at.desc())
        .all()
    )
    return [
        DocumentRead(
            id=doc.doc_id,
            filename=doc.filename,
            mime_type=doc.mime_type,
            file_url=doc.file_url,
            scope="project",
            scope_id=doc.project_id,
            owner_user=doc.uploaded_by,
            uploaded_at=doc.uploaded_at,
        )
        for doc in documents
    ]


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> FileResponse:
    document = db.get(Document, doc_id)
    if not document or (document.owner_user != current_user.user_id and not can_manage_workspace(current_user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        path = resolve_storage_path(document.file_url)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
    return FileResponse(path, filename=document.filename, media_type=document.mime_type)


@router.get("/documents/{doc_id}/file")
def stream_document(doc_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> StreamingResponse:
    document = db.get(Document, doc_id)
    if not document or (document.owner_user != current_user.user_id and not can_manage_workspace(current_user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        path = resolve_storage_path(document.file_url)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")

    def iterator():
        with path.open("rb") as stream:
            while chunk := stream.read(8192):
                yield chunk

    headers = {"Content-Disposition": f"inline; filename={document.filename}"}
    return StreamingResponse(iterator(), media_type=document.mime_type, headers=headers)


@router.get("/documents/{doc_id}/view", response_model=DocumentRead)
def view_document(doc_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> DocumentRead:
    document = db.get(Document, doc_id)
    if not document or (document.owner_user != current_user.user_id and not can_manage_workspace(current_user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
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


@router.get("/documents/{doc_id}", response_model=DocumentRead)
def get_document_metadata(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DocumentRead:
    return view_document(doc_id, db, current_user)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> None:
    document = db.get(Document, doc_id)
    if not document or document.owner_user != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        path = resolve_storage_path(document.file_url)
    except ValueError:
        path = None
    if path and path.exists():
        path.unlink()
    project_doc = db.get(ProjectDocument, doc_id)
    if project_doc:
        db.delete(project_doc)
    db.delete(document)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        message=f"Deleted document {document.filename}",
        event_type="document_deleted",
    )
