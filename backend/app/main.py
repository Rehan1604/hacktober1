import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import db
from app.explain import DocumentTooLong, ExplainError, explain, to_hindi
from app.extract import ExtractError, OCRUnavailable, extract_text
from app.llm import LLMError, get_provider
from app.prompts import DISCLAIMER
from app.schemas import Explanation


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Plain-Words", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
provider = get_provider()
llm_lock = asyncio.Lock()  # one CPU model: run one request at a time


class Feedback(BaseModel):
    helpful: bool


@app.get("/api/health")
async def health():
    return {**await provider.health(), "model": provider.model}


@app.post("/api/explain")
async def explain_endpoint(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    if file is not None and file.filename:
        data = await file.read()
        try:
            raw, source = await asyncio.to_thread(extract_text, file.filename, data)
        except OCRUnavailable as e:
            raise HTTPException(503, str(e))
        except ExtractError as e:
            raise HTTPException(400, str(e))
    elif text and text.strip():
        raw, source = text, "text"
    else:
        raise HTTPException(400, "Upload a file or paste some text.")

    try:
        async with llm_lock:
            exp = await explain(raw, provider)
    except DocumentTooLong as e:
        raise HTTPException(413, str(e))
    except ExplainError as e:
        raise HTTPException(422, str(e))
    except LLMError as e:
        raise HTTPException(503, str(e))

    doc_id = db.save(source, exp.doc_type, raw.strip(), provider.model, exp.model_dump())
    return {
        "id": doc_id,
        "result": exp.model_dump(),
        "disclaimer": DISCLAIMER,
        "source": source,
        "extracted_text": raw.strip() if source == "image" else None,
    }


@app.post("/api/documents/{doc_id}/hindi")
async def hindi_endpoint(doc_id: int):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    if doc["hindi"]:
        return {"hindi": doc["hindi"]}
    exp = Explanation.model_validate(doc["result"])
    try:
        async with llm_lock:
            hv = await to_hindi(exp, provider)
    except ExplainError as e:
        raise HTTPException(422, str(e))
    except LLMError as e:
        raise HTTPException(503, str(e))
    db.set_hindi(doc_id, hv.model_dump())
    return {"hindi": hv.model_dump()}


@app.get("/api/documents")
async def list_documents():
    return db.list_documents()


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return {**doc, "disclaimer": DISCLAIMER}


@app.post("/api/documents/{doc_id}/feedback")
async def feedback(doc_id: int, body: Feedback):
    if not db.set_helpful(doc_id, body.helpful):
        raise HTTPException(404, "Document not found.")
    return {"ok": True}


@app.delete("/api/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: int):
    if not db.delete_document(doc_id):
        raise HTTPException(404, "Document not found.")
    return Response(status_code=204)