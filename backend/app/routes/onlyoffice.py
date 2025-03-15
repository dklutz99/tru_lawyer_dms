from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from app.models import Document, User, AuditLog
from app.middleware.auth import get_current_active_user
import boto3
from botocore.client import Config
import jwt
from typing import Dict
import os
import requests
from datetime import datetime

router = APIRouter(
    prefix="/api/onlyoffice",
    tags=["onlyoffice"]
)

# MinIO client
minio_client = boto3.client(
    's3',
    endpoint_url='http://127.0.0.1:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='supersecretpassword',
    config=Config(signature_version='s3v4')
)
BUCKET_NAME = "documents"
# ONLYOFFICE settings
ONLYOFFICE_URL = "http://127.0.0.1:8080"  # Document Server URL
JWT_SECRET = "your-onlyoffice-secret"     # Must match docker-compose

@router.get("/editor/{document_id}")
def get_editor_config(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict:
    # Fetch document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Generate file URL for MinIO
    file_url = minio_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': document.minio_key},
        ExpiresIn=3600
    )
    callback_url = f"http://127.0.0.1:8000/api/onlyoffice/callback/{document_id}"

    # Editor config
    config = {
        "document": {
            "fileType": os.path.splitext(document.minio_key)[1][1:],  # e.g., "docx"
            "key": f"{document.id}_{int(datetime.now().timestamp())}",  # Unique key
            "title": document.title,
            "url": file_url
        },
        "documentType": "text",  # Adjust based on file type
        "editorConfig": {
            "callbackUrl": callback_url,
            "user": {
                "id": str(current_user.id),
                "name": current_user.username
            }
        }
    }

    # Add JWT token
    config["token"] = jwt.encode(config, JWT_SECRET, algorithm="HS256")
    return config

@router.post("/callback/{document_id}")
async def onlyoffice_callback(
    document_id: int,
    body: dict,
    db: Session = Depends(get_db)
):
    status = body.get("status")
    if status == 2:  # Document saved
        url = body.get("url")
        response = requests.get(url)
        if response.status_code == 200:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                version_num = db.query(DocumentVersion).filter(DocumentVersion.document_id == document.id).count() + 1
                minio_key = f"{document.minio_key.rsplit('.', 1)[0]}_v{version_num}.{document.minio_key.rsplit('.', 1)[1]}"
                minio_client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=minio_key,
                    Body=response.content
                )
                version = DocumentVersion(document_id=document.id, version=version_num, minio_key=minio_key)
                db.add(version)
                db.commit()
                audit = AuditLog(
                    user_id=body.get("users", [None])[0],
                    action="edit_document",
                    details=f"Edited document: {document.title}, version {version_num}"
                )
                db.add(audit)
                db.commit()
    return {"error": 0}
