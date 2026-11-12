# Stage 2 Tasks: RAG Core + Evals

Do the tasks in this sequence. One task at a time. Each task has a test.
You can generate the code with AI. Give the AI the **design** in each task. Then review the code and run the test.
When a task is done, change `[ ]` to `[x]`. Commit after each task.

```mermaid
flowchart LR
    A["A. Setup<br/>T1–T4"] --> B["B. Corpus<br/>T5–T6"] --> C["C. Index<br/>T7–T11"] --> D["D. Answer<br/>T12–T14"]
    D --> E["E. Evals<br/>T15–T18"] --> F["F. Improve<br/>T19–T22"] --> G["G. Arabic<br/>T23"]
    G --> H["H. Agent tool<br/>T24"] --> I["I. LangChain<br/>T25–T26"] --> J["J. Ship<br/>T27–T28"]
```

---

## Phase A: Setup

### [x] T1. Move to Python 3.12 (15 min)
**Why:** LangChain and LangGraph need Python 3.10 or newer. Your project uses 3.9.
**Do:**
```bash
uv venv --python 3.12
```
```bash
uv pip install -r requirements.txt
```
**Test:** `uv run python --version` shows 3.12. `uv run main.py` still works.

### [x] T2. Start PostgreSQL + pgvector in Docker (30 min)
**Design:** `docker-compose.yml` with one service:
- image `pgvector/pgvector:pg17`
- port **5433** on your Mac → 5432 in the container (5433 prevents a conflict with another local PostgreSQL)
- a named volume for the data, so the data stays after a restart
- user, password, and database `paperpilot`

Add `DATABASE_URL=postgresql://paperpilot:paperpilot@localhost:5433/paperpilot` to `.env` and `.env.example`.
**Test:**
```bash
docker compose up -d
```
```bash
docker compose exec db psql -U paperpilot -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"
```
**Done when:** You see the pgvector version.

### [ ] T3. Download the embedding model (10 min)
```bash
ollama pull bge-m3
```
**Test:**
```bash
curl http://localhost:11434/v1/embeddings -d '{"model":"bge-m3","input":"hello"}' | head -c 200
```
**Done when:** You see a list of numbers.

### [ ] T4. Add the new packages (10 min)
Add to `requirements.txt`: `pymupdf`, `psycopg[binary]`, `pgvector`, `numpy`. Install them.
Add `data/` to `.gitignore`.
**Test:** `uv run python -c "import fitz, psycopg, pgvector, numpy; print('ok')"`

---

## Phase B: Corpus

### [ ] T5. Choose the papers (45 min)
**Design:** `corpus.json`, a list of about 40 arXiv ids.
Start with these 17 classic papers (all checked):

| id | Paper |
|---|---|
| 2005.11401 | RAG (the original paper) |
| 2004.04906 | Dense Passage Retrieval (DPR) |
| 2004.12832 | ColBERT |
| 2104.08663 | BEIR benchmark |
| 2212.10496 | HyDE (query rewriting) |
| 2307.03172 | Lost in the Middle |
| 2310.11511 | Self-RAG |
| 2401.15884 | Corrective RAG (CRAG) |
| 2401.18059 | RAPTOR |
| 2404.16130 | GraphRAG |
| 2312.10997 | RAG survey |
| 2309.15217 | Ragas (RAG evals) |
| 2311.09476 | ARES (RAG evals) |
| 2402.03216 | BGE M3 embeddings |
| 2210.03629 | ReAct (agents) |
| 2302.04761 | Toolformer (tools) |
| 2303.11366 | Reflexion (agents) |

Then add about 23 more papers. Use your Stage 1 agent to find them. Topics: reranking, chunking, hybrid search, RAG evaluation, agent memory, multilingual retrieval.
**Done when:** `corpus.json` has 35–45 ids, and you know why each paper is there.

### [ ] T6. Download the PDFs (30 min)
**Design:** `download.py`
- Read `corpus.json`. For each id, download `https://arxiv.org/pdf/<id>` to `data/pdfs/<id>.pdf`.
- Skip a file that already exists.
- Wait 3 seconds between downloads. (arXiv asks for this. It is polite and it prevents a block.)
- Print a summary: downloaded, skipped, failed.

**Test:** `uv run download.py`, then run it a second time.
**Done when:** All PDFs are in `data/pdfs/`. The second run skips all of them.

---

## Phase C: Indexing

### [ ] T7. Parse one PDF (45 min)
**Design:** In `ingest.py`, a function `parse_pdf(path) -> list[dict]` that returns one dict for each page: `{"arxiv_id", "page", "text"}`. Use PyMuPDF (`fitz`). Pages start at 1.
**Test:** Parse `2005.11401.pdf`. Print page 3.
**Done when:** You can read the text. **Write in NOTES:** what is messy in the text? (Headers? Formulas? Hyphens at the end of lines?)

