import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
import networkx as nx

# 1. Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OpenAPI_API_Key")

# 2. Re-build the NetworkX Graph (Steps 1, 2, and 3 combined)
print("⚙️ Setting up Knowledge Graph for RAG...")
loader = TextLoader("sample_data.txt")
documents = loader.load()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_transformer = LLMGraphTransformer(llm=llm)
graph_documents = llm_transformer.convert_to_graph_documents(documents)

nx_graph = nx.MultiDiGraph()
for graph_doc in graph_documents:
    for node in graph_doc.nodes:
        nx_graph.add_node(node.id, type=node.type)
    for rel in graph_doc.relationships:
        nx_graph.add_edge(rel.source.id, rel.target.id, relation=rel.type)

# 3. Define a GraphRAG Query Function
def answer_with_graph_rag(question: str, target_entity: str):
    print(f"\n🔍 User Question: '{question}'")
    print(f"🎯 Target Entity Identified: '{target_entity}'")
    
    # Extract local neighborhood context from the NetworkX graph
    context_triples = []
    if target_entity in nx_graph:
        # Get outgoing connections
        for u, v, data in nx_graph.out_edges(target_entity, data=True):
            context_triples.append(f"- ({u}) [{data.get('relation')}] ({v})")
        # Get incoming connections
        for u, v, data in nx_graph.in_edges(target_entity, data=True):
            context_triples.append(f"- ({u}) [{data.get('relation')}] ({v})")
    
    context_text = "\n".join(context_triples)
    print(f"\n📄 Retrieved Graph Context:\n{context_text}")
    
    # 4. Prompt the LLM using the structured graph context instead of raw chunks
    prompt = f"""
    You are an expert assistant. Answer the user's question accurately using ONLY the provided Knowledge Graph context below.
    
    Knowledge Graph Context:
    {context_text}
    
    User Question: {question}
    """
    
    response = llm.invoke(prompt)
    return response.content

# 5. Test the GraphRAG System
question = "Who founded Apple Inc. and who succeeded Steve Jobs as CEO?"
# For this simple demo, we query around the 'Apple Inc.' and 'Steve Jobs' hub
answer = answer_with_graph_rag(question, target_entity="Apple Inc.")

print(f"\n🤖 Final GraphRAG Answer:\n{answer}")