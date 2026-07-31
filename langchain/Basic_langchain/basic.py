#full-fledged, multi-turn AI chatbot application using LangChain Expression Language (LCEL), dynamic prompt templates, model wrappers, output parsers, and explicit chat history management.

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# 1. Load setup
load_dotenv()
openapi_key = os.getenv("OpenAPI_API_Key")

# 2. Setup Chain
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=openapi_key)
output_parser = StrOutputParser()

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful, friendly AI assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm | output_parser

# 3. Store conversation history
chat_history = []

print("="*50)
print("  Welcome to your LangChain AI Assistant!  ")
print("  (Type 'exit' or 'quit' to end the session)  ")
print("="*50 + "\n")

# 4. Interactive loop
while True:
    user_input = input("You: ").strip()
    
    if user_input.lower() in ["exit", "quit"]:
        print("\nAI: Goodbye! Have a great day!")
        break
        
    if not user_input:
        continue

    # Run chain
    response = chain.invoke({
        "history": chat_history,
        "input": user_input
    })

    print(f"AI: {response}\n")

    # Save memory state
    chat_history.append(HumanMessage(content=user_input))
    chat_history.append(AIMessage(content=response))