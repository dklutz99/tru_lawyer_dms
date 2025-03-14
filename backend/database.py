from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import yaml
from app.models import Base  # Import Base from models

with open("config/database.yaml", "r") as file:
    config = yaml.safe_load(file)["database"]

DATABASE_URL = (
    f"postgresql://{config['user']}:{config['password']}"
    f"@{config['host']}:{config['port']}/{config['dbname']}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
