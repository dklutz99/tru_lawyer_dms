from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Document  # Absolute import
import boto3
from botocore.client import Config

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"]
)

# MinIO Client Configuration
minio_client = boto3.client(
    's3',
    endpoint_url='http://127.0.0.1:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='supersecretpassword',
    config=Config(signature_version='s3v4')
)
BUCKET_NAME = "documents"

# Ensure bucket exists
try:
    minio_client.head_bucket(Bucket=BUCKET_NAME)
except minio_client.exceptions.NoSuchBucket:
    minio_client.create_bucket(Bucket=BUCKET_NAME)
except Exception as e:
    raise Exception(f"Failed to initialize MinIO bucket: {str(e)}")

@router.post("/upload", response_model=dict)
async def upload_document(
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    minio_key = file.filename
    try:
        # Upload to MinIO
        minio_client.upload_fileobj(file.file, BUCKET_NAME, minio_key)
        # Save to database
        document = Document(title=title, minio_key=minio_key)
        db.add(document)
        db.commit()
        db.refresh(document)
        return {"id": document.id, "title": document.title, "minio_key": document.minio_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
