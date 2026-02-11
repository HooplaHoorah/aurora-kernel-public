**For evaluation only.**

# Aurora — Judges Readme (Elastic Agent Builder Hackathon)

**Project:** Aurora (Aurora Kernel + Aurora Studio)

**Public repo (kernel):** https://github.com/HooplaHoorah/aurora-kernel-public

**Corpus repo:** https://github.com/HooplaHoorah/aurora-hackathon-corpus

Aurora is a **compliance evidence copilot** that turns policies, controls, incidents, and “hot-seat” scenarios into an **Evidence Pack** you can inspect, export, and reuse.

This bundle is built to help judges validate the full loop quickly via **Live Demo** (preferred) or **Local Run**.

## Architecture

![Aurora Kernel architecture](docs/architecture.png)

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Quick judge path: [docs/JUDGES.md](docs/JUDGES.md)

---

## Live Demo (fastest)

- **Aurora Studio (UI):** https://d11zsiqq3s9tq.cloudfront.net
- **Aurora Kernel API:** https://x2vcyviirf.us-east-1.awsapprunner.com
- **API Docs (Swagger):** https://x2vcyviirf.us-east-1.awsapprunner.com/docs
- **Health Check:** https://x2vcyviirf.us-east-1.awsapprunner.com/health

### 60-second judge path

1. Open **Aurora Studio**.
2. Pick a **Stakeholder preset** (e.g., *Compliance / GRC* or *CISO / Security*).
3. Pick a **Hot-seat scenario**.
4. Set **Mode = Agent Builder** (if available), then click **Generate Evidence Pack**.
5. Export **Markdown** or **JSON**.

### What you should see

- **Grounding / retrieval evidence:** citations, doc IDs, and/or snippets tied to corpus hits.
- **Structured Evidence Pack:** mapped controls → evidence requests → gaps → remediation plan.
- **Graceful fallback:** if Agent Builder is unavailable, deterministic mode should still generate an Evidence Pack.

---

## What to look for (hackathon-aligned)

### Elastic Agent Builder usage
- “Agent Builder” mode routes the run through an agent created in **Elastic Agent Builder**.
- If agent mode is not configured, the UI should degrade gracefully.

### Elasticsearch-backed retrieval
- Outputs are grounded in **Elasticsearch** retrieval (search endpoint returns relevant hits).
- Evidence Pack includes traceability back to retrieved context.

### Practical output
- Evidence Pack is immediately useful: clear controls, evidence list, gaps, and next actions.
- Exports work.

---

## If live demo is unavailable: local run (5–10 minutes)

1) Clone the kernel repo
```bash
git clone https://github.com/HooplaHoorah/aurora-kernel-public
cd aurora-kernel-public
```

2) Create a Python venv and install deps (Python 3.10+)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3) Configure environment
- Copy `.env.example` → `.env`
- Fill in the Elastic credentials requested by the repo (Cloud ID or host + auth)

4) (Optional) Ingest the synthetic corpus
```bash
git clone https://github.com/HooplaHoorah/aurora-hackathon-corpus.git
# Run the ingest command described in the repo README
```

5) Run the API
```bash
export PYTHONPATH="$PWD/src"
python -m uvicorn aurora_kernel.api:app --port 8000 --reload
```

6) Validate
- Open `http://localhost:8000/docs`
- Run `/search`
- POST `/evidence_pack`

---

## Data & safety notes

- Demo corpus is **synthetic / sanitized** and intended for evaluation.
- No user uploads are required for the judge path.
- Secrets are kept out of source control (use `.env`, rotate keys after demos).

---

Thanks for reviewing Aurora.

---
---

# Aurora Kernel — Elastic Agent Builder Hackathon
(Detailed Technical README)

Portable execution kernel for Aurora:

- SimOps tick runner (**Build / Prove / Attack / Patch / Replay / Export**)
- Evidence receipts (hashing + chain pointers)
- Evidence Pack export builder (zip output)
- **Hackathon slice:** Elasticsearch-backed corpus search + Evidence Pack API

## 👩‍⚖️ Judge Quickstart (Live Demo)

- **Aurora Studio (UI):** https://d11zsiqq3s9tq.cloudfront.net
- **Aurora Kernel API:** https://x2vcyviirf.us-east-1.awsapprunner.com
- **API Docs (Swagger):** https://x2vcyviirf.us-east-1.awsapprunner.com/docs
- **Health Check:** https://x2vcyviirf.us-east-1.awsapprunner.com/health

### 60-second path
1. Open the Studio URL.
2. Select a stakeholder preset (e.g., Compliance / GRC).
3. Select a hot-seat scenario.
4. Set **Mode = Agent Builder** (if available) and click **Generate Evidence Pack**.
5. Export Markdown or JSON.

**What to look for**
- Retrieval grounding (citations/doc IDs/snippets)
- Controls → evidence → gaps → remediation plan
- Deterministic fallback if agent mode is unavailable

---

## Quick start (Local)

### 1) Setup Python environment (Python 3.10+)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment
Copy `.env.example` to `.env` and fill in your Elasticsearch credentials.

```bash
cp .env.example .env
# Edit .env with your Elastic Cloud ID or host + auth variables as required
```

### 3) (Optional) Ingest the provided synthetic corpus
The demo corpus lives in the companion repo:
https://github.com/HooplaHoorah/aurora-hackathon-corpus

Follow the ingest instructions in this repository to load it into Elasticsearch.

### 4) Start the API server
```bash
export PYTHONPATH="$PWD/src"
python -m uvicorn aurora_kernel.api:app --reload --port 8000
```

Visit http://localhost:8000/docs for interactive API docs.

---

## API endpoints

- **GET** `/health`
- **GET** `/search?q=query&size=N`
- **POST** `/evidence_pack`

(Deployments that enable Agent Builder may also expose `/agent/status`.)

---

## Architecture

- **Aurora Studio:** static UI
- **Aurora Kernel:** FastAPI backend
- **Elasticsearch / Elastic Cloud:** retrieval index

---

## Secrets hygiene

- Never commit credentials.
- Store secrets in `.env` (gitignored) or the deployment platform’s secret manager.
- Rotate keys after public demos.

---

## License

MIT License (see `LICENSE`).

