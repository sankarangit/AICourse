import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph

# 1. Load environment variables
load_dotenv()

openapi_key = os.getenv("OpenAPI_API_Key")
langsmith_key = os.getenv("LangSmith_API_Key")

# 2. Configure LangSmith & OpenAI
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = langsmith_key
os.environ["LANGSMITH_PROJECT"] = "my-KGDEMO-app"
os.environ["OPENAI_API_KEY"] = openapi_key

print("LangSmith is connected!")

# --- STEP 1: Document Loader ---
print("\n📁 Loading document...")
loader = TextLoader("sample_data.txt")
documents = loader.load()
print(f"✅ Loaded {len(documents)} document(s).")

# --- STEP 2: Entity Extraction ---
print("\n🤖 Initializing LLM and Graph Transformer...")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_transformer = LLMGraphTransformer(llm=llm)

print("🔍 Extracting entities and relationships...")
graph_documents = llm_transformer.convert_to_graph_documents(documents)

# --- STEP 3 (Part A): Store in Neo4j Aura DB ---
print("\n🔌 Connecting to Neo4j Aura DB...")
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

print("💾 Saving graph documents to Neo4j...")
graph.add_graph_documents(
    graph_documents, 
    include_source=True  # Links nodes back to the source text chunk
)

print("✨ Successfully stored graph data into Neo4j Aura DB!")