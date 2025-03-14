from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from app.models import Folder, Document, User, RoleEnum  # From models
from pydantic import BaseModel
from app.middleware.auth import require_role

router = APIRouter(
    prefix="/api/folders",
    tags=["folders"]
)

class FolderCreate(BaseModel):
    name: str
    parent_id: int | None = None

class FolderUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None

@router.post("/", response_model=dict)
def create_folder(
    folder: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.ADMIN))
):
    db_folder = Folder(name=folder.name, parent_id=folder.parent_id)
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return {"id": db_folder.id, "name": db_folder.name, "parent_id": db_folder.parent_id}

@router.get("/", response_model=list[dict])
def list_folders(db: Session = Depends(get_db)):
    folders = db.query(Folder).all()
    return [{"id": f.id, "name": f.name, "parent_id": f.parent_id} for f in folders]

@router.put("/{folder_id}", response_model=dict)
def update_folder(folder_id: int, folder: FolderUpdate, db: Session = Depends(get_db)):
    db_folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not db_folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    if folder.name is not None:
        db_folder.name = folder.name
    if folder.parent_id is not None:
        db_folder.parent_id = folder.parent_id
    db.commit()
    db.refresh(db_folder)
    return {"id": db_folder.id, "name": db_folder.name, "parent_id": db_folder.parent_id}
