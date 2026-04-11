from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from app.core.database import Base

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    code_content = Column(Text)
    issues_count = Column(Integer)
    analysis_results = Column(JSON) # Зберігатимемо Issues, Graph JSON тощо [cite: 15]