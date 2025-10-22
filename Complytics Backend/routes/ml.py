from fastapi import APIRouter, UploadFile, File
from typing import Any, Dict
import json
from pathlib import Path


router = APIRouter(prefix="/api/ml", tags=["ml-placeholder"])


@router.get("/status")
async def ml_status() -> Dict[str, Any]:
    info_path = Path(__file__).resolve().parent.parent / "ml" / "outputs" / "model_info.json"
    if info_path.exists():
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
            return {"status": "ready", "model": data.get("model_type"), "labels": data.get("labels")}
        except Exception:
            return {"status": "ready", "model": "unknown", "labels": []}
    return {"status": "not_trained"}


@router.post("/predict")
async def ml_predict_placeholder(file: UploadFile = File(...)) -> Dict[str, Any]:
    # Returns a canned response proving the endpoint exists.
    _ = await file.read()
    return {
        "message": "Prediction endpoint.",
        "accepted_filename": file.filename,
        "note": "This endpoint is used to predict the accessibility severity of a given file.",
    }


