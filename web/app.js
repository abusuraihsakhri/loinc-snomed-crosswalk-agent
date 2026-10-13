"use strict";

// Local-only terminology index. Data is supplied and interpreted by the user.
const COLUMNS = ["local_term", "loinc_code", "snomed_code", "relation", "source", "version"];
const RELATIONS = new Set(["equivalent", "associated", "answer"]);
const MAX_ROWS = 50000;
const MAX_FILE_BYTES = 2 * 1024 * 1024;
const CAUTION = "User-supplied mapping only. Identifier existence, licensing and clinical equivalence are not verified.";

function normalizeTerm(value) {
  return String(value).trim().replace(/\s+/gu, " ").toLocaleLowerCase("en");
}

function parseCSV(content) {
  if (typeof content !== "string") throw new Error("Expected UTF-8 CSV text");
  const text = content.replace(/^\uFEFF/u, "");
  const rows = [];
  let row = [], cell = "", quoted = false, closed = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cell += '"'; i += 1; }
        else { quoted = false; closed = true; }
      } else { cell += ch; }
    } else if (ch === "," || ch === "\n" || ch === "\r") {
      row.push(cell); cell = ""; closed = false;
      if (ch !== ",") {
        if (row.some(v => v !== "")) rows.push(row);
        row = [];
        if (ch === "\r" && text[i + 1] === "\n") i += 1;
      }
    } else if (ch === '"') {
      if (cell !== "" || closed) throw new Error("Unexpected quote in CSV field");
      quoted = true;
    } else {
      if (closed && ch !== " ") throw new Error("Unexpected characters after CSV quote");
      if (!closed) cell += ch;
    }
  }
  if (quoted) throw new Error("Unclosed quoted CSV field");
  row.push(cell);
  if (row.some(v => v !== "")) rows.push(row);
  return rows;
}

function buildIndex(csv) {
  const rows = parseCSV(csv);
  if (!rows.length) throw new Error("Mapping CSV is empty");
  const headers = rows[0].map(v => v.trim());
  if (new Set(headers).size !== headers.length) throw new Error("Duplicate CSV column name");
  for (const col of COLUMNS) {
    if (!headers.includes(col)) throw new Error("Missing column: " + col);
  }
  if (rows.length - 1 > MAX_ROWS) throw new Error("More than 50,000 records");
  const index = new Map();
  rows.slice(1).forEach((values, pos) => {
    if (values.length !== headers.length) throw new Error("Column count mismatch on row " + (pos + 2));
    const entry = {};
    headers.forEach((header, j) => { entry[header] = values[j].trim(); });
    if (COLUMNS.some(name => !entry[name])) throw new Error("Missing value on row " + (pos + 2));
    if (entry.local_term.length > 256 || entry.source.length > 256)
      throw new Error("Field too long on row " + (pos + 2));
    if (!/^[0-9]{1,7}-[0-9]$/u.test(entry.loinc_code))
      throw new Error("Invalid LOINC format on row " + (pos + 2));
    if (!/^[0-9]{6,18}$/u.test(entry.snomed_code))
      throw new Error("Invalid SNOMED format on row " + (pos + 2));
    entry.relation = entry.relation.toLowerCase();
    if (!RELATIONS.has(entry.relation)) throw new Error("Unsupported relation on row " + (pos + 2));
    const key = normalizeTerm(entry.local_term);
    if (!index.has(key)) index.set(key, []);
    index.get(key).push(Object.fromEntries(COLUMNS.map(col => [col, entry[col]])));
  });
  return { index, count: rows.length - 1 };
}

function lookup(index, term) {
  if (typeof term !== "string" || !term.trim() || term.length > 256)
    throw new Error("Each query must be 1–256 characters");
  const matches = index.get(normalizeTerm(term)) || [];
  const seen = new Set();
  const candidates = matches.filter(entry => {
    const key = JSON.stringify(COLUMNS.map(col => entry[col]));
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });
  return {
    query: term,
    status: !candidates.length ? "unmapped" : candidates.length === 1 ? "single_candidate" : "ambiguous",
    candidates,
    warning: CAUTION
  };
}

