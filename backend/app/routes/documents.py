from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from database import get_db
from app.models import Document, DocumentVersion
import boto3
from botocore.client import Config

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"]
)

minio_client = boto3.client(
    's3',
    endpoint_url='http://127.0.0.1:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='supersecretpassword',
    config=Config(signature_version='s3v4')
)
BUCKET_NAME = "documents"

try:
    minio_client.head_bucket(Bucket=BUCKET_NAME)
except minio_client.exceptions.NoSuchBucket:
    minio_client.create_bucket(Bucket=BUCKET_NAME)
except Exception as e:
    raise Exception(f"Failed to initialize MinIO bucket: {str(e)}")

@router.post("/upload", response_model=dict)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    folder_id: int | None = None,
    db: Session = Depends(get_db)
):
    existing_doc = db.query(Document).filter(Document.title == title).first()
    if existing_doc:
        version_num = db.query(DocumentVersion).filter(DocumentVersion.document_id == existing_doc.id).count() + 1
        minio_key = f"{file.filename.rsplit('.', 1)[0]}_v{version_num}.{file.filename.rsplit('.', 1)[1]}"
        document = existing_doc
    else:
        version_num = 1
        minio_key = file.filename
        document = Document(title=title, minio_key=minio_key, folder_id=folder_id)
        db.add(document)
        db.commit()
        db.refresh(document)

    minio_client.upload_fileobj(file.file, BUCKET_NAME, minio_key)
    version = DocumentVersion(document_id=document.id, version=version_num, minio_key=minio_key)
    db.add(version)
    db.commit()
    db.refresh(version)
    return {"id": document.id, "title": document.title, "minio_key": version.minio_key, "version": version.version}

@router.get("/{document_id}/versions", response_model=list[dict])
def list_document_versions(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).all()
    return [{"version": v.version, "minio_key": v.minio_key, "created_at": v.created_at} for v in versions]
