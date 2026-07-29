# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

db_url = settings.DATABASE_URL

# Auto-convert IPv6-only hostname to IPv4 pooler in our local agent environment
if "db.nnapoohhhibyxlebsxqj.supabase.co" in db_url:
    try:
        # URL format: postgresql://postgres:PASSWORD@db.nnapoohhhibyxlebsxqj.supabase.co:5432/postgres
        part1 = db_url.split("://")[1]
        auth_part = part1.split("@")[0]
        password = auth_part.split(":")[1]
        db_url = f"postgresql://postgres.nnapoohhhibyxlebsxqj:{password}@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    except Exception as e:
        print(f"Warning: Could not parse database URL for pooler mapping: {e}")

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency injection helper to yield active DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
