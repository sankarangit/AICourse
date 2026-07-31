import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.callbacks.manager import get_openai_callback

# 1. Page Config & Title
st.set_page_config(page_title="LangChain Cost & Token Tracker", page_icon="🤖")
st.title("🤖 GenAI Chatbot (with Token & Cost Tracker)")

# Pricing Constants for gpt-4o-mini
INPUT_PRICE_PER_M = 0.15   # $0.15 per 1M prompt tokens
OUTPUT_PRICE_PER_M = 0.60  # $0.60 per 1M completion tokens

load_dotenv()
openapi_key = os.getenv("OpenAPI_API_Key")

# 2. Setup Chain
@st.cache_resource
def get_chain():
    # Streamlit works best when temperature and API keys are initialized clearly
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=openapi_key)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful, friendly AI assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    return prompt | llm  # Returning the raw message object so metadata stays intact

chain = get_chain()

# 3. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []  # Stores dicts: {"role": ..., "content": ..., "metrics": ...}

# 4. Display Existing Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display cost/tokens if this is an assistant message and metrics exist
        if msg["role"] == "assistant" and "metrics" in msg and msg["metrics"]:
            m = msg["metrics"]
            st.caption(
                f"📊 **Tokens:** {m['total_tokens']} "
                f"(Prompt: {m['prompt_tokens']} | Output: {m['completion_tokens']}) | "
                f"💵 **Cost:** `${m['cost']:.6f}`"
            )

# 5. Handle User Input
user_input = st.chat_input("Type your question here...")

if user_input:
    # Render user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Prepare chat history format for LangChain
    langchain_history = []
    for msg in st.session_state.messages[:-1]:  # exclude latest prompt
        if msg["role"] == "user":
            langchain_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_history.append(AIMessage(content=msg["content"]))

    # Generate AI response and calculate metrics
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            with get_openai_callback() as cb:
                # Call LangChain inside callback context
                response = chain.invoke({
                    "history": langchain_history,
                    "input": user_input
                })
                
                # Calculate costs manually for gpt-4o-mini
                prompt_cost = (cb.prompt_tokens / 1_000_000) * INPUT_PRICE_PER_M
                completion_cost = (cb.completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_M
                total_cost = prompt_cost + completion_cost

                metrics_data = {
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens,
                    "total_tokens": cb.total_tokens,
                    "cost": total_cost
                }

            # Display response text
            st.markdown(response.content)

            # Display metrics caption
            st.caption(
                f"📊 **Tokens:** {metrics_data['total_tokens']} "
                f"(Prompt: {metrics_data['prompt_tokens']} | Output: {metrics_data['completion_tokens']}) | "
                f"💵 **Cost:** `${metrics_data['cost']:.6f}`"
            )

    # Save Assistant message + metrics together in session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": response.content,
        "metrics": metrics_data
    })