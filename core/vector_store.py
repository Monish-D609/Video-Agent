import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
# NOTE: We no longer use a single global collection name.
# Each video gets its own collection: "video_<key>" so transcripts never bleed across chats.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _collection_name(key: str) -> str:
    """Return a ChromaDB-safe collection name for a given video key.
    ChromaDB collection names must be 3-63 chars, alphanumeric + hyphens.
    We sanitise the key and prefix it so it's always valid."""
    safe = "".join(c if c.isalnum() or c == "-" else "_" for c in key)[:55]
    return f"vid_{safe}"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )


def build_vector_store(transcript: str, key: str = "default") -> Chroma:
    """Build a fresh per-video vector store, replacing any previous index for this key."""
    collection = _collection_name(key)
    print(f"Building vector store for collection '{collection}'")

    # Delete the old collection for this video so stale chunks never bleed in.
    try:
        existing = Chroma(
            collection_name=collection,
            embedding_function=get_embeddings(),
            persist_directory=CHROMA_DIR,
        )
        existing.delete_collection()
        print(f"  Deleted stale collection '{collection}'")
    except Exception:
        pass  # Collection didn't exist yet — that's fine

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_text(transcript)

    docs = [
        Document(page_content=chunk, metadata={"chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    embeddings = get_embeddings()
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection,
        persist_directory=CHROMA_DIR,
    )
    return vector_store


def load_vector_store(key: str = "default") -> Chroma:
    """Load an existing per-video vector store by key."""
    collection = _collection_name(key)
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
    return vector_store


def get_retriever(vector_store: Chroma, k: int = 4):
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )