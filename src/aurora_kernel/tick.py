from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

@dataclass
class EvidenceReceipt:
    schema_version: str
    evidence_id: str
    captured_at: str
    sha256: str
    prev_sha256: str
    source: Dict[str, Any]

def make_receipt(evidence_id: str, payload: Dict[str, Any], prev_sha: str = "") -> EvidenceReceipt:
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return EvidenceReceipt(
        schema_version="0.1.0",
        evidence_id=evidence_id,
        captured_at=utc_now_iso(),
        sha256=sha256_bytes(raw),
        prev_sha256=prev_sha,
        source={"type": "simulated", "actor": "aurora-kernel"},
    )

def run_minimal_scenario(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = "RUN-" + sha256_bytes(utc_now_iso().encode("utf-8"))[:10].upper()
    scenario_id = "demo.startup.v1"

    tick = ["Build", "Prove", "Export"]

    receipt = make_receipt("EVID.LOGS.SAMPLE", {"message": "sample log line", "level": "INFO"})

    run_manifest = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "scenario_id": scenario_id,
        "tick": tick,
        "started_at": utc_now_iso(),
        "ended_at": utc_now_iso(),
    }

    decisions = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "results": [
            {"control_id": "CTRL.LOGGING.BASIC", "status": "pass", "invariant_trace": "Simulated log evidence present."},
            {"control_id": "CTRL.DATA.RETENTION.BASIC", "status": "unknown", "invariant_trace": "No retention policy evidence in minimal run."},
        ],
    }

    (out_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    (out_dir / "decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    (out_dir / "evidence_receipts.json").write_text(json.dumps([receipt.__dict__], indent=2), encoding="utf-8")
    (out_dir / "audit_chain.json").write_text(json.dumps({"note": "hash-chain stub (extend in v0.2)"}, indent=2), encoding="utf-8")
    return out_dir
