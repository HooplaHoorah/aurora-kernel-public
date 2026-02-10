from __future__ import annotations

import os
import requests
from pathlib import Path
from typing import Any, Dict, Optional, List
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fastapi
import uuid

from aurora_kernel.corpus_loader import load_corpus
from aurora_kernel.elastic_store import make_es_client, index_corpus, search as es_search
# from fastapi import HTTPException  <-- removed redundant line

import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aurora_kernel")

load_dotenv()

app = FastAPI(title="Aurora Kernel Hackathon API", version="0.1.0")

# Configure CORS to allow Aurora Studio frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://aurora-studio-20260201.s3-website-us-east-1.amazonaws.com",
        "https://d11zsiqq3s9tq.cloudfront.net",
        "*", 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: fastapi.Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Method={request.method} Path={request.url.path} Duration={process_time:.4f}s")
    return response

# --- Config ---
def _client():
    cloud_id = os.getenv("ELASTIC_CLOUD_ID")
    es_url = os.getenv("ES_URL", "http://localhost:9200")
    api_key = os.getenv("ES_API_KEY")
    username = os.getenv("ES_USERNAME")
    password = os.getenv("ES_PASSWORD")
    return make_es_client(cloud_id=cloud_id, es_url=es_url, api_key=api_key, username=username, password=password)

def _index_name() -> str:
    return os.getenv("AURORA_INDEX", "aurora_kb_v1")

def _corpus_path() -> Path:
    return Path(os.getenv("AURORA_CORPUS_PATH", "../aurora-hackathon-corpus")).resolve()

# --- Helpers for Agent Builder ---

# --- Helpers for Agent Builder ---
class AgentBuilderConfig(BaseModel):
    kibana_url: str
    api_key: str
    connector_id: str
    agent_id: str
    space_id: Optional[str] = None

def get_agent_builder_config() -> Optional[AgentBuilderConfig]:
    kibana_url = os.getenv("KIBANA_URL")
    api_key = os.getenv("KIBANA_API_KEY")
    connector_id = os.getenv("AGENT_BUILDER_CONNECTOR_ID")
    agent_id = os.getenv("AURORA_AGENT_ID") or os.getenv("AGENT_BUILDER_AGENT_ID")
    space_id = os.getenv("KIBANA_SPACE_ID")
    
    has_auth = api_key or (os.getenv("ES_USERNAME") and os.getenv("ES_PASSWORD"))

    if not (kibana_url and connector_id and agent_id and has_auth):
        return None
        
    return AgentBuilderConfig(
        kibana_url=kibana_url.rstrip("/"),
        api_key=(api_key or "").strip(),
        connector_id=connector_id.strip(),
        agent_id=agent_id.strip(),
        space_id=space_id.strip() if space_id else None,
    )

def kibana_api_base(cfg: AgentBuilderConfig) -> str:
    if cfg.space_id:
        return f"{cfg.kibana_url}/s/{cfg.space_id}"
    return cfg.kibana_url

def _find_key_recursive(obj: Any, key_names: List[str]) -> Any:
    """Search recursively for a key in a nested dict/list structure."""
    if isinstance(obj, dict):
        for k in key_names:
            if k in obj: return obj[k]
        for v in obj.values():
            res = _find_key_recursive(v, key_names)
            if res: return res
    elif isinstance(obj, list):
        for v in obj:
            res = _find_key_recursive(v, key_names)
            if res: return res
    return None


