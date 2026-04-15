from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import WorkflowRun, TrackerRecord  # noqa: F401 — register models

settings = get_settings()
engine = create_engine(settings.db_url, echo=False)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine)