### [ ] T8. Chunk the pages (45 min)
**Design:** `chunk_pages(pages, size=1000, overlap=200) -> list[dict]`
- Split the text of each page into chunks of `size` characters, with `overlap`.
- Each chunk keeps `arxiv_id` and `page`.
- Remove chunks that are shorter than 100 characters (they are usually page numbers or headers).

**Test:** Chunk `2005.11401`. Print the number of chunks and 2 examples.
**Done when:** Each chunk has an id and a page. The overlap is visible between chunk 1 and chunk 2.

### [ ] T9. Add `embed()` to `llm.py` (30 min)
**Design:** `embed(texts: list[str]) -> list[list[float]]`
- Use `client.embeddings.create(model=EMBED_MODEL, input=texts)`.
- `EMBED_MODEL` comes from `.env` (`bge-m3`).
- Send texts in **batches** of 32, not one by one. (One request per text is very slow.)

**Test:** `embed(["RAG", "retrieval augmented generation", "pizza"])`. Compute the cosine similarity of the pairs with numpy.
**Done when:** "RAG" is nearer to "retrieval augmented generation" than to "pizza". **Write the 3 numbers in NOTES.**

### [ ] T10. Make the table (30 min)
**Design:** `db.py`
- `get_conn()` uses `DATABASE_URL` and registers the pgvector type.
- `create_schema()` makes the extension and the `chunks` table: `id`, `arxiv_id`, `title`, `page`, `chunk_index`, `content`, `embedding VECTOR(1024)`.
- Add an HNSW index: `USING hnsw (embedding vector_cosine_ops)`.

**Test:** Run `create_schema()` two times. The second run does not fail (use `IF NOT EXISTS`).

### [ ] T11. Index all papers (60 min)
**Design:** `ingest.py` main:
- For each PDF: parse → chunk → embed (batches) → insert.
- **Idempotent:** before you insert a paper, delete its old chunks. Then you can run ingest again safely.
- Print progress: `[12/40] 2005.11401: 87 chunks`.

**Test:**
```bash
docker compose exec db psql -U paperpilot -c "SELECT count(DISTINCT arxiv_id), count(*) FROM chunks;"
```
**Done when:** ~40 papers and a few thousand chunks. Run ingest again: the count stays the same.

---

## Phase D: Answer

### [ ] T12. Vector search (30 min)
**Design:** `retrieve.py` → `vector_search(question, k=5) -> list[dict]`. Embed the question. Use `ORDER BY embedding <=> %s LIMIT k`. Return `arxiv_id`, `page`, `content`, and the score (`1 - distance`).
**Test:** `vector_search("What is lost in the middle?")`
**Done when:** The top results come from `2307.03172`.

### [ ] T13. Answer with citations (60 min)
**Design:** `rag.py` → `answer(question, k=5) -> dict` with `answer` and `sources`.
- Format the chunks in the prompt like this: `[2307.03172 p.4] <chunk text>`
- The system prompt has the 3 rules from Lesson A8: only the chunks, cite as `[id p.N]`, say "I don't know" when the answer is not there.

**Test:** 3 questions:
1. `What problem does the "Lost in the Middle" paper find?` → answer with citations.
2. `How does Self-RAG decide when to retrieve?` → answer with citations.
3. `What is the capital of France?` → "I don't know" (it is not in the papers).

### [ ] T14. CLI (15 min)
**Design:** `ask.py "question"` prints the answer, then the sources (id, page, score).
**Done when:** `uv run ask.py "What is HyDE?"` works.

---

## Phase E: Evals

### [ ] T15. Make the golden set (3–4 hours) ⭐ the most important task of Stage 2
**Design:** `evals/golden.jsonl`, one JSON object per line:
```json
{"id": "q01", "question": "...", "lang": "en", "arxiv_id": "2307.03172", "pages": [4], "reference_answer": "...", "answerable": true}
```
**How (best practice: AI draft + human check):**
1. Write a small script: pick 40 random chunks. For each chunk, ask the LLM to write one question that the chunk answers.
2. **You check each draft.** Delete bad questions. Fix unclear questions. Open the PDF and confirm the page.
3. Keep **25 English** questions. Mix easy and hard. Include some questions with exact terms (names, acronyms).
4. Add **3 unanswerable** questions (`"answerable": false`). The correct answer is "I don't know".
5. The 5 Arabic questions come later, in T23.

**Write guidelines first** (you did this as an annotation supervisor): what makes a good question? Write 5 rules in `evals/GUIDELINES.md`.
**Done when:** 28 checked questions.

### [ ] T16. Retrieval metrics (60 min)
**Design:** `evals/run_eval.py`
- For each answerable question: run the retrieval, top 5.
- **Hit:** a result has the correct `arxiv_id` AND its `page` is in `pages`.
- Compute **hit rate@5** and **MRR**.
- Print the failed questions (they show you what to fix).

