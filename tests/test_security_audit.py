import pytest
from agents.base import AuditTrail


def test_audit_checks_signature_not_only_link_pointers():
    audit = AuditTrail(secret_key="only-for-test")
    audit.log("system", "test", "EVENT", {"status": "OK"})
    audit.log("system", "test", "EVENT", {"status": "MORE"})
    assert audit.verify_integrity() is True
    audit.logs[0]["event_type"] = "FORGED"
    assert audit.verify_integrity() is False


def test_audit_api_returns_defensive_copy():
    audit = AuditTrail(secret_key="only-for-test")
    audit.log("system", "test", "EVENT", {"status": "OK"})
    retrieved = audit.get_trail()
    retrieved[0]["event_type"] = "FORGED"
    assert audit.verify_integrity() is True
