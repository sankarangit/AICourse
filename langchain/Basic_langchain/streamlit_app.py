import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# 1. Page Configuration & Setup
st.set_page_config(page_title="LangChain Chatbot", page_icon="🤖")
st.title("🤖 My First GenAI Chatbot")

# ==============================================================================
# DISPLAY APPLICATION FLOW AT THE TOP
# ==============================================================================
st.caption("### ⚙️ LangChain Architecture & Execution Flow")
st.info(
    "**Flow:** User Input ➔ `ChatPromptTemplate` ➔ `ChatOpenAI` (gpt-4o-mini) ➔ `StrOutputParser` ➔ UI Display"
)

with st.expander("🔍 Click to see detailed step-by-step execution path"):
    st.markdown("""
    1. **Initialize Components**: Load API Key, set up `ChatOpenAI`, and construct `ChatPromptTemplate`.
    2. **Capture User Input**: Receive message from Streamlit `st.chat_input`.
    3. **Pass History & Input**: Combine past `HumanMessage` and `AIMessage` history with current user prompt.
    4. **Format Prompt**: `MessagesPlaceholder` formats system instructions + history + new input.
    5. **Invoke Chain (`|`)**: Pipeline passes formatted prompt directly to `ChatOpenAI`.
    6. **Parse Output**: `StrOutputParser` converts raw model response (`AIMessage`) into plain text.
    7. **Update UI & State**: Display answer on screen and append exchange to `st.session_state.chat_history`.
    """)

st.divider()

# ==============================================================================
# LANGCHAIN SETUP
# ==============================================================================
load_dotenv()
openapi_key = os.getenv("OpenAPI_API_Key")

# Initialize Model & Chain
@st.cache_resource
def get_chain():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=openapi_key)
    output_parser = StrOutputParser()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful, friendly AI assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    # LCEL Chain Execution Flow: Prompt -> LLM -> Output Parser
    return prompt | llm | output_parser

chain = get_chain()

# Initialize Chat History in Streamlit Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display past messages in the UI
for message in st.session_state.chat_history:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# Handle user input
user_input = st.chat_input("Type your message here...")

if user_input:
    # 1. Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Generate response from LangChain
    with st.chat_message("assistant"):
        with st.spinner("Executing LangChain Pipeline..."):
            response = chain.invoke({
                "history": st.session_state.chat_history,
                "input": user_input
            })
            st.markdown(response)

    # 3. Save to session state history
    st.session_state.chat_history.append(HumanMessage(content=user_input))
    st.session_state.chat_history.append(AIMessage(content=response))