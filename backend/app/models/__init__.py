from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

class RoleEnum(enum.Enum):
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    ADMIN = "admin"

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    minio_key = Column(String, unique=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)

class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(RoleEnum), default=RoleEnum.LAWYER)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # e.g., "create_folder", "upload_document"
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String, nullable=True)  # Optional JSON or text details
