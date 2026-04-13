from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisListItem, AnalysisFull
from typing import List

from app.services.ast_parser import ReactASTAnalyzer
from app.services.graph_builder import GraphBuilder

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


@router.post("/", response_model=AnalysisFull)
def perform_analysis(request: AnalysisCreate, db: Session = Depends(get_db)):
    # 1. Run AST Analysis (Extracts components, states, effects, functions)
    ast_analyzer = ReactASTAnalyzer(request.code)
    ast_result = ast_analyzer.run_analysis()

    # 2. Build Dependency Graph
    graph_builder = GraphBuilder(ast_result["extracted_data"])
    graph_data = graph_builder.build_graph()

    # 3. Compile final structured result
    analysis_results = {
        "issues": ast_result["issues"],
        "extracted_data": ast_result["extracted_data"],
        "graph": graph_data,
    }

    # 4. Save to Database
    new_analysis = Analysis(
        issues_count=len(ast_result["issues"]),
        analysis_results=analysis_results,
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
