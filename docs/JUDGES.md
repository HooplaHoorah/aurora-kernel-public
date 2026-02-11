# Aurora — Quick Judge Path

> **Time required:** ~60 seconds (live demo) or ~10 minutes (local run).

## Live Demo (fastest)

| Resource | URL |
|----------|-----|
| **Aurora Studio (UI)** | https://d11zsiqq3s9tq.cloudfront.net |
| **Aurora Kernel API** | https://x2vcyviirf.us-east-1.awsapprunner.com |
| **API Docs (Swagger)** | https://x2vcyviirf.us-east-1.awsapprunner.com/docs |
| **Health Check** | https://x2vcyviirf.us-east-1.awsapprunner.com/health |

### 3-minute path

1. **Open Aurora Studio** → https://d11zsiqq3s9tq.cloudfront.net
2. **Pick a Stakeholder preset** — e.g., *Compliance / GRC* or *CISO / Security*
3. **Pick a Hot-seat scenario** — e.g., *HS-001: Regulator Inquiry*
4. **Set Mode = Agent Builder** (if available), then click **Generate Evidence Pack**
5. **Review the output** — you should see:
   - Retrieval grounding (citations, doc IDs, snippets)
   - Controls → evidence → gaps → remediation plan
   - Deterministic fallback if agent mode is unavailable
6. **Export** — click **Markdown** or **JSON** to download the Evidence Pack

### What to look for

| Criterion | Where to find it |
|-----------|-----------------|
| Elastic Agent Builder usage | Mode selector in the UI; `/agent/status` endpoint |
| Elasticsearch-backed retrieval | Citations and doc IDs in the Evidence Pack output |
| Practical, structured output | Controls, evidence list, gaps, and remediation plan |
| Graceful degradation | Switch to Deterministic mode; output should still work |
| Export capability | Download buttons (Markdown / JSON) |

## Local Run (if live demo is unavailable)

See the main [README.md](../README.md) for full local setup instructions.

Quick summary:
```bash
git clone https://github.com/HooplaHoorah/aurora-kernel-public
cd aurora-kernel-public
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in Elastic credentials
export PYTHONPATH="$PWD/src"
python -m uvicorn aurora_kernel.api:app --port 8000 --reload
# Visit http://localhost:8000/docs
```

## Companion repos

- **Corpus:** [aurora-hackathon-corpus](https://github.com/HooplaHoorah/aurora-hackathon-corpus) — synthetic demo dataset (CC BY 4.0)
