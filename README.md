# Automative Cognitive Orchestration System (ACOS)

A highly robust, production-ready **multi-agent orchestration** system developed by Arnav. ACOS leverages a sophisticated **supervisor routing agent**, a high-performance FastAPI backend, an interactive Streamlit frontend, PostgreSQL persistence, local RAG (ChromaDB), and knowledge graph retrieval to create a seamless cognitive assistant.

## Features

- **Supervisor Graph Architecture**: Intelligently routes requests through specialized agents including safety, intent, rewrite, retrieval, response, and evaluation agents.
- **Hybrid Retrieval System**: Combines Chroma vector search, BM25-style lexical matching, reranking, and local fallbacks for high-accuracy local RAG.
- **Human-in-the-Loop (HITL)**: Pauses recency-sensitive or high-risk workflows until user approval is granted directly from the UI.
- **Enterprise-Grade Ops**: Integrated authentication, thread history, LangGraph checkpoints, Prometheus metrics, and Grafana dashboards.
- **Local Knowledge Graph Reasoning**: Uses NetworkX for complex relationship-style queries and reasoning over documentation.

## Project Structure

- `acos_core/` - LangGraph orchestration, agents, and routing logic
- `acos_api/` - FastAPI service, endpoints, and persistence logic
- `acos_models/` - Pydantic schemas and shared models
- `acos_client/` - Client utilities
- `streamlit_app.py` - Streamlit User Interface
- `docker/` - Dockerfiles for containerization
- `monitoring/` - Prometheus and Grafana setup

## Setup and Installation

### 1. Environment Configuration
Create a `.env` file in the root directory based on the following template:

```env
OPENAI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here

PORT=8000
API_BASE_URL=http://localhost:8000

POSTGRES_CHECKPOINT_URI=postgresql://postgres:password@localhost:5432/agentdb
CHECKPOINT_FALLBACK_SQLITE=true
CHECKPOINT_DB_PATH=data/checkpoints/checkpoints.db

POSTGRES_STORE_URI=postgresql://postgres:password@localhost:5432/agentdb
STORE_FALLBACK_SQLITE=true
STORE_DB_PATH=data/store/store.db
STORE_NAMESPACE=default

USE_CHROMA_RAG=true
CHROMA_PERSIST_DIR=data/chroma_db
CHROMA_COLLECTION_NAME=local_pdf_docs
RAG_PDF_DIR=rag_docs
LOCAL_RAG_DB_PATH=data/rag/local_rag.db
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=150

HYBRID_ROUTER_ENABLE=true
HYBRID_ROUTER_MIN_CONFIDENCE=0.75

RAG_VECTOR_TOP_K=8
RAG_BM25_TOP_K=8
RAG_RERANK_TOP_K=6
RAG_RRF_K=60
RAG_ENABLE_LLM_RERANKER=true

GRAPH_RAG_ENABLED=true
GRAPH_RAG_PDF_DIR=graph_rag_docs
GRAPH_CHROMA_PERSIST_DIR=data/graph_chroma_db
GRAPH_CHROMA_COLLECTION_NAME=graph_pdf_docs
GRAPH_RAG_CHUNK_SIZE=1000
GRAPH_RAG_CHUNK_OVERLAP=150
GRAPH_RAG_CACHE_TTL_SECONDS=600

WEB_CACHE_TTL_SECONDS=300
RAG_CACHE_TTL_SECONDS=600

CACHE_USE_REDIS=false

ENABLE_USER_AUTH=true
USER_AUTH_SECRET=change_me_to_a_long_random_secret
USER_AUTH_TOKEN_TTL_SECONDS=86400
PASSWORD_HASH_ITERATIONS=210000

MCP_TOOLS_ENABLED=false
```

### 2. Running with Docker Compose
To start the entire orchestration platform (API, UI, and Monitoring):

```bash
docker compose up -d --build
```

- **Frontend (Streamlit)**: `http://localhost:8501`
- **Backend (FastAPI)**: `http://localhost:8000`
- **Grafana Dashboards**: `http://localhost:3001` (admin/admin)
- **Prometheus Metrics**: `http://localhost:9090`

## System Architecture

ACOS utilizes an intent router agent to evaluate queries and direct them to specialized sub-agents:
- `local:` prefix automatically routes to local RAG or Knowledge Graph.
- Math operations are routed to an isolated environment.
- Ambiguous queries trigger the clarification agent.

Checkpointer and conversation stores are securely maintained within PostgreSQL, ensuring graph execution continuity across complex agent operations.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
