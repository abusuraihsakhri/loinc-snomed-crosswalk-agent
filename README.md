# LOINC–SNOMED Crosswalk Agent

A local terminology-review utility for **exact lookups against user-provided, versioned LOINC–SNOMED CT mapping tables**. The Python CLI and browser app distinguish a single candidate, multiple conflicting candidates, and unmapped terms. No mapping is inferred or invented.

**Not a clinical terminology authority or decision-support device.** It does not check whether a code exists, verify equivalence, interpret laboratory results, or perform patient-specific clinical validation. Do not use unreviewed output for clinical coding or care.

## Browser application

The browser app is in [`web/index.html`](web/index.html). Open the file in a modern browser, select a CSV mapping table, enter local laboratory terms, and export reviewed candidates as CSV. The lookup runs locally in JavaScript with **no backend or file upload**. It supports:

- Exact, case-insensitive, whitespace-normalized lookups (no synonym guessing)
- Ambiguous and unmapped results rather than silent fallbacks
- Source, version and relationship shown for each candidate
- CSV export with protections against spreadsheet-formula execution
- Responsive layout, keyboard-accessible controls, and no external runtime dependencies

GitHub Pages can serve the same static folder through the supplied workflow. The browser interface does not run the FastAPI server or the legacy numerical audit.

## Mapping data contract

Bring your own appropriately licensed and expert-reviewed mapping CSV; **no copyrighted terminology database is bundled**. Required UTF-8 CSV columns:

```csv
local_term,loinc_code,snomed_code,relation,source,version
```

Every row must have all six values. Use `equivalent`, `associated`, or `answer` for `relation` to record an assertion from **your mapping source**, not one made by this software. Identifier checks are syntactic only: LOINC resembles `1234-5`; SNOMED CT consists of 6–18 digits. Neither identifier is checked against a terminology server or release.

Multiple distinct rows for the same normalized local term produce `ambiguous`, not a randomly selected winner. Duplicate identical rows are consolidated in lookup results. The tool preserves provenance and does not bundle the official LOINC Ontology mappings. Consult the [LOINC Ontology](https://loinc.org/ontology) and applicable SNOMED International licensing/implementation guidance before incorporating official releases.

## Install and use Python

Python 3.10–3.12 are exercised in CI (the package declares Python >=3.9).

```bash
git clone https://github.com/abusuraihsakhri/loinc-snomed-crosswalk-agent.git
cd loinc-snomed-crosswalk-agent
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Look up one term or a query file with a `local_term` column:

```bash
loinc-snomed-crosswalk-agent crosswalk --mapping your-mappings.csv --term "Your local assay"
loinc-snomed-crosswalk-agent crosswalk --mapping your-mappings.csv --queries local-terms.csv --output crosswalk-results.json
```

The same `crosswalk` command is supported by `python cli.py` for existing users. Python permits mapping/query CSV files up to 10 MiB and 50,000 records; the browser limits mapping CSV files to 2 MiB and queries to 5,000 terms.

## Existing legacy demo workflows

The pre-existing numeric-threshold evaluators, supervisor, and FastAPI REST endpoints are retained for backward compatibility. **These are generic demonstrations, not LOINC–SNOMED crosswalk algorithms or evidence-based clinical reference ranges.** They must not be interpreted as validated alarms or clinical decisions.

```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
python cli.py batch -i your-legacy-input.csv -o results.csv
python cli.py chat "What is the system status?"
python cli.py verify-audit
python cli.py serve --host 127.0.0.1 --port 8000
```

The legacy API provides `GET /health`, `GET /metrics`, `POST /api/audit`, `POST /api/chat`, and `GET /api/audit/logs`. Its interface has **no authentication**; keep it bound to localhost or protect it behind a properly configured reverse proxy and access-control layer. The API is not a terminology lookup service.

## Security and privacy

The browser crosswalk does not upload input files, use browser storage, or contact a terminology endpoint. Do not paste patient identifiers into this research utility. The Python legacy API includes **best-effort pattern-based** personal-identifier checks, which are not comprehensive anonymization or HIPAA compliance.

Legacy audit entries are HMAC-SHA256 signed and chained; verification recomputes signatures and predecessor links. The log exists **only in process memory**, is lost on restart, and is not a durable compliance audit record. Set a strong `AUDIT_SECRET_KEY` environment variable to keep the signing key consistent; otherwise a random ephemeral key is used.

Docker deployment:

```bash
export AUDIT_SECRET_KEY="replace-with-your-own-long-random-secret"
docker compose up --build
```

Compose binds to `127.0.0.1:8000` by default. The example value above is a placeholder: generate a unique secret and never commit it to the repository.

## Tests and development

```bash
python -m pip install -e . pytest build
pytest -q
python -m build
node --test tests/browser.test.cjs
```

GitHub Actions tests Python 3.10, 3.11 and 3.12, verifies package builds, and runs the dependency-free JavaScript regression suite using Node 22. No Pyodide is needed: the standalone browser functionality is implemented in plain JavaScript.

## License

MIT — see [LICENSE](LICENSE). This repository's MIT license does **not** grant rights to distribute third-party terminology releases, including SNOMED CT.