async def _call_agent_builder_converse(
    cfg: AgentBuilderConfig,
    user_input: str,
    attachments: List[Dict],
    conversation_id: Optional[str] = None,
) -> Dict:
    """Send a request to the Elastic Agent Builder and return structured output."""
    
    # Build context string from attachments
    context_sections = []
    for idx, att in enumerate(attachments):
        # Each attachment has title, doc_id and content
        context_sections.append(
            f"Doc {idx + 1} – {att.get('title', 'Untitled')} ({att.get('doc_id', 'unknown')}): {att.get('content', '')}"
        )
    context_str = "\n\n=== RETRIEVED CONTEXT ===\n" + "\n\n".join(context_sections) if context_sections else ""

    # Combine user input and context
    final_input = user_input + context_str

    # Construct the base URL from config (supporting spaces)
    base_url = kibana_api_base(cfg)
    url = f"{base_url}/api/agent_builder/converse"
    
    # Authorization headers
    headers = {
        "Content-Type": "application/json",
        "kbn-xsrf": "kbn",
    }
    auth = None
    if cfg.api_key:
        headers["Authorization"] = f"ApiKey {cfg.api_key}"
    else:
        # Fallback to Basic Auth
        username = os.getenv("ES_USERNAME")
        password = os.getenv("ES_PASSWORD")
        if username and password:
            auth = (username, password)

    # Payload: STRICTLY agent_id and input. 
    # Elastic API may reject extra fields like 'attachments' or 'context'.
    payload = {
        "agent_id": cfg.agent_id,
        "input": final_input,
    }
    # Note: conversation_id is supported by the API, but if it causes issues we might drop it.
    # We will include it if provided.
    if conversation_id:
        payload["conversation_id"] = conversation_id

    print(f"DEBUG: Sending to Agent Builder: {payload.keys()}")

    full_response_text = ""
    last_conversation_id = conversation_id

    async with httpx.AsyncClient(timeout=60.0) as client:
        request_kwargs = {"headers": headers, "json": payload}
        if auth:
            request_kwargs["auth"] = auth

        async with client.stream("POST", url, **request_kwargs) as response:
            if response.status_code != 200:
                body = await response.aread()
                logger.error(f"Agent Builder error {response.status_code}: {body.decode()}")
                raise Exception(f"Agent Builder error {response.status_code}: {body.decode()}")

            content_type = response.headers.get("content-type", "")
            is_sse = "text/event-stream" in content_type
            
            if not is_sse and "application/json" in content_type:
                # JSON Mode (non-streaming or buffered by proxy)
                body_bytes = await response.aread()
                try:
                    import json
                    event = json.loads(body_bytes)
                    
                    chunk = _find_key_recursive(event, ["text_chunk", "text", "content", "message"])
                    new_conv_id = _find_key_recursive(event, ["conversation_id", "conversationId"])

                    if chunk and isinstance(chunk, str):
                        full_response_text += chunk
                    if new_conv_id:
                        last_conversation_id = new_conv_id
                except Exception as e:
                    logger.error(f"Failed to parse JSON response body: {e}")
            else:
                # SSE Mode (streaming)
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    
                    if line.startswith("event:"):
                        continue

                    # SSE lines start with "data: "
                    clean_line = line
                    if line.startswith("data:"):
                        clean_line = line[5:].strip()
                    
                    if not clean_line:
                        continue

                    try:
                        import json
                        event = json.loads(clean_line)
                        
                        chunk = _find_key_recursive(event, ["text_chunk", "text", "content", "message"])
                        new_conv_id = _find_key_recursive(event, ["conversation_id", "conversationId"])

                        if chunk and isinstance(chunk, str):
                            full_response_text += chunk
                        
                        if new_conv_id:
                            last_conversation_id = new_conv_id

                    except Exception as e:
                        logger.debug(f"Failed to parse stream line as JSON: {e}")
    logger.info(f"Stream complete. Full text length: {len(full_response_text)}")
    
    # Parse the LLM JSON output
    ai_output = _parse_llm_json(full_response_text)
    
    # Return structured dict compatible with our evidence pack
    return {
        "text": full_response_text,
        "conversationId": last_conversation_id,
        "summary": ai_output.get("summary", ""),
        "findings": ai_output.get("claims", []) or ai_output.get("findings", []),
        "recommendations": ai_output.get("recommendations", []),
        "citations": ai_output.get("citations", []),
        # Pass through any other parsed fields
        **ai_output
    }

# --- Storage for downloads ---
PACK_STORAGE = {}

# --- Endpoints ---

@app.get("/api/evidence-pack/{pack_id}.json")
def download_json(pack_id: str):
    if pack_id not in PACK_STORAGE:
         raise HTTPException(status_code=404, detail="Pack not found")
    return PACK_STORAGE[pack_id]

@app.get("/api/evidence-pack/{pack_id}.md")
def download_md(pack_id: str):
    if pack_id not in PACK_STORAGE:
         raise HTTPException(status_code=404, detail="Pack not found")
    
    pack = PACK_STORAGE[pack_id]
    # Simple JSON to MD conversion
    md = f"# Evidence Pack: {pack.get('claim', 'Unknown')}\n\n"
    md += f"**Scenario:** {pack.get('scenario_id')}\n"
    md += f"**Summary:** {pack.get('summary')}\n\n"
    
    md += "## Findings\n"
    for f in pack.get("findings", []):
        md += f"- {f}\n"
    
    md += "\n## Evidence\n"
    for e in pack.get("evidence", []):
         md += f"### {e.get('doc_id')}\n"
         md += f"> {e.get('chunk')}\n\n"
         
    return fastapi.responses.PlainTextResponse(md)

