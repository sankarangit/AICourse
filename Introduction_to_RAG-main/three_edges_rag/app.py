"""Single-file RAG app using local FAISS, OpenAI, and LangSmith tracing."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "Three_Edges_Alpha_X.pdf"
FAISS_DIR = BASE_DIR / "faiss_db"
MODEL_DIR = BASE_DIR / "models" / "embeddings"
INDEX_NAME = "three_edges_alpha_x"
MANIFEST_PATH = FAISS_DIR / "manifest.json"

load_dotenv(BASE_DIR / ".env")
course_env_path = BASE_DIR.parents[1] / ".env"
if course_env_path.exists():
    load_dotenv(course_env_path, override=False)

# Map the user's environment-variable names to the names expected by OpenAI and
# LangSmith. Values remain in the environment and are never stored in FAISS.
openapi_key = os.getenv("OpenAPI_API_Key") or os.getenv("OPENAI_API_KEY")
langsmith_key = (
    os.getenv("LangSmith_API_Key")
    or os.getenv("langsmith_api_key")
    or os.getenv("LANGSMITH_API_KEY")
)

if openapi_key:
    os.environ["OPENAI_API_KEY"] = openapi_key
if langsmith_key:
    os.environ["LANGSMITH_API_KEY"] = langsmith_key

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "my-RAG-app")


# -----------------------------------------------------------------------------
# Embeddings and FAISS
# -----------------------------------------------------------------------------

def embedding_model_is_cached(model_name: str) -> bool:
    cache_name = "models--" + model_name.replace("/", "--")
    snapshots = MODEL_DIR / cache_name / "snapshots"
    return snapshots.exists() and any(snapshots.iterdir())


@st.cache_resource
def get_embeddings() -> HuggingFaceEmbeddings:
    """Load the local embedding model once per application process."""
    model_name = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    return HuggingFaceEmbeddings(
        model_name=model_name,
        cache_folder=str(MODEL_DIR),
        model_kwargs={
            "device": "cpu",
            "local_files_only": embedding_model_is_cached(model_name),
        },
        encode_kwargs={"normalize_embeddings": True},
    )


def vector_store_count() -> int:
    """Read the chunk count without loading the embedding model."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return int(manifest["chunk_count"])
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 0


