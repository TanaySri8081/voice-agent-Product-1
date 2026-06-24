from typing import Any, Optional
from fastapi.responses import JSONResponse

def serialize_doc(doc: Optional[dict]) -> Optional[dict]:
    if doc is None:
        return None
    doc_copy = doc.copy()
    if "_id" in doc_copy:
        doc_copy["id"] = str(doc_copy["_id"])
        del doc_copy["_id"]
    return doc_copy

def serialize_docs(docs: list) -> list:
    return [serialize_doc(doc) for doc in docs if doc]

def api_response(
    success: bool,
    message: str,
    data: Optional[Any] = None,
    error: Optional[Any] = None,
    status_code: int = 200
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": success,
            "message": message,
            "data": data,
            "error": error
        }
    )
