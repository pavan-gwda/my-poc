# RAG service: embeddings + retrieval using sentence-transformers + chromadb
# Run: pip install -r requirements.txt
# Start: python rag_service.py
from fastapi import FastAPI
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
import uvicorn
import os, json

app = FastAPI()
client = chromadb.Client()
collection = None
COLL_NAME = "local_docs"

model = SentenceTransformer('all-MiniLM-L6-v2')  # small, local

# bootstrap collection
try:
    collection = client.get_collection(COLL_NAME)
except Exception:
    collection = client.create_collection(COLL_NAME)

class AddDoc(BaseModel):
    id: str
    text: str
    meta: dict = None

class QueryReq(BaseModel):
    query: str
    k: int = 4

@app.post('/add')
def add_doc(doc: AddDoc):
    emb = model.encode(doc.text).tolist()
    collection.add(ids=[doc.id], metadatas=[doc.meta or {}], documents=[doc.text], embeddings=[emb])
    return {"ok": True}

@app.post('/query')
def query(q: QueryReq):
    emb = model.encode(q.query).tolist()
    results = collection.query(query_embeddings=[emb], n_results=q.k)
    # strip binary objects to JSON
    hits = []
    for ids, docs, metas, dists in zip(results['ids'], results['documents'], results['metadatas'], results.get('distances', [])):
        for _id, doc, meta in zip(ids, docs, metas):
            hits.append({"id": _id, "text": doc, "meta": meta})
    return {"results": hits}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001)
