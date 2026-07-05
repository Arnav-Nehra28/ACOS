<div align="center">

# 🧠 ACOS — Automative Cognitive Orchestration System

**A production-grade, supervisor-routed multi-agent AI platform built with LangGraph, FastAPI, and Streamlit.**

[![CI](https://github.com/Arnav-Nehra28/ACOS/actions/workflows/ci.yml/badge.svg)](https://github.com/Arnav-Nehra28/ACOS/actions/workflows/ci.yml)
[![CD](https://github.com/Arnav-Nehra28/ACOS/actions/workflows/cd-release.yml/badge.svg)](https://github.com/Arnav-Nehra28/ACOS/actions/workflows/cd-release.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<br/>

[Architecture](#-system-architecture) · [Quick Start](#-quick-start) · [Agent Graph](#-the-12-agent-orchestration-graph) · [API Reference](#-api-reference) · [Deployment](#-deployment) · [Monitoring](#-observability-stack)

<br/>

<img src="media/agent_architecture.png" alt="ACOS Architecture" width="780"/>

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [The 12-Agent Orchestration Graph](#-the-12-agent-orchestration-graph)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Configuration Reference](#-configuration-reference)
- [API Reference](#-api-reference)
- [Deployment](#-deployment)
- [Observability Stack](#-observability-stack)
- [Local RAG & Knowledge Graph](#-local-rag--knowledge-graph)
- [Human-in-the-Loop (HITL)](#-human-in-the-loop-hitl)
- [Caching Strategy](#-caching-strategy)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Known Limitations](#-known-limitations)
- [License](#-license)

---

## 🔭 Overview

**ACOS** (Automative Cognitive Orchestration System) is a highly robust, production-ready multi-agent orchestration platform. It implements a **supervisor routing pattern** using LangGraph to intelligently direct user queries through a pipeline of 12 specialized agents — each responsible for a distinct cognitive task such as safety moderation, intent classification, web retrieval, local RAG, knowledge graph reasoning, mathematical computation, and quality evaluation.

The system is designed with enterprise-grade concerns in mind: per-user authentication, dual-layer persistence (PostgreSQL + SQLite fallback), hybrid retrieval with reranking, real-time streaming, and a full observability stack.

### What You Can Build With ACOS

| Use Case | Description |
|---|---|
| **Multi-Agent Assistants** | Supervisor-routed agents that handle safety, retrieval, reasoning, and response generation |
| **Agentic RAG Systems** | Hybrid retrieval combining vector search, BM25 lexical matching, and LLM-based reranking |
| **Real-Time Chat Services** | FastAPI backend with SSE streaming + interactive Streamlit frontend |
| **Knowledge Graph Reasoning** | NetworkX-powered relationship extraction and entity-linking over local documentation |
| **Tool-Augmented Agents** | MCP tool bridge for `web_search` and `calculator` with automatic local fallbacks |

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🏗️ Core Architecture
- 12-agent LangGraph orchestration graph
- Hybrid supervisor routing (deterministic rules + LLM fallback)
- LlamaGuard content moderation (`safety_agent`)
- Graph-native Human-in-the-Loop (HITL) approval workflows
- Heuristic evaluation agent for quality auditing

</td>
<td width="50%">

### 🔍 Retrieval & Reasoning
- Local RAG with ChromaDB + SQLite fallback
- Hybrid retrieval: vector + BM25 + Reciprocal Rank Fusion
- Optional LLM reranker with heuristic fallback
- Knowledge graph reasoning (NetworkX) for relationship queries
- TTL caching for web search and RAG retrieval

</td>
</tr>
<tr>
<td width="50%">

### 🔐 Security & Persistence
- Per-user authentication with PBKDF2-SHA256 password hashing
- HMAC-signed bearer tokens with configurable TTL
- Dual-layer persistence: LangGraph checkpointer + conversation store
- PostgreSQL primary with automatic SQLite fallback
- HITL decision audit trail per user/thread

</td>
<td width="50%">

### 🚀 Operations & Deployment
- FastAPI service with `/invoke`, `/stream`, `/metrics`, `/healthz`, `/readyz`
- Docker Compose for local development (API + UI + Prometheus + Grafana)
- Kubernetes manifests with health/readiness probes
- CI pipeline with pytest + Docker build verification
- CD pipeline with Docker Hub image publishing

</td>
</tr>
</table>

---

## 🏛️ System Architecture

### Runtime Agent Flow

```mermaid
%%{init: {"flowchart":{"nodeSpacing":45,"rankSpacing":65},"themeVariables":{"fontSize":"14px"}}}%%
flowchart TD
    U[User in Streamlit] --> AUTH[Login / Register]
    AUTH --> HIST[Load conversation history]
    HIST --> Q[User sends message]
    Q --> API[FastAPI /invoke or /stream]

    API --> STOREH[Store human message]
    API --> HMAP[HITL mapper for approve/reject]
    HMAP --> CFG[Build graph config + thread_id]
    CFG --> LG[LangGraph research_assistant]
    CFG --> CHK[Postgres checkpoints]

    LG --> SA[safety_agent]
    SA --> IR[intent_router_agent]

    IR -->|clarify| CA[clarification_agent]
    CA --> EVA[evaluation_agent]

    IR -->|rewrite| QR[query_rewriter_agent]
    QR --> IR

    IR -->|math| MA[math_agent]
    MA --> RESP[response_agent]

    IR -->|rag| RA[rag_agent]
    RA --> RESP

    IR -->|kg| KG[knowledge_graph_agent]
    KG --> RA

    IR -->|general| RESP

    IR -->|web / hybrid| RG[recency_guard_agent]
    RG --> WH[web_hitl_gate_agent]

    WH -->|awaiting| WAIT[Wait for user decision]
    WAIT --> BTN[Approve / Reject]
    BTN --> API

    WH -->|approved web| WS[web_search_agent]
    WS -->|web route| RESP

    WH -->|approved hybrid| WS
    WS -->|hybrid route| RA

    WH -->|rejected| REJ[Rejection follow-up]
    REJ --> EVA

    RESP --> EVA
    EVA --> END[Graph END]
    END --> APIRESP[Return to Streamlit]
    APIRESP --> STOREA[Store AI message]
    STOREA --> CST[conversation_store]
    END --> HITLDB[Persist HITL decision]
    HITLDB --> HITL[hitl_events]

    API --> METRICS[/healthz · /readyz · /metrics]
    METRICS --> PROM[Prometheus]
    PROM --> GRAF[Grafana]
```


---

## 🤖 The 12-Agent Orchestration Graph

| # | Agent | Role | Key Behavior |
|---|---|---|---|
| 1 | `safety_agent` | Content moderation | LlamaGuard-based safety screening of all user inputs |
| 2 | `intent_router_agent` | Supervisor / Router | Hybrid routing: deterministic rules first, LLM classifier fallback for low-signal queries |
| 3 | `clarification_agent` | Follow-up generation | Asks targeted follow-up when intent is ambiguous; ends current run |
| 4 | `query_rewriter_agent` | Query refinement | Deterministic + LLM-based rewrite for vague queries (e.g., "news" → "latest AI news today") |
| 5 | `recency_guard_agent` | Temporal filtering | Extracts recency preferences ("today", "this week") and applies date-range constraints |
| 6 | `web_hitl_gate_agent` | Human approval gate | Pauses graph execution for recency-sensitive web queries; waits for user approve/reject |
| 7 | `web_search_agent` | Web retrieval | Performs web search via MCP tool bridge with relevance + recency filtering |
| 8 | `knowledge_graph_agent` | Relationship reasoning | NetworkX-based entity relationship extraction over graph RAG evidence |
| 9 | `rag_agent` | Local document retrieval | Hybrid retrieval: Chroma vector + BM25 + RRF + optional LLM reranking |
| 10 | `math_agent` | Computation | Safe mathematical expression evaluation via MCP calculator or `numexpr` |
| 11 | `response_agent` | Answer synthesis | Generates final response using gathered evidence with source citations |
| 12 | `evaluation_agent` | Quality audit | Heuristic quality scoring of the final response |

### Routing Logic (Supervisor)

The `intent_router_agent` implements a **hybrid routing strategy**:

```
1. Deterministic rules (high precision, low latency)
   ├── `local:` prefix          → rag / kg
   ├── Relationship keywords    → kg
   ├── Ambiguous pronouns       → clarify
   ├── Vague but rewritable     → rewrite
   ├── Math symbols/keywords    → math
   ├── Web/news keywords        → web
   ├── Local project keywords   → rag
   └── Web + local keywords     → hybrid

2. LLM classifier fallback (confidence-gated)
   └── Only fires for low-signal queries where rules produce no match
   └── Requires confidence ≥ 0.75 (configurable)

3. Safe fallback
   └── general (when classifier confidence is below threshold)
```

---

## 📁 Project Structure

```
acos-orchestrator/
├── acos_core/                          # 🧠 Agent orchestration engine
│   ├── research_assistant.py           #    LangGraph graph definition + all 12 agents
│   ├── tools.py                        #    Web search + filtering logic
│   ├── local_rag.py                    #    Local RAG (ChromaDB + hybrid retrieval)
│   ├── graph_rag.py                    #    Graph RAG Chroma retrieval store
│   ├── knowledge_graph.py              #    NetworkX relationship extraction
│   ├── llama_guard.py                  #    LlamaGuard content moderation
│   ├── mcp_client.py                   #    MCP tool bridge client
│   ├── mcp_bridge_client.py            #    MCP stdio bridge subprocess
│   └── mcp_tool_server.py              #    MCP tool server (web_search + calculator)
│
├── acos_api/                           # 🌐 FastAPI backend service
│   ├── service.py                      #    All API endpoints + auth + checkpointer
│   ├── persistence_store.py            #    Conversation store (Postgres / SQLite)
│   └── test_service.py                 #    Service integration tests
│
├── acos_models/                        # 📐 Shared Pydantic schemas
│   ├── schema.py                       #    ChatMessage, UserInput, Feedback, Auth models
│   └── test_schema.py                  #    Schema unit tests
│
├── acos_client/                        # 📡 Client utilities
│   └── client.py                       #    AgentClient (HTTP + SSE streaming)
│
├── streamlit_app.py                    # 🎨 Streamlit chat UI
├── run_service.py                      #    Backend entry point
├── run_client.py                       #    CLI client entry point
│
├── docker/                             # 🐳 Container definitions
│   ├── Dockerfile.service              #    API container
│   └── Dockerfile.app                  #    Frontend container
│
├── compose.yaml                        #    Docker Compose (full stack)
│
├── k8s/                                # ☸️ Kubernetes manifests
│   ├── agent-deployment.yaml           
│   ├── streamlit-deployment.yaml       
│   ├── prometheus-deployment.yaml      
│   ├── grafana-deployment.yaml         
│   └── kustomization.yaml              #    One-command deploy: kubectl apply -k k8s
│
├── monitoring/                         # 📊 Observability
│   └── prometheus.yml                  #    Prometheus scrape config
│
├── scripts/ingestion/                  # 📥 Data ingestion scripts
│   ├── ingest_local_rag_pdfs.py        #    PDF → ChromaDB (local RAG)
│   ├── ingest_graph_rag_pdfs.py        #    PDF → Graph ChromaDB (knowledge graph)
│   └── generate_synthetic_graph_pdfs.py#    Synthetic PDFs for KG testing
│
├── docs/architecture/                  # 📖 Architecture documentation
│   ├── agent_runtime_flow.md           #    Human-readable flow explainer
│   └── agent_runtime_flow.mmd          #    Mermaid source
│
├── .github/workflows/                  # ⚙️ CI/CD
│   ├── ci.yml                          #    Test + Docker build on push/PR
│   └── cd-release.yml                  #    Docker Hub publish on version tags
│
├── requirements.txt                    
├── test-requirements.txt               
└── LICENSE                             
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** installed
- At least one LLM API key: `OPENAI_API_KEY` or `GROQ_API_KEY`

### 1. Clone the Repository

```bash
git clone https://github.com/Arnav-Nehra28/ACOS.git
cd ACOS
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# ─── LLM Provider Keys (at least one required) ───
OPENAI_API_KEY=sk-your-openai-key
GROQ_API_KEY=gsk_your-groq-key

# ─── Service Configuration ───
PORT=8000
API_BASE_URL=http://localhost:8000

# ─── Persistence (auto-falls back to SQLite) ───
CHECKPOINT_FALLBACK_SQLITE=true
CHECKPOINT_DB_PATH=data/checkpoints/checkpoints.db
STORE_FALLBACK_SQLITE=true
STORE_DB_PATH=data/store/store.db

# ─── RAG Configuration ───
USE_CHROMA_RAG=true
CHROMA_PERSIST_DIR=data/chroma_db
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# ─── Authentication ───
ENABLE_USER_AUTH=true
USER_AUTH_SECRET=change_me_to_a_long_random_secret
```

> 💡 See the full [Configuration Reference](#-configuration-reference) below for all available options.

### 3. Launch the Full Stack

```bash
docker compose up -d --build
```

### 4. Access the Services

| Service | URL | Notes |
|---|---|---|
| **Streamlit UI** | [http://localhost:8501](http://localhost:8501) | Register → Login → Chat |
| **FastAPI Backend** | [http://localhost:8000](http://localhost:8000) | REST API + SSE streaming |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | Metrics dashboard |
| **Grafana** | [http://localhost:3001](http://localhost:3001) | Visualization (admin/admin) |

---

## ⚙️ Configuration Reference

<details>
<summary><strong>📦 Full .env Configuration</strong> (click to expand)</summary>

```env
# ─── LLM Providers ───
OPENAI_API_KEY=...
GROQ_API_KEY=...

# ─── Service ───
PORT=8000
API_BASE_URL=http://localhost:8000

# ─── LangGraph Checkpointer (PostgreSQL) ───
POSTGRES_CHECKPOINT_URI=postgresql://postgres:password@localhost:5432/agentdb
CHECKPOINT_FALLBACK_SQLITE=true
CHECKPOINT_DB_PATH=data/checkpoints/checkpoints.db

# ─── Conversation Store ───
POSTGRES_STORE_URI=postgresql://postgres:password@localhost:5432/agentdb
STORE_FALLBACK_SQLITE=true
STORE_DB_PATH=data/store/store.db
STORE_NAMESPACE=default

# ─── Local RAG / ChromaDB ───
USE_CHROMA_RAG=true
CHROMA_PERSIST_DIR=data/chroma_db
CHROMA_COLLECTION_NAME=local_pdf_docs
RAG_PDF_DIR=rag_docs
LOCAL_RAG_DB_PATH=data/rag/local_rag.db
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=150

# ─── Hybrid Router ───
HYBRID_ROUTER_ENABLE=true
HYBRID_ROUTER_MIN_CONFIDENCE=0.75

# ─── Hybrid RAG Retrieval + Reranking ───
RAG_VECTOR_TOP_K=8
RAG_BM25_TOP_K=8
RAG_RERANK_TOP_K=6
RAG_RRF_K=60
RAG_ENABLE_LLM_RERANKER=true

# ─── Graph RAG (Knowledge Graph Store) ───
GRAPH_RAG_ENABLED=true
GRAPH_RAG_PDF_DIR=graph_rag_docs
GRAPH_CHROMA_PERSIST_DIR=data/graph_chroma_db
GRAPH_CHROMA_COLLECTION_NAME=graph_pdf_docs
GRAPH_RAG_CHUNK_SIZE=1000
GRAPH_RAG_CHUNK_OVERLAP=150
GRAPH_RAG_CACHE_TTL_SECONDS=600

# ─── TTL Caches ───
WEB_CACHE_TTL_SECONDS=300
RAG_CACHE_TTL_SECONDS=600

# ─── Redis (optional shared cache) ───
CACHE_USE_REDIS=false
REDIS_URL=redis://localhost:6379/0

# ─── Authentication ───
ENABLE_USER_AUTH=true
USER_AUTH_SECRET=change_me_to_a_long_random_secret
USER_AUTH_TOKEN_TTL_SECONDS=86400
PASSWORD_HASH_ITERATIONS=210000

# ─── MCP Tools (optional) ───
MCP_TOOLS_ENABLED=false
MCP_TOOL_SERVER_COMMAND=python
MCP_TOOL_SERVER_SCRIPT=acos_core/mcp_tool_server.py
MCP_BRIDGE_COMMAND=python
MCP_BRIDGE_SCRIPT=acos_core/mcp_bridge_client.py
MCP_CALL_TIMEOUT_SECONDS=20
```

</details>

---

## 🛰️ API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user and receive a bearer token |
| `POST` | `/auth/login` | Authenticate and receive a bearer token |

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/invoke` | Non-streaming chat response |
| `POST` | `/stream` | Streaming chat response (SSE) |
| `POST` | `/feedback` | Submit user feedback/rating |

### Conversation & History

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/store/threads` | List authenticated user's conversation threads |
| `GET` | `/store/{thread_id}` | Retrieve persisted messages for a thread |

### HITL (Human-in-the-Loop)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/hitl/web_decision` | Record a HITL audit event |
| `GET` | `/hitl/web_decisions` | List authenticated user's HITL audit records |

### Web Search

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/web_search/preview` | Manual web search preview (for external clients) |

### Operations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness probe |
| `GET` | `/metrics` | Prometheus scrape endpoint |

> 🔒 When `ENABLE_USER_AUTH=true`, all non-auth endpoints require `Authorization: Bearer <access_token>`.

---

## 📦 Deployment

### Docker Compose (Local Development)

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f acos_api

# Tear down
docker compose down
```

### Kubernetes (Production-Ready)

Beginner-friendly manifests are included in `k8s/` with health and readiness probes:

```bash
# One-command deploy
kubectl apply -k k8s

# Verify pods
kubectl get pods -n acos
```

See [k8s/README.md](k8s/README.md) for detailed step-by-step instructions.

### Release Tagging (CD)

```bash
git tag v1.0.0
git push origin v1.0.0
# → Triggers CD pipeline → publishes Docker images to Docker Hub
```

---

## 📊 Observability Stack

ACOS ships with a complete **Prometheus + Grafana** monitoring stack.

### Prometheus Targets

Verify the `acos_api` target is `UP`:

```
http://localhost:9090/targets
```

### Recommended Grafana Dashboard Panels

| Panel | PromQL Query |
|---|---|
| **Request Rate** | `sum(rate(http_requests_total[5m]))` |
| **Error Rate (5xx)** | `sum(rate(http_requests_total{status_code=~"5.."}[15m])) / clamp_min(sum(rate(http_requests_total[15m])), 1e-9)` |
| **P95 Latency** | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[15m])))` |
| **Traffic by Endpoint** | `sum by (path) (rate(http_requests_total[5m]))` |
| **Status Code Distribution** | `sum by (status_code) (rate(http_requests_total[5m]))` |

---

## 📚 Local RAG & Knowledge Graph

### Ingest PDFs into Local RAG

```bash
# Place PDFs in the rag_docs/ directory, then run:
python scripts/ingestion/ingest_local_rag_pdfs.py --pdf-dir rag_docs --reset
```

Query with the `local:` prefix:
```
local: summarize the uploaded pdfs
```

### Ingest PDFs for Knowledge Graph

```bash
# Place relationship-focused PDFs in graph_rag_docs/, then run:
python scripts/ingestion/ingest_graph_rag_pdfs.py --pdf-dir graph_rag_docs --reset
```

Query with relationship-style language:
```
local: how is streamlit connected to fastapi in this project
```

### Retrieval Pipeline

```
User Query
    │
    ├── 1. Chroma Vector Retrieval (semantic similarity)
    ├── 2. BM25 Lexical Ranking (keyword matching)
    ├── 3. Reciprocal Rank Fusion (RRF merge)
    └── 4. LLM Reranker (optional, heuristic fallback)
            │
            └── Top-K results → response_agent
```

---

## 🔄 Human-in-the-Loop (HITL)

For recency-sensitive web queries (e.g., "latest AI news this week"), ACOS implements a **graph-native HITL workflow**:

1. `recency_guard_agent` detects temporal intent and extracts date constraints
2. `web_hitl_gate_agent` fetches preview results and pauses graph execution
3. The Streamlit UI renders **Approve / Reject** buttons (plain text also works: `approve` or `reject: <reason>`)
4. On approval → `web_search_agent` generates the full answer
5. On rejection → `evaluation_agent` produces a follow-up message
6. All decisions are persisted in the `hitl_events` audit table

---

## ⚡ Caching Strategy

| Layer | Backend | TTL | Scope |
|---|---|---|---|
| **Web Search Cache** | Redis / In-memory | 300s | `perform_web_search()` results keyed by query + recency |
| **RAG Cache** | Redis / In-memory | 600s | `search_local_knowledge()` results keyed by query + limit |
| **Graph RAG Cache** | Redis / In-memory | 600s | Knowledge graph retrieval results |

- If `REDIS_URL` is configured and reachable, caches use Redis (`SETEX`)
- If Redis is unavailable, the system automatically falls back to local in-memory TTL caches
- RAG cache is cleared automatically after PDF ingestion/reset

---

## ⚙️ CI/CD Pipeline

### Continuous Integration (`ci.yml`)

Triggers on every `push` and `pull_request` to `main`:

1. **Python Tests** — runs `pytest` against `acos_api/test_service.py` and `acos_models/test_schema.py`
2. **Docker Build Check** — verifies both `Dockerfile.service` and `Dockerfile.app` build successfully

### Continuous Deployment (`cd-release.yml`)

Triggers on version tags (`v*`) or manual dispatch:

1. Builds and publishes Docker images to Docker Hub:
   - `<namespace>/acos-api:<version>`
   - `<namespace>/acos-frontend:<version>`

**Required GitHub Secrets:**
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

---

## ⚠️ Known Limitations

| Area | Limitation |
|---|---|
| `evaluation_agent` | Heuristic-based quality audit, not factual verification |
| `clarification_agent` | Ends the current graph run; the actual answer comes on the next user turn |
| Hybrid Router | LLM classifier confidence thresholds can misroute low-signal queries |
| RAG Quality | Depends on chunking parameters, embedding model, ingestion quality, and reranker behavior |
| MCP Tools | Requires a separate `.venv` with `mcp` package installed for the sidecar bridge |

---

## 📝 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License · Copyright (c) 2026 Arnav
```

