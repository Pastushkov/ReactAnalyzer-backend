from pydantic import BaseModel
from datetime import datetime
from typing import List, Any, Optional

# Що приходить з фронту
class AnalysisCreate(BaseModel):
    code: str

# Коротка інфа для списку
class AnalysisListItem(BaseModel):
    id: int
    created_at: datetime
    issues_count: int

    class Config:
        from_attributes = True

# Повна інфа по ID
class AnalysisFull(AnalysisListItem):
    code_content: str
    analysis_results: Any