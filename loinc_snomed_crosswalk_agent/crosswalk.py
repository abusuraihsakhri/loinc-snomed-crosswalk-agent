"""Deterministic, provenance-preserving lookup of user-supplied terminology mappings.

This is a local exact-label index, NOT an authoritative terminology service.
LOINC and SNOMED CT identifiers are checked for shape, not existence or semantics.
"""
import csv
import io
import json
import re
from collections import defaultdict
from pathlib import Path

REQUIRED_COLUMNS = ("local_term", "loinc_code", "snomed_code", "relation", "source", "version")
LOINC_SHAPE = re.compile(r"^[0-9]{1,7}-[0-9]$")
SNOMED_SHAPE = re.compile(r"^[0-9]{6,18}$")
RELATIONS = frozenset(("equivalent", "associated", "answer"))
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50000
CAUTION = ("Exact local-term lookup only. Candidate mappings are user-supplied assertions; "
           "identifier syntax, terminology validity, semantic equivalence and licensing "
           "have NOT been independently verified. Review before clinical use.")


def normalize(term):
    if not isinstance(term, str):
        raise ValueError("Term must be text")
    return " ".join(term.split()).casefold()


def load_mappings(path):
    """Read an explicitly provided local CSV with required provenance columns."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Mapping CSV exceeds 10 MiB")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, strict=True)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Mapping CSV requires unique column names")
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise ValueError("Missing mapping column(s): " + ", ".join(sorted(missing)))
        index = defaultdict(list)
        for row_number, row in enumerate(reader, 2):
            if row_number > MAX_ROWS + 1:
                raise ValueError("Mapping CSV exceeds 50,000 records")
            if None in row:
                raise ValueError(f"Unexpected extra column at CSV row {row_number}")
            values = {k: (row.get(k) or "").strip() for k in REQUIRED_COLUMNS}
            if not all(values.values()):
                raise ValueError(f"Missing required value at CSV row {row_number}")
            if len(values["local_term"]) > 256 or len(values["source"]) > 256:
                raise ValueError(f"Field too long at CSV row {row_number}")
            if not LOINC_SHAPE.fullmatch(values["loinc_code"]):
                raise ValueError(f"Invalid LOINC identifier format at CSV row {row_number}")
            if not SNOMED_SHAPE.fullmatch(values["snomed_code"]):
                raise ValueError(f"Invalid SNOMED identifier format at CSV row {row_number}")
            values["relation"] = values["relation"].lower()
            if values["relation"] not in RELATIONS:
                raise ValueError(f"Unsupported relation at CSV row {row_number}")
            index[normalize(values["local_term"])].append(values)
    return dict(index)


def lookup(index, term):
    key = normalize(term)
    if not key or len(term) > 256:
        raise ValueError("Enter a local term (up to 256 characters)")
    candidates = index.get(key, [])
    # Deduplicate identical assertions without hiding conflicting alternatives.
    unique = list({tuple(c[k] for k in REQUIRED_COLUMNS): c for c in candidates}.values())
    status = ("unmapped" if not unique else
              "single_candidate" if len(unique) == 1 else "ambiguous")
    return {"query": term, "status": status, "candidates": unique, "warning": CAUTION}


def export_json(index, terms):
    return json.dumps([lookup(index, term) for term in terms], indent=2, ensure_ascii=False)


def load_terms(path):
    """Read a query CSV with a local_term column; no patient data is needed."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Query CSV exceeds 10 MiB")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, strict=True)
        if not reader.fieldnames or "local_term" not in reader.fieldnames:
            raise ValueError("Query CSV requires local_term column")
        terms = []
        for row_number, row in enumerate(reader, 2):
            if row_number > MAX_ROWS + 1:
                raise ValueError("Query CSV exceeds 50,000 records")
            if None in row:
                raise ValueError(f"Unexpected extra column at query row {row_number}")
            terms.append(row.get("local_term") or "")
        return terms
