from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db
from app.models import Base, User, RoleEnum
from sqlalchemy import Column, Integer, String
from .routes import documents, folders, onlyoffice
from .middleware.auth import get_current_active_user, create_access_token, verify_password, get_password_hash
from datetime import timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(folders.router)
app.include_router(onlyoffice.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Tru Lawyer DMS API"}

Base.metadata.create_all(bind=engine)

@app.post("/api/auth/register")
def register(username: str, password: str, role: RoleEnum = RoleEnum.LAWYER, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = get_password_hash(password)
    user = User(username=username, password_hash=hashed_password, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered", "username": user.username, "role": user.role.value}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {"username": current_user.username, "role": current_user.role.value}
