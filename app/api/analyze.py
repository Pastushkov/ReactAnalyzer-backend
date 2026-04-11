from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisListItem, AnalysisFull
from typing import List

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

@router.post("/", response_model=AnalysisFull)
def perform_analysis(request: AnalysisCreate, db: Session = Depends(get_db)):
    # 1. ТУТ БУДЕ ЛОГІКА AST ТА AI АНАЛІЗУ [cite: 6]
    # Поки що робимо "заглушку"
    issues = [{"type": "warning", "msg": "Test issue"}]
    
    new_analysis = Analysis(
        code_content=request.code,
        issues_count=len(issues),
        analysis_results={"issues": issues, "graph": {}} # [cite: 7]
    )
    
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)
    return new_analysis

@router.get("/", response_model=List[AnalysisListItem])
def get_analyses(db: Session = Depends(get_db)):
    return db.query(Analysis).all()

@router.get("/{id}", response_model=AnalysisFull)
def get_analysis_details(id: int, db: Session = Depends(get_db)):
    result = db.query(Analysis).filter(Analysis.id == id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return result