**Test:** `uv run python -m evals.run_eval`

### [ ] T17. Answer metrics: LLM-as-judge (90 min)
**Design:** In `run_eval.py`, for each question, call `answer()`, then ask a judge LLM for JSON:
```json
{"faithful": true, "correct": true, "reason": "..."}
```
- **faithful:** each fact in the answer is in the retrieved chunks.
- **correct:** the answer agrees with `reference_answer`. For unanswerable questions, correct = it said "I don't know".

Print % faithful and % correct.
**Interview point:** the judge is the same small model. That is a bias. Write in NOTES why, and what you would do in production.

### [ ] T18. Record the baseline (20 min)
**Design:** `evals/RESULTS.md`:

| # | Experiment | Hit@5 | MRR | Faithful | Correct | Notes |
|---|---|---|---|---|---|---|
| 0 | Baseline: vector, size 1000, overlap 200, k=5 | | | | | |

**Done when:** The baseline row has real numbers. Commit. 🎯

---

## Phase F: Improve (one change at a time, measure each)

### [ ] T19. Chunk size experiment (60 min)
Re-index with size 500 and with size 2000. Run the eval for each. Add 2 rows to RESULTS.md. Keep the best.

### [ ] T20. Hybrid search (90 min)
**Design:**
- Add a column `content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED` with a GIN index.
- `keyword_search(question, k=20)` with `websearch_to_tsquery` and `ts_rank_cd`.
- `hybrid_search(question, k=5)`: vector top 20 + keyword top 20 → **RRF** (`1 / (60 + rank)`) → top 5.

Measure. Add a row. Look at the questions with exact terms: did they improve?

### [ ] T21. Reranking (90 min)
**Design:** `rerank(question, chunks, top_n=5)` with `sentence-transformers` `CrossEncoder("BAAI/bge-reranker-v2-m3")` (multilingual, about 2 GB download, runs on your Mac).
Pipeline: hybrid top 30 → rerank → top 5.
Measure quality **and time** for each question. Add a row. Is the quality gain worth the time?

### [ ] T22. Query rewriting (60 min)
**Design:** Before retrieval, ask the LLM to rewrite the question as a better search query (for example, expand acronyms). Search with the rewritten query.
Measure. Add a row. Keep it only if the numbers are better.

---

## Phase G: Arabic

### [ ] T23. Cross-lingual test (60 min)
Add **5 Arabic questions** to the golden set (`"lang": "ar"`) about English papers.
Run the eval. Compare the Arabic hit rate with the English hit rate.
Make sure that the answer comes back in Arabic, with the citations.
**This is your differentiator. Write the result clearly in RESULTS.md.**

---

## Phase H: Connect to the agent

### [ ] T24. New agent tool: `search_library` (45 min)
**Design:** In `tools.py`, add `search_library(query)`. It calls your best retrieval and returns the top 5 chunks with ids and pages. Add its schema.
Now the agent can choose: `search_arxiv` (new papers on the internet) or `search_library` (deep content of the indexed papers).
**Test:** In `main.py`, ask: `According to the Self-RAG paper, what are reflection tokens?`
**Done when:** The trace shows `search_library`, and the answer has page citations.

---

## Phase I: LangChain

### [ ] T25. Rebuild with LangChain (2–3 hours)
**Design:** `lc/` folder:
- `PyMuPDFLoader` → `RecursiveCharacterTextSplitter` → `OllamaEmbeddings` → `PGVector` store
- A retriever + a prompt + `ChatOllama` in an **LCEL** chain: `retriever | format | prompt | llm | parser`
- Use a **different table/collection** name, so the two versions do not mix.

**Test:** Run your golden set against the LangChain version.

### [ ] T26. Compare (30 min)
Add a section to RESULTS.md: numbers, lines of code, what was easier, what was hidden, what was harder to debug. **This is an interview answer: "When would you use LangChain, and when not?"**

---

## Phase J: Ship

### [ ] T27. Product README (60 min)
Move the stage lessons to `docs/`. Write a root `README.md` for **recruiters**: what PaperPilot does, an architecture diagram, how to run it, and **the results table**.

### [ ] T28. LinkedIn post (30 min)
One post: the problem, one diagram, one number (for example "hit rate@5 from 62% → 84%"), and the GitHub link. The job track starts this week.

---

## Time estimate

| Phase | Time |
|---|---|
| A. Setup | 1 h |
| B. Corpus | 1.5 h |
| C. Indexing | 3.5 h |
| D. Answer | 2 h |
| E. Evals | 7 h |
| F. Improve | 5 h |
| G. Arabic | 1 h |
| H. Agent | 1 h |
| I. LangChain | 3.5 h |
| J. Ship | 1.5 h |
| **Total** | **about 27 hours** |

You have about 60 hours for weeks 2–4. The extra time is for debugging, reading the papers, and the questions you will have. Use it.
