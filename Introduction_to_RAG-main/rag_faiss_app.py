import os
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OpenAPI_API_Key")
langsmith_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LangSmith_API_Key")

if not openai_key:
    raise RuntimeError("Set OPENAI_API_KEY (or OpenAPI_API_Key) in your .env file.")

os.environ["OPENAI_API_KEY"] = openai_key

# LangChain automatically sends traces to LangSmith when these variables are set.
# Tracing remains optional, so the RAG chat can still run without a LangSmith key.
if langsmith_key:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = langsmith_key
    os.environ.setdefault("LANGSMITH_PROJECT", "pdf-rag-app")

PDF_PATH = "spotify_web_app_architecture.pdf"
FAISS_DB_PATH = "faiss_index"

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def create_vector_db():
    print("Loading PDF...")

    loader = PyPDFLoader(PDF_PATH)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)

    print("Creating FAISS vector DB...")

    vector_db = FAISS.from_documents(chunks, embeddings)
    vector_db.save_local(FAISS_DB_PATH)

    print("FAISS vector DB saved locally.")
    print(f"Total chunks stored: {len(chunks)}")


def load_vector_db():
    if not os.path.exists(FAISS_DB_PATH):
        create_vector_db()

    return FAISS.load_local(
        FAISS_DB_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )


def ask_question(question, vector_db):
    docs = vector_db.similarity_search(question, k=3)

    context = "\n\n".join(doc.page_content for doc in docs)

    prompt = ChatPromptTemplate.from_template("""
You are a helpful RAG assistant.

Answer the user's question only using the given context.
If the answer is not available in the context, say:
"I don't know from the provided document."

Context:
{context}

Question:
{question}

Answer:
""")

    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0
    )

    chain = prompt | llm

    response = chain.invoke(
        {
            "context": context,
            "question": question
        },
        config={
            "run_name": "answer-pdf-question",
            "tags": ["rag", "faiss", "pdf"],
            "metadata": {"retrieved_chunks": len(docs)}
        }
    )

    return response.content


def main():
    vector_db = load_vector_db()

    print("\nRAG app is ready.")
    print("Ask questions from your PDF.")
    print("Type 'exit' or 'quit' to stop. You can also press Ctrl+C.")
    if langsmith_key:
        print(f"LangSmith tracing: ON (project: {os.environ['LANGSMITH_PROJECT']})")
        print("View traces at https://smith.langchain.com")
    else:
        print("LangSmith tracing: OFF (set LANGSMITH_API_KEY to enable it)")

    try:
        while True:
            question = input("\nAsk question: ").strip()

            if question.lower() in {"exit", "quit"}:
                break

            if not question:
                print("Please enter a question, or type 'exit' to stop.")
                continue

            answer = ask_question(question, vector_db)

            print("\nAnswer:")
            print(answer)
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C / Ctrl+Z should close the chat without displaying a traceback.
        print()

    print("Chat ended. Bye!")


if __name__ == "__main__":
    main()