function escapeCsvField(value) {
  let raw = String(value ?? "");
  // Prevent spreadsheet formula injection when a CSV is subsequently opened.
  if (/^\s*[=+@-]/u.test(raw) || /^[\t\r]/u.test(raw)) raw = "'" + raw;
  return '"' + raw.replace(/"/gu, '""') + '"';
}

function resultsToCSV(results) {
  const names = ["query", "status", ...COLUMNS.slice(1)];
  const rows = [names];
  for (const result of results) {
    const entries = result.candidates.length ? result.candidates : [null];
    for (const entry of entries) {
      rows.push([result.query, result.status,
        ...COLUMNS.slice(1).map(key => entry ? entry[key] : "")]);
    }
  }
  return rows.map(row => row.map(escapeCsvField).join(",")).join("\r\n") + "\r\n";
}

function initialize() {
  const fileInput = document.getElementById("mapping-file");
  const queriesInput = document.getElementById("queries");
  const runButton = document.getElementById("run");
  const exportButton = document.getElementById("export");
  const feedback = document.getElementById("feedback");
  const tbody = document.getElementById("results");
  let index = null, results = [];
  const setFeedback = (text, error = false) => {
    feedback.textContent = text;
    feedback.classList.toggle("error", error);
  };
  function updateCounters() {
    const mapped = results.filter(r => r.status === "single_candidate").length;
    const ambiguous = results.filter(r => r.status === "ambiguous").length;
    const unmapped = results.filter(r => r.status === "unmapped").length;
    for (const [id, value] of [["map-count", index ? index.count : 0],
      ["query-count", results.length], ["matched-count", mapped],
      ["ambiguous-count", ambiguous], ["unmapped-count", unmapped]]) {
      document.getElementById(id).textContent = String(value);
    }
  }
  fileInput.addEventListener("change", async () => {
    index = null; results = []; tbody.replaceChildren();
    runButton.disabled = true; exportButton.disabled = true;
    updateCounters();
    const file = fileInput.files && fileInput.files[0];
    if (!file) { setFeedback("Select a mapping CSV."); return; }
    if (file.size > MAX_FILE_BYTES) { setFeedback("Mapping file exceeds 2 MiB.", true); return; }
    try {
      index = buildIndex(await file.text());
      runButton.disabled = index.count === 0;
      setFeedback("Loaded " + index.count + " user-supplied mapping rows. Nothing uploaded.");
      updateCounters();
    } catch (err) { setFeedback("Invalid mapping: " + err.message, true); }
  });
  document.getElementById("lookup-form").addEventListener("submit", event => {
    event.preventDefault();
    if (!index) { setFeedback("Load a valid CSV first.", true); return; }
    const terms = queriesInput.value.split(/\r?\n/u).map(t => t.trim()).filter(Boolean);
    if (!terms.length || terms.length > 5000) {
      setFeedback("Enter 1–5,000 local terms, one per line.", true); return;
    }
    try {
      results = terms.map(t => lookup(index.index, t));
      const fragment = document.createDocumentFragment();
      for (const res of results) {
        const candidates = res.candidates.length ? res.candidates : [null];
        for (const candidate of candidates) {
          const row = document.createElement("tr");
          const values = [res.query, res.status, candidate?.loinc_code || "—",
            candidate?.snomed_code || "—", candidate?.relation || "—",
            candidate?.source || "—", candidate?.version || "—"];
          for (const value of values) {
            const cell = document.createElement("td");
            cell.textContent = value; row.appendChild(cell);
          }
          fragment.appendChild(row);
        }
      }
      tbody.replaceChildren(fragment);
      exportButton.disabled = !results.length;
      updateCounters();
      setFeedback("Exact-label search complete. Ambiguous candidates require manual review.");
    } catch (err) { setFeedback("Query error: " + err.message, true); }
  });
  exportButton.addEventListener("click", () => {
    if (!results.length) return;
    const blob = new Blob([resultsToCSV(results)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = "crosswalk-results.csv";
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  updateCounters();
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { parseCSV, buildIndex, lookup, normalizeTerm, resultsToCSV, escapeCsvField };
if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
}
