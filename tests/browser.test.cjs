"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { parseCSV, buildIndex, lookup, resultsToCSV } = require("../web/app.js");

const header = "local_term,loinc_code,snomed_code,relation,source,version\r\n";
const row = '"Serum, assay",1234-5,123456789,associated,synthetic-test,2026\r\n';

test("RFC-style escaped quotes and embedded line breaks", () => {
  assert.deepEqual(parseCSV('x,y\r\n"alpha ""quote""","two\nlines"\r\n'),
                   [["x", "y"], ['alpha "quote"', "two\nlines"]]);
  assert.throws(() => parseCSV('a,b\n"unterminated'), /Unclosed/);
});

test("exact candidate, unmapped and ambiguous are distinct", () => {
  const one = buildIndex(header + row);
  assert.equal(one.count, 1);
  assert.equal(lookup(one.index, "  SERUM,   ASSAY ").status, "single_candidate");
  assert.equal(lookup(one.index, "Serum assay").status, "unmapped");
  const multiple = buildIndex(header + row + '"Serum, assay",1234-5,987654321,answer,synthetic-test,2026\r\n');
  assert.equal(lookup(multiple.index, "Serum, assay").status, "ambiguous");
});

test("invalid mapping rows are rejected", () => {
  assert.throws(() => buildIndex("local_term,loinc_code\nA,1234-5\n"), /Missing column/);
  assert.throws(() => buildIndex(header + "A,INVALID,123456789,answer,test,v1\n"), /Invalid LOINC/);
  assert.throws(() => buildIndex(header + "A,1234-5,123456789,invalid,test,v1\n"), /Unsupported relation/);
});

test("result exports neutralize formula injection", () => {
  const data = resultsToCSV([{query:"=SUM(1,1)",status:"unmapped",candidates:[]}]);
  assert.match(data, /"'=SUM\(1,1\)"/);
});
