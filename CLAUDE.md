# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
uv sync                                # install deps from pyproject.toml / uv.lock
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
./run.sh                               # equivalent: cd backend && uv run uvicorn app:app --reload --port 8000
```

- Web UI: http://localhost:8000  •  Swagger: http://localhost:8000/docs
- Requires Python 3.13+ (`pyproject.toml`) and `uv`.
- First launch is slow: documents in `docs/` are ingested into ChromaDB at startup ([backend/app.py:88-98](backend/app.py#L88-L98)). Vectors persist in `backend/chroma_db/` (gitignored).
- No test suite, linter config, or build step exists in this repo. Don't invent commands for them.
- Always use `uv` for Python in this repo — `uv sync` / `uv add` / `uv run ...`. Never invoke `pip` directly, and never use bare `python` (there is no activated virtualenv).

## Architecture

This is a tool-using RAG chatbot, not a classic "retrieve-then-stuff-context" RAG. The LLM decides whether to search.

### Request flow (one user query)

```
script.js  →  POST /api/query  →  RAGSystem.query()  →  AIGenerator.generate_response()
                                                              │
                                                              ├─ 1st Anthropic call (with tools)
                                                              │   └─ if stop_reason == "tool_use":
                                                              │        CourseSearchTool.execute() → VectorStore.search() → Chroma
                                                              │        (writes self.last_sources as a side-effect)
                                                              └─ 2nd Anthropic call (NO tools) → final text
```

Then `RAGSystem.query()` pulls sources out of the tool via `ToolManager.get_last_sources()` and resets them ([backend/rag_system.py:130-133](backend/rag_system.py#L130-L133)). Sources are an **out-of-band side-channel** — Claude never sees the source list; it only sees formatted chunks. If Claude chooses not to call the search tool, `sources == []`.

The "no tools on the second call" pattern ([backend/ai_generator.py:127-131](backend/ai_generator.py#L127-L131)) is intentional: it caps tool use at one round-trip per query and matches the "One search per query maximum" rule in `AIGenerator.SYSTEM_PROMPT`. Don't add a tool-use loop unless you also revisit that prompt.

### Component ownership

`RAGSystem` ([backend/rag_system.py](backend/rag_system.py)) is the only orchestrator — it owns one instance each of `DocumentProcessor`, `VectorStore`, `AIGenerator`, `SessionManager`, `ToolManager`, `CourseSearchTool`. Everything else is a single-responsibility leaf. New tools should implement the `Tool` ABC in [backend/search_tools.py](backend/search_tools.py) and be registered on `ToolManager` in `RAGSystem.__init__`.

### Two ChromaDB collections (not one)

[backend/vector_store.py](backend/vector_store.py) maintains:

- **`course_catalog`** — one doc per course; document text = course title; lessons stored as a JSON-string in metadata (Chroma can't store nested lists). Used for fuzzy course-name resolution (`_resolve_course_name`, top-1 semantic match).
- **`course_content`** — one doc per chunk, with `course_title` / `lesson_number` / `chunk_index` metadata, filtered via Chroma `where` clauses.

A search with a `course_name` argument is a **two-step query**: resolve title against `course_catalog`, then filter `course_content`. This is why partial names like "MCP" match.

### Course title is the primary key

[backend/rag_system.py:87](backend/rag_system.py#L87) and [backend/vector_store.py:159](backend/vector_store.py#L159) — re-ingesting a folder skips any file whose parsed course title already exists. The Chroma ID for catalog entries is the title itself. Renaming a course in a source file creates a duplicate; it does not update the existing record. `clear_existing=True` is the only way to force a rebuild.

### Document format expected by `DocumentProcessor`

Course `.txt` files in `docs/` must start with these three header lines, then lesson blocks:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson body...>
```

Parser in [backend/document_processor.py:97-259](backend/document_processor.py#L97-L259). Chunking is sentence-aware with overlap (`CHUNK_SIZE=800`, `CHUNK_OVERLAP=100` in [backend/config.py](backend/config.py)). **Known inconsistency**: the *last* lesson's chunks get a richer `"Course {title} Lesson {N} content:"` prefix on every chunk ([document_processor.py:234](backend/document_processor.py#L234)), while earlier lessons only prefix the first chunk ([document_processor.py:185-188](backend/document_processor.py#L185-L188)). Preserve this if touching that code unless deliberately fixing it.

### Sessions

`SessionManager` is in-memory only (a plain dict, [backend/session_manager.py](backend/session_manager.py)). Restarting the server drops all conversation history. `MAX_HISTORY=2` exchanges = 4 messages retained. The browser learns its session ID from the first response ([frontend/script.js:79-81](frontend/script.js#L79-L81)) — clients send `session_id: null` on turn 1.

### Frontend

Static files in [frontend/](frontend/) served by FastAPI's `StaticFiles` mount at `/` ([backend/app.py:119](backend/app.py#L119)). Order matters: API routes are registered before the mount so they take precedence. No build step, no framework — vanilla JS + `marked` CDN for markdown rendering of assistant replies.

### Known rough edges (don't "fix" without reason)

- `backend/app.py` uses the deprecated `@app.on_event("startup")` — works but warns on modern FastAPI; switching to `lifespan` is a real change, not a no-op.
- `query_documents` is `async def` but calls the sync `rag_system.query()`, blocking the event loop during the LLM round-trip. Fine for low concurrency.
- [main.py](main.py) at the repo root is a leftover stub (`print("Hello from starting-codebase!")`) — not the entrypoint. The real entrypoint is `backend/app.py:app`.
