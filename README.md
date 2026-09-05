# LOINC SNOMED Crosswalk Agent

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Standards:** CAP / CLSI / ISO / Regenstrief LOINC & SNOMED International

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

**LOINC SNOMED Crosswalk Agent** is an analytical platform for semantic harmonization of clinical laboratory observations. It maps local EHR laboratory strings to standardized LOINC codes and SNOMED-CT concepts using a multi-agent evaluation architecture with three specialized workers:

- **InvariantQCWorker** — Primary metric threshold monitoring
- **SafetyEscalationWorker** — Critical safety interlock and STAT escalation detection
- **ProtocolConformanceWorker** — Biomarker concordance and anomaly triage

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/loinc-snomed-crosswalk-agent.git
cd loinc-snomed-crosswalk-agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install fastapi uvicorn pydantic pytest
```

---

## Usage

### CLI Commands

```bash
# Single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT

# Batch process CSV records
python cli.py batch -i sample.csv -o results.csv

# Query the supervisory assistant
python cli.py chat "What is the system status?"

# Verify HMAC audit trail integrity
python cli.py verify-audit

# Launch FastAPI REST server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Input Data Schema (CSV)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `task_id` | Unique task / case identifier | Required |
| `target_identifier` | Entity or specimen key | Required |
| `primary_metric` | Primary measurement value | Required |
| `secondary_metric` | Secondary kinetic index | Optional |
| `status_descriptor` | Status code (NOMINAL, DISCORDANT, etc.) | Optional |
| `is_critical_flag` | Emergency escalation flag | Optional |

### REST API

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus operational metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Query supervisory assistant |
| `/api/audit/logs` | GET | Retrieve and verify HMAC audit trail |

---

## Security

* **Zero-PHI Outbound Guard:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, DOBs, and patient identifiers from outbound data.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
* **Path Traversal Protection:** Batch file I/O is validated to stay within the working directory.
* **Secure Key Management:** Audit signing key sourced from `AUDIT_SECRET_KEY` environment variable; falls back to ephemeral secure random key if unset (logs a warning).

### Environment Variables

| Variable | Description | Default |
|:---------|:------------|:--------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 audit signing key | Ephemeral random (warns) |
| `MODEL_PROVIDER` | LLM provider (mock, ollama, claude, openai) | mock |

---

## Testing

```bash
# Run full test suite
pytest -v

# Run with coverage (requires pytest-cov)
pytest -v --cov=agents --cov=loinc_snomed_crosswalk_agent
```

---

## Container Deployment

```bash
# Build and run with Docker
docker build -t loinc-snomed-crosswalk-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key loinc-snomed-crosswalk-agent

# Or use Docker Compose
AUDIT_SECRET_KEY=your-secret-key docker-compose up
```

---

## Architecture

```
cli.py (Entry Point)
  └── agents/
      ├── base.py          — PHI guard, HMAC audit trail, security utilities
      ├── models.py        — Pydantic schemas and data definitions
      ├── supervisor.py    — SystemSupervisor orchestrator
      ├── workers.py       — Three specialized evaluation workers
      ├── api.py           — FastAPI REST server
      ├── metrics.py       — Prometheus metrics exporter
      ├── learning.py      — Bayesian calibration engine
      └── streamer.py      — WebSocket telemetry broadcaster
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