def build_faiss_index() -> int:
    """Read the PDF, create chunks, and replace the local FAISS index."""
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    pages = PyPDFLoader(str(PDF_PATH)).load()
    for page in pages:
        page.metadata["source"] = PDF_PATH.name
        page.metadata["page_number"] = int(page.metadata.get("page", 0)) + 1

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        add_start_index=True,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = [
        chunk
        for chunk in splitter.split_documents(pages)
        if chunk.page_content.strip()
    ]
    ids = [
        hashlib.sha256(
            f"{chunk.metadata['page_number']}:{chunk.metadata.get('start_index', 0)}:{chunk.page_content}".encode(
                "utf-8"
            )
        ).hexdigest()
        for chunk in chunks
    ]

    store = FAISS.from_documents(chunks, get_embeddings(), ids=ids)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    store.save_local(str(FAISS_DIR), index_name=INDEX_NAME)
    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "document": PDF_PATH.name,
                "page_count": len(pages),
                "chunk_count": len(chunks),
                "embedding_model": os.getenv(
                    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return len(chunks)


def load_faiss_index() -> FAISS:
    """Load the FAISS index generated locally by this application."""
    return FAISS.load_local(
        str(FAISS_DIR),
        get_embeddings(),
        index_name=INDEX_NAME,
        # Safe because the app creates and owns these local index files.
        allow_dangerous_deserialization=True,
    )


def retrieve(question: str, k: int = 5) -> list[Document]:
    if vector_store_count() == 0:
        build_faiss_index()
    return load_faiss_index().similarity_search(question, k=k)


# -----------------------------------------------------------------------------
# OpenAI answer generation with automatic LangSmith tracing
# -----------------------------------------------------------------------------

def answer_question(question: str, k: int = 5) -> tuple[str, list[Document]]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OpenAPI_API_Key is missing from the .env file.")
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError("LangSmith_API_Key is missing from the .env file.")

    documents = retrieve(question, k=k)
    context = "\n\n".join(
        f"[Page {doc.metadata.get('page_number', '?')}]\n{doc.page_content}"
        for doc in documents
    )
    messages = [
        SystemMessage(
            content=(
                "Answer the question using only the retrieved document context. "
                "If the answer is absent, say the document does not provide enough "
                "information. Cite supporting pages inline as [Page N]. Preserve "
                "material facts and caveats, and do not invent information."
            )
        ),
        HumanMessage(
            content=f"Question:\n{question}\n\nRetrieved context:\n{context}"
        ),
    ]

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"))
    response = llm.invoke(
        messages,
        config={
            "run_name": "three-edges-rag-answer",
            "tags": ["rag", "faiss", "three-edges"],
            "metadata": {
                "document": PDF_PATH.name,
                "retrieved_chunks": len(documents),
            },
        },
    )
    return str(response.content), documents


# -----------------------------------------------------------------------------
# Streamlit interface
# -----------------------------------------------------------------------------

st.set_page_config(page_title="Three Edges RAG", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at 10% 5%, rgba(99, 102, 241, 0.16), transparent 28%),
            radial-gradient(circle at 90% 8%, rgba(14, 165, 233, 0.14), transparent 26%),
            linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #172554 0%, #1e3a8a 55%, #0f766e 100%);
    }
    [data-testid="stSidebar"] * { color: #f8fafc; }
    [data-testid="stSidebar"] code {
        color: #172554 !important;
        background: #dbeafe !important;
        border-radius: 6px;
        padding: .12rem .35rem;
    }
    [data-testid="stSidebar"] .stMetric {
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 14px;
        padding: 10px;
    }
    .hero {
        padding: 1.5rem 1.7rem;
        border-radius: 22px;
        color: white;
        background: linear-gradient(120deg, #312e81, #2563eb 52%, #0d9488);
        box-shadow: 0 16px 40px rgba(30, 64, 175, 0.22);
        margin-bottom: 1rem;
    }
    .hero h1 { margin: 0 0 .3rem 0; font-size: 2.25rem; }
    .hero p { margin: 0; opacity: .92; font-size: 1.02rem; }
    .flow-wrap {
        display: flex;
        align-items: center;
        gap: .4rem;
        flex-wrap: wrap;
        padding: .9rem 0 1.1rem;
    }
    .flow-step {
        color: #172554;
        background: white;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: .55rem .72rem;
        font-weight: 650;
        box-shadow: 0 5px 14px rgba(37, 99, 235, .10);
    }
    .flow-step.local { border-color: #5eead4; background: #f0fdfa; }
    .flow-step.cloud { border-color: #c4b5fd; background: #f5f3ff; }
    .flow-arrow { color: #2563eb; font-size: 1.15rem; font-weight: 800; }
    .status-ready, .status-build {
        display: inline-block;
        border-radius: 999px;
        padding: .3rem .7rem;
        font-weight: 700;
        margin-bottom: .5rem;
    }
    .status-ready { color: #065f46; background: #d1fae5; }
    .status-build { color: #9a3412; background: #ffedd5; }
    div.stButton > button {
        border: 0;
        border-radius: 12px;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #2dd4bf);
        color: #082f49;
    }
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, .78);
        border: 1px solid rgba(147, 197, 253, .55);
        border-radius: 16px;
        padding: .35rem .55rem;
    }
    </style>
    <div class="hero">
        <h1>Three Edges RAG</h1>
        <p>Local FAISS retrieval &middot; OpenAI answers &middot; LangSmith observability</p>
    </div>
    """,
    unsafe_allow_html=True,
)

chunk_count = vector_store_count()
index_ready = chunk_count > 0

with st.sidebar:
    st.header("Knowledge base")
    st.write(f"**Document:** {PDF_PATH.name}")
    st.metric("Stored FAISS chunks", chunk_count)
    st.write(f"**OpenAI model:** `{os.getenv('OPENAI_MODEL', 'gpt-5.6-sol')}`")
    st.write(f"**LangSmith project:** `{os.environ['LANGSMITH_PROJECT']}`")
    top_k = st.slider("Chunks per question", min_value=2, max_value=10, value=5)

    if st.button("Build / rebuild FAISS index", use_container_width=True):
        with st.spinner("Reading, chunking, and embedding the PDF..."):
            try:
                built_chunks = build_faiss_index()
                st.success(f"Stored {built_chunks} chunks locally.")
                st.rerun()
            except Exception as exc:
                st.error(f"Indexing failed: {exc}")

with st.expander("How does each request travel?", expanded=True):
    if index_ready:
        st.markdown(
            '<span class="status-ready">Ready: FAISS index exists; the later-request path is active.</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-build">Setup: no index exists; the first request will build it.</span>',
            unsafe_allow_html=True,
        )

    first_tab, later_tab = st.tabs(["1. First request / missing index", "2. Every later request"])

    with first_tab:
        st.markdown(
            """
            <div class="flow-wrap">
              <span class="flow-step">Question</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Read PDF</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Split text</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Embed chunks</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Save FAISS</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Retrieve top-k</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step cloud">OpenAI</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step cloud">LangSmith trace</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step">Answer</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.table(
            [
                {"Step": "1", "Action": "Read the 30-page PDF", "Where": "Local"},
                {"Step": "2", "Action": "Split text and create embeddings", "Where": "Local"},
                {"Step": "3", "Action": "Save vectors and metadata in FAISS", "Where": "Local"},
                {"Step": "4", "Action": "Retrieve the most relevant chunks", "Where": "Local"},
                {"Step": "5", "Action": "Send question + retrieved text to the LLM", "Where": "OpenAI"},
                {"Step": "6", "Action": "Record the model run", "Where": "LangSmith"},
                {"Step": "7", "Action": "Show answer and page sources", "Where": "Browser"},
            ]
        )

    with later_tab:
        st.markdown(
            """
            <div class="flow-wrap">
              <span class="flow-step">Question</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Embed question</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Search saved FAISS</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step local">Top-k context</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step cloud">OpenAI</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step cloud">LangSmith trace</span><span class="flow-arrow">&rarr;</span>
              <span class="flow-step">Answer</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.table(
            [
                {"Step": "1", "Action": "Create an embedding for the new question", "Where": "Local"},
                {"Step": "2", "Action": "Search the already-saved FAISS index", "Where": "Local"},
                {"Step": "3", "Action": "Select the top matching PDF chunks", "Where": "Local"},
                {"Step": "4", "Action": "Send question + retrieved text to the LLM", "Where": "OpenAI"},
                {"Step": "5", "Action": "Record the model run", "Where": "LangSmith"},
                {"Step": "6", "Action": "Show answer and page sources", "Where": "Browser"},
            ]
        )

st.subheader("Ask the document")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Ask a question about The Three Edges...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving context and asking OpenAI..."):
            try:
                answer, sources = answer_question(question, k=top_k)
                st.markdown(answer)

                with st.expander("Retrieved source passages"):
                    for index, source in enumerate(sources, start=1):
                        page = source.metadata.get("page_number", "?")
                        st.markdown(f"**{index}. Page {page}**")
                        st.write(source.page_content)
                        st.divider()

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
            except Exception as exc:
                st.error(f"Could not answer: {exc}")


