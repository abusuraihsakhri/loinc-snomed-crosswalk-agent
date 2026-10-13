"""Focused regression tests for exact, user-provided terminology mappings."""
import json
from types import SimpleNamespace

import pytest

from loinc_snomed_crosswalk_agent.crosswalk import load_mappings, lookup, load_terms, run_cli


HEADER = "local_term,loinc_code,snomed_code,relation,source,version\n"
A = "Serum assay,1234-5,123456789,associated,synthetic-test,2026-01\n"
B = "Serum assay,1234-5,987654321,answer,synthetic-test,2026-02\n"


def fixture(tmp_path, rows=A):
    file = tmp_path / "mapping.csv"
    file.write_text(HEADER + rows, encoding="utf-8")
    return file


def test_exact_lookup_and_normalization(tmp_path):
    index = load_mappings(fixture(tmp_path))
    result = lookup(index, "  SERUM   ASSAY  ")
    assert result["status"] == "single_candidate"
    assert result["candidates"][0]["snomed_code"] == "123456789"
    assert "NOT been independently verified" in result["warning"]


def test_unmapped_does_not_guess(tmp_path):
    index = load_mappings(fixture(tmp_path))
    assert lookup(index, "Serum assays")["status"] == "unmapped"
    assert lookup(index, "Serum assays")["candidates"] == []


def test_ambiguous_assertions_remain_visible(tmp_path):
    index = load_mappings(fixture(tmp_path, A + B))
    result = lookup(index, "serum assay")
    assert result["status"] == "ambiguous"
    assert len(result["candidates"]) == 2


def test_identical_duplicates_are_deduplicated(tmp_path):
    index = load_mappings(fixture(tmp_path, A + A))
    assert lookup(index, "serum assay")["status"] == "single_candidate"


@pytest.mark.parametrize("rows", [
    "Test,1234-5,123456789,invalid,synthetic-test,2026\n",
    "Test,NOT-LOINC,123456789,answer,synthetic-test,2026\n",
    "Test,1234-5,not-a-code,answer,synthetic-test,2026\n",
    "Test,1234-5,123456789,answer,,2026\n",
    "Test,1234-5,123456789,answer,synthetic-test,2026,extra\n",
])
def test_reject_invalid_rows(tmp_path, rows):
    with pytest.raises(ValueError):
        load_mappings(fixture(tmp_path, rows))


def test_cli_single_and_batch(tmp_path, capsys):
    mapping = fixture(tmp_path)
    args = SimpleNamespace(term="Serum assay", queries=None, output=None, mapping=str(mapping))
    assert run_cli(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "single_candidate"
    terms = tmp_path / "terms.csv"
    terms.write_text("local_term\nSerum assay\nNot found\n", encoding="utf-8")
    args.term = None
    args.queries = str(terms)
    out = tmp_path / "results.json"
    args.output = str(out)
    assert run_cli(args) == 0
    assert [r["status"] for r in json.loads(out.read_text())] == ["single_candidate", "unmapped"]


def test_reject_overwrite_and_malformed_query(tmp_path):
    mapping = fixture(tmp_path)
    args = SimpleNamespace(term="Serum assay", queries=None, output=str(mapping), mapping=str(mapping))
    assert run_cli(args) == 1
    query = tmp_path / "terms.csv"
    query.write_text("something_else\nA\n")
    with pytest.raises(ValueError):
        load_terms(query)
