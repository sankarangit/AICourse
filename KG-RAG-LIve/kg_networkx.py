import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_community.graphs import NetworkxEntityGraph
# Alternatively, NetworkX can be handled directly via networkx library structures

# 1. Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OpenAPI_API_Key")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LangSmith_API_Key")
os.environ["LANGSMITH_PROJECT"] = "my-KGDEMO-app"

# --- STEP 1 & 2: Load & Extract ---
print("📁 Loading document and extracting entities...")
loader = TextLoader("sample_data.txt")
documents = loader.load()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_transformer = LLMGraphTransformer(llm=llm)
graph_documents = llm_transformer.convert_to_graph_documents(documents)

# --- STEP 3 (Part B): Store in NetworkX ---
print("\n🧠 Building In-Memory NetworkX Graph...")

# Initialize an empty NetworkX graph wrapper or raw networkx graph
import networkx as nx

# We can populate a native NetworkX MultiDiGraph from our extracted graph_documents
nx_graph = nx.MultiDiGraph()

for graph_doc in graph_documents:
    # Add nodes with their types as attributes
    for node in graph_doc.nodes:
        nx_graph.add_node(node.id, type=node.type)
    
    # Add edges with relationship types
    for rel in graph_doc.relationships:
        nx_graph.add_edge(rel.source.id, rel.target.id, relation=rel.type)

print(f"✅ NetworkX Graph Built Successfully!")
print(f"• Total Nodes: {nx_graph.number_of_nodes()}")
print(f"• Total Edges: {nx_graph.number_of_edges()}")

# Inspect graph neighbors/connections
print("\n--- Exploring Apple Inc. Connections in NetworkX ---")
target_node = "Apple Inc."
if target_node in nx_graph:
    # Outgoing edges
    for u, v, data in nx_graph.out_edges(target_node, data=True):
        print(f"({u}) --[{data.get('relation')}]--> ({v})")
    # Incoming edges
    for u, v, data in nx_graph.in_edges(target_node, data=True):
        print(f"({u}) --[{data.get('relation')}]--> ({v})")
else:
    print(f"{target_node} not found in graph keys.")