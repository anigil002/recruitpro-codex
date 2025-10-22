"""Document endpoints."""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_current_user, get_db
from ..models import Document
from ..schemas import DocumentRead
from ..services.activity import log_activity
from ..utils.security import generate_id

settings = get_settings()
router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=List[DocumentRead])
def list_documents(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[DocumentRead]:
    documents = db.query(Document).filter(Document.owner_user == current_user.user_id).all()
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
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_id = generate_id()
    file_path = storage_dir / f"{file_id}_{file.filename}"
    with file_path.open("wb") as f:
        f.write(file.file.read())

    document = Document(
        id=file_id,
        filename=filename,
        mime_type=mime_type,
        file_url=str(file_path),
        scope=scope,
        scope_id=scope_id,
        owner_user=current_user.user_id,
    )
    db.add(document)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        message=f"Uploaded document {document.filename}",
        event_type="document_uploaded",
    )
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


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> FileResponse:
    document = db.get(Document, doc_id)
    if not document or document.owner_user != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    path = Path(document.file_url)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
    return FileResponse(path, filename=document.filename, media_type=document.mime_type)


@router.get("/documents/{doc_id}/view", response_model=DocumentRead)
def view_document(doc_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> DocumentRead:
    document = db.get(Document, doc_id)
    if not document or document.owner_user != current_user.user_id:
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
    path = Path(document.file_url)
    if path.exists():
        path.unlink()
    db.delete(document)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        message=f"Deleted document {document.filename}",
        event_type="document_deleted",
    )
