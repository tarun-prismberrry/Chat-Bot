import os
import uuid
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

print(embeddings.embed_query("What is process scheduling?")[:5])

vector_store = Chroma(
    collection_name="docss",
    embedding_function=embeddings,
    persist_directory="./chromadb"
)

def load_documents(file_path: str):
    extension = os.path.splitext(file_path)[1].lower()

    if(extension == '.pdf'):
        loader = PyPDFLoader(file_path)
    elif extension == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif extension == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError("Unsupported file format")

    return loader.load()


def ingest_document(file_path: str, thread_id: str):
    documents = load_documents(file_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap  = 200
    )

    chunks = splitter.split_documents(documents)
    document_id = str(uuid.uuid4())
    for chunk in chunks:
        chunk.metadata.update({
             "thread_id": thread_id,
            "document_id": document_id,
            "filename": os.path.basename(file_path),
        })
    ids = [str(uuid.uuid4()) for _ in chunks]

    vector_store.add_documents(
        documents=chunks,
        ids=ids,
    )

    return {
        "document_id": document_id,
        "chunks_created": len(chunks),
    }

def retrieve_documents(query: str, thread_id: str):
    return vector_store.similarity_search(
        query, 
        k = 4, 
        filter = {'thread_id': thread_id}
    )