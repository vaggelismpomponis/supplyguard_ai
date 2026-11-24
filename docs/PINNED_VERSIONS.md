# Pinned Versions Policy: Docker Base Images & Python Dependencies

**Project:** SupplyGuard AI (Capstone Project Code.Hub × PwC)  
**Scope:** Docker Base Images, Python Dependencies, Container Environment Stability  
**Target Date:** 2026-11-24  
**Status:** Agreed & Decided (All 5 Roles Aligned)  
**Primary Owner:** Platform Role  
**Related Documents:** [`ARCHITECTURE_CONTRACTS.md`](./ARCHITECTURE_CONTRACTS.md), [`PROJECT_CHECKLIST.md`](./PROJECT_CHECKLIST.md)

---

## 1. Motivation & Objectives

SupplyGuard AI is built by a distributed 5-person team across diverse host operating systems (Windows, macOS, Linux). To satisfy the core project milestone—**"The full stack boots up in <10 minutes on a clean clone on any laptop"**—all dependencies and container images must be deterministic.

Unpinned versions introduce silent build breakage, caching discrepancies, and API drift.

### Golden Rules
1. **Never use `:latest` or floating image tags.** Every Docker image must specify an exact, immutable tag.
2. **Never use loose dependency operators (`>=`, `~=`, `^`, unpinned).** Every Python package in `requirements.txt` must use exact equality (`==`).
3. **No unreviewed dependencies.** Any new package must be justified in a Pull Request and committed under the `deps` scope.

---

## 2. Docker Base Images Policy

All services configured in `Dockerfile` and `docker-compose.yml` adhere to the pinned versions below:

| Service / Container | Pinned Base Image | Justification / Role |
|---|---|---|
| **App Service (Chainlit UI & Deep Agents)** | `python:3.11-slim` | Debian-based slim Python 3.11 image. Minimal attack surface and small image size (~150MB), retaining compatibility with wheels for `psycopg[binary]`, `pgvector`, and `deepagents`. |
| **PostgreSQL + pgvector** | `pgvector/pgvector:pg16` | Official PostgreSQL 16 image bundled with pre-compiled `pgvector` extension. Provides vector similarity indexing (`vector(1536)`) on initial boot. |
| **Neo4j Graph Database** | `neo4j:5.26.0` | Official Neo4j Community Edition pinned to 5.26.0. Guarantees Cypher syntax compatibility and driver stability with `neo4j==5.26.0`. |
| **ChromaDB Vector Store** | `chromadb/chroma:0.5.23` | Official ChromaDB vector database container for indexing and retrieval benchmark comparison against pgvector. |
| **External Risk Service** | `python:3.11-slim` (or mock HTTP/JSON) | Simulated external risk and disruption feed service. |

### Docker Build Standards
- **Layer caching:** Copy `requirements.txt` and install dependencies *before* copying application code (`src/`).
- **No byte-code clutter:** Set `ENV PYTHONDONTWRITEBYTECODE=1` and `ENV PYTHONUNBUFFERED=1`.
- **Clean package manager cache:** Always run `rm -rf /var/lib/apt/lists/*` after `apt-get install` to keep layers slim.

---

## 3. Python Dependencies Policy (`requirements.txt`)

All production, persistence, and test packages are pinned to exact versions in `requirements.txt`.

### Baseline Inventory

```text
# Core Framework & Agent Workflow
chainlit==2.12.0              # Interactive chat interface, steps, and approval cards
deepagents==0.7.41            # Deep Agents orchestration framework with planning & scratchpad
langchain==1.5.2              # Composition and tool abstraction
langchain-anthropic==1.7.12   # Anthropic model client
langchain-core==1.8.4         # Core Pydantic primitives, messages, runnable protocols
langchain-openai==1.8.5       # OpenAI / Azure OpenAI runtime client
langgraph==1.2.24             # Stateful graph & checkpoint runtime

# Persistence & Data Stores
pgvector==0.5.1               # Python bindings for PostgreSQL vector extension
psycopg[binary,pool]==3.3.9   # PostgreSQL driver with connection pooling support
psycopg2-binary==2.9.13       # Secondary Postgres DBAPI driver
SQLAlchemy==2.1.9             # Relational ORM / driver dependency
neo4j==5.28.8                 # Official Neo4j Cypher driver
chromadb==0.5.23              # ChromaDB vector store client & benchmark store

# Integration & Protocols
mcp==1.30.0                   # Model Context Protocol for procurement & risk tools

# HTTP, Settings, Validation & Environment
httpx==0.28.1                 # Async/sync HTTP client
pydantic==2.14.4              # High-performance data validation for contracts
pydantic-settings==2.16.3     # Environment variable parsing and configuration
python-dotenv==1.2.4          # Local development .env loader
PyYAML==6.0.4                 # YAML parser for configuration and Compose tests
requests==2.34.2              # HTTP client

# Observability & Tracing
langsmith==0.16.1             # Execution tracing, run metadata, evaluation dataset

# Quality Assurance & Testing
pytest==9.2.0                 # Unit and integration test runner
pytest-asyncio==1.5.0         # Async test support
```

---

## 4. Dependency Change Management Protocol

To prevent dependency conflicts between roles, team members must follow this 4-step workflow:

```text
1. Propose in Stand-up  ──►  2. Update requirements.txt  ──►  3. Commit with scope 'deps'  ──►  4. Test Clean Install
   (Agree on necessity)        (Alphabetical & pinned)          feat(deps): add package          (<10 min verify)
```

1. **Stand-up Communication:** Announce in the daily stand-up before adding a dependency to avoid two members editing `requirements.txt` simultaneously.
2. **Alphabetical Sorting:** Keep entries grouped by domain and sorted alphabetically within their group to minimize diff collisions.
3. **Commit Scope:** Use the `deps` scope with conventional commit format:
   ```text
   feat(deps): pin pydantic-settings to 2.6.1
   ```
4. **Clean Verification:** Before opening a PR, test that `pip install --no-cache-dir -r requirements.txt` succeeds in a clean virtual environment or container.

---

## 5. Team Sign-off Matrix (Pinned Versions Policy)

| Role | Representative | Responsibility | Status | Date |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis | Docker base images, compose orchestration & OS portability | **Signed-off** | 2026-11-16 |
| **Workflow** | All members | LangGraph, LangChain Core & state checkpointer dependencies | **Signed-off** | 2026-11-16 |
| **Interface** | @AlexZarkalis | Chainlit UI library & websocket runtime | **Signed-off** | 2026-11-16 |
| **Knowledge** | @stef-fot | Neo4j driver, pgvector bindings & ingestion libraries | **Signed-off** | 2026-11-16 |
| **Quality** | @VickyMil-ai | Pytest, LangSmith SDK & evaluation dependencies | **Signed-off** | 2026-11-16 |