@app.get("/agent/status")
def agent_status():
    cfg = get_agent_builder_config()
    return {"configured": bool(cfg)}

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "version": "v1.3-debug", "index": _index_name(), "corpus_path": str(_corpus_path())}


class IngestRequest(BaseModel):
    corpus_path: Optional[str] = None
    index: Optional[str] = None

@app.post("/ingest")
def ingest(req: IngestRequest) -> Dict[str, Any]:
    corpus = Path(req.corpus_path).resolve() if req.corpus_path else _corpus_path()
    index = req.index or _index_name()

    docs = load_corpus(corpus)
    c = _client()
    resp = index_corpus(c, index=index, docs=docs)
    return {"corpus": str(corpus), "index": index, **resp}

@app.get("/search")
def search(
    q: str = Query(..., description="Search query"),
    index: Optional[str] = Query(None, description="Override index name"),
    doc_type: Optional[str] = None,
    stakeholder: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    size: int = 5,
) -> Dict[str, Any]:
    idx = index or _index_name()
    # P1: Filter implicitly for actual sources to prevent citing expected outputs
    filters = {"doc_type": doc_type or "source", "stakeholder": stakeholder, "jurisdiction": jurisdiction}
    c = _client()
    return es_search(c, index=idx, q=q, filters=filters, size=size)

class EvidencePackRequest(BaseModel):
    question: str
    preset_id: Optional[str] = None
    scenario_id: Optional[str] = None
    index: Optional[str] = None


def _build_deterministic_pack(question: str, scenario_id: Optional[str], preset_id: Optional[str], index: str = None) -> Dict[str, Any]:
    idx = index or _index_name()
    c = _client()
    idx = index or _index_name()
    c = _client()
    # P1: Enforce doc_type='source'
    results = es_search(c, index=idx, q=question, filters={"doc_type": "source"}, size=8)

    controls = set()
    citations = []
    for h in results["hits"]:
        for cid in (h.get("control_ids") or []):
            controls.add(cid)
        citations.append({
            "doc_id": h.get("doc_id"),
            "doc_type": h.get("doc_type"),
            "source_path": h.get("source_path"),
            "chunk": h.get("content") or h.get("chunk_id"),
            "content": h.get("content"),
            "score": h.get("score")
        })

    return {
        "schema_version": "0.1.0",
        "scenario_id": scenario_id,
        "preset_id": preset_id,
        "summary": "This is a deterministic placeholder summary. Use Agent Mode for AI summary.",
        "findings": ["Finding 1: Evidence found.", "Finding 2: Review controls."],
        "claim": question,
        "controls_mapped": sorted(list(controls)),
        "evidence": citations,
        "gaps": ["No Agent Analysis performed."],
        "fix_plan": ["Enable Agent Mode to generate fix plan."],
        "raw_search": results,
    }

@app.get("/evidence_pack")
def evidence_pack_get(
    question: str = Query(..., description="The compliance question"),
    preset_id: Optional[str] = Query(None),
    scenario_id: Optional[str] = Query(None),
    index: Optional[str] = Query(None),
):
    return _build_deterministic_pack(question, scenario_id, preset_id, index)

class EvidencePackCompat(BaseModel):
    # preferred (query-style)
    question: str | None = None
    preset_id: str | None = None
    scenario_id: str | None = None
    index: str | None = None
    # legacy (studio-style)
    role: str | None = None
    scenario: str | None = None
    extra: str | None = None

@app.post("/evidence_pack")
def evidence_pack_post(body: EvidencePackCompat):
    q = body.question or body.extra
    preset = body.preset_id or body.role
    scenario = body.scenario_id or body.scenario
    idx = body.index
    
    if not (q and preset and scenario):
        raise HTTPException(
            status_code=422,
            detail="Missing params. Provide (question,preset_id,scenario_id) or legacy (role,scenario,extra).",
        )
    return _build_deterministic_pack(q, scenario, preset, idx)

class AgentEvidencePackRequest(BaseModel):
    role: str
    scenario: str
    extra: str | None = None
    conversation_id: str | None = None
    top_k: int | None = 6

