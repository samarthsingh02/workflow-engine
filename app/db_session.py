from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session

# SQLite URL. Connects to a file named 'workflow.db' in the project root.
SQLALCHEMY_DATABASE_URL = "sqlite:///./workflow.db"

# Create the engine. check_same_thread is needed for SQLite with FastAPI.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# A factory for new Session objects.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models.
Base = declarative_base()

def get_db():
    """
    Dependency to get a database session for FastAPI endpoints.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()