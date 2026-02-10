# Aurora Kernel (aurora-kernel)

> **Note:** Architecture & specs live in `aurora-spec` (private).


Portable execution kernel for Aurora:
- SimOps tick runner (**Build / Prove / Attack / Patch / Replay / Export**)
- Evidence receipts (hashing + chain pointers)
- EvidencePack export builder (zip output)
- GitHub Actions workflow that publishes an `EvidencePack.zip` artifact
- **Hackathon:** Elasticsearch-backed corpus search + Evidence Pack API

## Quick start (local)

### 1. Setup Python environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment
Copy `.env.example` to `.env` and fill in your Elasticsearch credentials:
```powershell
copy .env.example .env
# Edit .env with your actual credentials
```

### 3. Start the API server
```powershell
$env:PYTHONPATH = "$PWD\src"
python -m uvicorn aurora_kernel.api:app --reload --port 8000
```

Visit http://localhost:8000/docs for the interactive API documentation.

## 🔒 Secrets Hygiene

- **Secrets are stored locally** in `.env` (gitignored). **Never commit credentials.**
- For public demos, use a tunnel (ngrok/Cloudflare) and **rotate Elastic credentials after the demo.**
- Local dev may use Basic Auth; public demos should prefer Elastic API keys.
- See `.env.example` for required environment variables.

## 🎯 Hackathon Demo: Evidence Pack Generation

The Aurora Kernel can generate audit-ready Evidence Packs by searching the corpus and mapping controls.

### Demo 1: Compliance (EU AI Act Governance)
```powershell
curl.exe -X POST "http://localhost:8000/evidence_pack" `
  -H "Content-Type: application/json" `
  -d '{
    "question": "EU AI Act governance obligations: documentation, risk management, human oversight, logging, transparency. Generate an audit-ready evidence pack with citations.",
    "preset_id": "compliance_grc",
    "scenario_id": "HS-EUAI-01"
  }' `
  -o "evidence_pack_compliance.json"
```

**Output:** Audit-ready evidence with mapped controls, citations, gaps, and fix plan.

### Demo 2: Security & Risk (Incident Response)
```powershell
curl.exe -X POST "http://localhost:8000/evidence_pack" `
  -H "Content-Type: application/json" `
  -d '{
    "question": "Incident response for AI system: monitoring, detection, escalation, containment, post-incident review. Generate an evidence pack and action list with citations.",
    "preset_id": "security_risk",
    "scenario_id": "HS-IR-01"
  }' `
  -o "evidence_pack_security.json"
```

**Output:** Incident response evidence + monitoring gaps + action list with citations.

Demo outputs are saved to: `../aurora-hackathon-corpus/09_expected_outputs/demo_runs/`

## API Endpoints

- **GET** `/health` - Health check
- **GET** `/search?q=query` - Search corpus
- **POST** `/evidence_pack` - Generate evidence pack with citations
- **POST** `/ingest` - Ingest corpus (use CLI for reliability; endpoint WIP)

## CI

See `.github/workflows/aurora_tick.yml`.


---

Trademark and Copyright 2026. AIPEX INDUSTRIES. All Rights Reserved. Created by Richard A. Morgan.


---

Trademark and Copyright 2026. Hoopla Hoorah. All Rights Reserved.
