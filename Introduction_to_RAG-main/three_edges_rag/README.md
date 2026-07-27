# Three Edges - Single-file OpenAI RAG

All executable Python code is contained in `app.py`. The PDF is embedded locally
and retrieved from a persistent FAISS index. Retrieved context is sent to the
OpenAI API for answer generation, and LangSmith records the model runs.

## Configure credentials

Copy the template and put your actual keys in `.env`:

```powershell
Copy-Item .env.example .env
```

```dotenv
OpenAPI_API_Key=your-openai-api-key
LangSmith_API_Key=your-langsmith-api-key
OPENAI_MODEL=gpt-5.6-sol
LANGSMITH_PROJECT=my-second-app
```

Never commit `.env`; it is excluded by `.gitignore`.

## Install and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

You can also double-click `run_app.bat`. Use the sidebar button to rebuild the
FAISS index whenever the PDF changes.

## Data flow

1. `PyPDFLoader` reads the local PDF.
2. Local Hugging Face embeddings create vectors.
3. FAISS stores and retrieves vectors locally from `faiss_db/`.
4. Only the question and retrieved text passages are sent to OpenAI.
5. LangSmith records the LangChain model run under `my-second-app`.