def _parse_llm_json(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM output, handling Markdown fences."""
    import re
    import json
    
    clean = text.strip()
    
    # Try to find JSON inside code fences
    # Look for ```json { ... } ``` or just ``` { ... } ```
    # Using regex to find the content between fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        clean = match.group(1)
    else:
        # Fallback: find first { and last }
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1:
            clean = clean[start:end+1]

    try:
        return json.loads(clean)
    except Exception:
        return {}

@app.post("/agent/evidence_pack")
async def agent_evidence_pack(req: AgentEvidencePackRequest):
    """Generate an Evidence Pack using Elastic Agent Builder."""
    cfg = get_agent_builder_config()
    if not cfg:
        raise HTTPException(
            detail="Agent Builder not configured. Set KIBANA_URL, KIBANA_API_KEY, AGENT_BUILDER_CONNECTOR_ID, AGENT_BUILDER_AGENT_ID.",
        )

    # --- DEMO MODE CHECK ---
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        logger.info(f"🎭 DEMO MODE ACTIVE: Returning pre-recorded response for {req.role}")
        
        # Simulate network delay for realism
        import asyncio
        await asyncio.sleep(2.5)
        
        pack_id = str(uuid.uuid4())
        conv_id = req.conversation_id or str(uuid.uuid4())
        
        # High quality pre-recorded response
        ai_output = {
            "summary": "Based on the HS-001 compliance review for the v0.3 release, three critical gaps were identified in the internal LLM assistant implementation: (1) inadequate access logging for prompt injection monitoring, (2) missing hallucination detection controls, and (3) incomplete data leakage prevention. These gaps pose moderate to high risk for regulatory violations under AI governance frameworks including SOC 2 and ISO 27001. findings indicate that while baseline security controls exist, LLM-specific risks require enhanced monitoring before production deployment.",
            "findings": [
                "Access logging does not capture sufficient detail for LLM-specific attack vectors (prompt injection attempts).",
                "No automated hallucination detection or confidence scoring in customer-facing LLM responses.",
                "Training data provenance tracking incomplete - cannot verify GDPR compliance for all datasets.",
                "Input sanitization rules do not adequately cover adversarial prompt patterns identified in recent research.",
                "Role-based access controls not enforced at the model invocation layer, allowing over-privileged access."
            ],
            "recommendations": [
                "Implement semantic analysis logging to detect prompt injection attempts and jailbreaking.",
                "Integrate confidence scoring and source attribution validation for all LLM outputs.",
                "Implement end-to-end provenance tracking for all training datasets.",
                "Expand input sanitization to include adversarial prompt patterns."
            ],
            "citations": [
                {"doc_id": "controls_v0", "title": "v0.3 Security Controls", "relevance": "Primary source for access control gaps"},
                {"doc_id": "risk_llm_2024", "title": "LLM Risk Assessment 2024", "relevance": "Identified hallucination risks"},
                {"doc_id": "owasp_llm", "title": "OWASP Top 10 for LLM", "relevance": "Standard for prompt injection defense"},
                {"doc_id": "gdpr_ai", "title": "GDPR AI Guidelines", "relevance": "Data provenance requirements"}
            ]
        }
        
        # Build the full pack structure
        deterministic = _build_deterministic_pack(query_text, req.scenario, req.role)
        final_pack = deterministic.copy()
        final_pack["mode"] = "agent_builder_demo"
        final_pack["schema_version"] = "0.1.0"
        final_pack.update(ai_output)
        
        PACK_STORAGE[pack_id] = final_pack
        
        return {
            "ok": True,
            "mode": "agent_builder_demo",
            "pack_id": pack_id,
            "conversationId": conv_id,
            "agent": ai_output,
            "deterministic": deterministic,
            "retrieval": {"query": query_text, "hits": []},
            **final_pack
        }
    # -----------------------
    query_text = f"{req.role}: {req.scenario}\n{req.extra or ''}".strip()
    
    # Reuse es_search logic
    c = _client()
    idx = _index_name()
    # P1: Filter doc_type='source'
    results = es_search(c, index=idx, q=query_text, filters={"doc_type": "source"}, size=req.top_k or 6)
    hits = results.get("hits", [])

    # Convert into Agent Builder context blocks
    context_items = []
    for h in hits:
        # es_search implementation:
        # returns {"hits": [ { ...src fields..., "score": ... } ]}
        
        # We need to format it nicely
        title = h.get("title", "Untitled")
        content = h.get("content", "")
        doc_id = h.get("doc_id", "unknown")
        
        context_items.append(
            {
                "type": "text",
                "text": f"DOC {doc_id} | score={h.get('score')}\nTitle: {title}\nContent: {content}",
            }
        )

    # 2) Agent Builder prompt
    agent_prompt = (
        "You are Aurora, an AI compliance assistant.\n"
        "Use ONLY the provided context docs to support claims.\n"
        "Return a JSON object with keys: summary, claims (array of strings), recommendations (array of strings), citations (array of objects with doc_id and reason).\n"
        "Each item in citations must reference the DOC ids used in the context.\n\n"
        f"ROLE: {req.role}\nSCENARIO: {req.scenario}\nEXTRA: {req.extra or ''}\n"
    )

    try:
        # Prepare context items as attachments dict for the new helper
        attachments = []
        for h in hits:
            attachments.append({
                "title": h.get("title", "Untitled"),
                "doc_id": h.get("doc_id", "unknown"),
                "content": h.get("content", "") or h.get("chunk_id", ""),
                "score": h.get("score")
            })

        agent_result = await _call_agent_builder_converse(
            cfg=cfg,
            user_input=agent_prompt,
            attachments=attachments,
            conversation_id=req.conversation_id,
        )
        
        # Determine if we got a valid fallback or success
        if agent_result.get("mode") == "fallback":
             raise Exception(agent_result.get("error"))

    except Exception as e:
         # Fallback on error (P0 requirement)
         print(f"ERROR: Agent Builder failed: {e}")
         deterministic = _build_deterministic_pack(query_text, req.scenario, req.role)
         pack_id = str(uuid.uuid4())
         PACK_STORAGE[pack_id] = deterministic
         return {
             "ok": True,
             "mode": "fallback",
             "pack_id": pack_id,
             "note": f"Agent unavailable: {str(e)}",
             "agent": None,
             "deterministic": deterministic,
             "retrieval": {"query": query_text, "hits": hits},
             # Spread deterministic content so it looks like a valid pack
             **deterministic
         }

    # 3) Merge Agent Results
    deterministic = _build_deterministic_pack(query_text, req.scenario, req.role)
    
    final_pack = deterministic.copy()
    final_pack["mode"] = "agent_builder"
    final_pack["agent_raw"] = agent_result
    final_pack["schema_version"] = "0.1.0"
    
    # Update fields from agent result
    if agent_result.get("summary"):
        final_pack["summary"] = agent_result["summary"]
    if agent_result.get("findings"):
        final_pack["findings"] = agent_result["findings"]
    if agent_result.get("citations"):
        # Map citations to evidence format if possible, or append
        final_pack["citations_ai"] = agent_result["citations"]
        
    pack_id = str(uuid.uuid4())
    PACK_STORAGE[pack_id] = final_pack

    return {
        "ok": True,
        "mode": "agent_builder",
        "pack_id": pack_id,
        "conversationId": agent_result.get("conversationId"),
        "agent": agent_result,
        "deterministic": deterministic,
        "retrieval": {"query": query_text, "hits": hits},
        **final_pack
    }

@app.post("/agent/warmup")
async def agent_warmup():
    """Warm up the Agent Builder connection."""
    try:
        cfg = get_agent_builder_config()
        if not cfg:
            return {"status": "skipped", "reason": "Agent not configured"}
            
        # --- DEMO MODE CHECK ---
        if os.getenv("DEMO_MODE", "false").lower() == "true":
            logger.info("🎭 DEMO MODE WARMUP: Pretending to warm up...")
            import asyncio
            await asyncio.sleep(0.5)
            return {"status": "warmed", "message": "Agent Builder is active (DEMO MODE)"}
        # -----------------------

        # Fire a quick, cheap request to wake up the model/connector
        logger.info("Warming up Agent Builder...")
        await _call_agent_builder_converse(
            cfg=cfg,
            user_input="System warm-up check. Respond with 'OK'.",
            attachments=[],
            conversation_id=None
        )
        return {"status": "warmed", "message": "Agent Builder is active"}
    except Exception as e:
        logger.warning(f"Warm-up exception (non-fatal): {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/agent/evidence_pack")
async def agent_evidence_pack_get(
    preset_id: str = Query("HS-001", description="Preset ID (e.g., HS-001)"),
    question: str = Query("", description="Compliance question / prompt"),
    top_k: int = Query(6, ge=1, le=25, description="Number of retrieved documents"),
):
    """Simple GET shim for smoke tests.

    The Aurora Studio frontend uses POST. This endpoint exists only to make it easy
    to sanity-check a deployment in a browser/curl without constructing a JSON body.
    """

    req = AgentEvidencePackRequest(role=preset_id, scenario=preset_id, extra=question, top_k=top_k)
    return await agent_evidence_pack(req)
