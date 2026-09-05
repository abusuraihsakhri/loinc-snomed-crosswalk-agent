"""
Automated Pytest Test Suite for Loinc Snomed Crosswalk Agent.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, validate_safe_path, AuditTrail
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_validate_safe_path_allows_cwd_paths():
    """Paths within the working directory should be allowed."""
    cwd = Path.cwd()
    test_file = cwd / "test_safe_path.tmp"
    test_file.write_text("test")
    try:
        result = validate_safe_path("test_safe_path.tmp", must_exist=True)
        assert Path(result).resolve() == test_file.resolve()
    finally:
        test_file.unlink()


def test_validate_safe_path_rejects_traversal():
    """Paths outside the working directory should be rejected."""
    with pytest.raises(PermissionError):
        validate_safe_path("/etc/passwd")
    with pytest.raises(PermissionError):
        validate_safe_path("../../../etc/passwd")


def test_validate_safe_path_missing_file():
    """Non-existent files should raise FileNotFoundError when must_exist=True."""
    with pytest.raises(FileNotFoundError):
        validate_safe_path("nonexistent_file_12345.csv", must_exist=True)


def test_audit_trail_uses_env_key():
    """AuditTrail should use AUDIT_SECRET_KEY from environment when set."""
    os.environ["AUDIT_SECRET_KEY"] = "test-secret-key-12345"
    try:
        trail = AuditTrail()
        assert trail.secret_key == b"test-secret-key-12345"
    finally:
        del os.environ["AUDIT_SECRET_KEY"]


def test_audit_trail_falls_back_to_random_key():
    """AuditTrail should generate a random key when no env var is set."""
    os.environ.pop("AUDIT_SECRET_KEY", None)
    trail = AuditTrail()
    # Key should be 64 hex chars = 32 bytes
    assert len(trail.secret_key) == 64


def test_batch_cli_with_missing_file_returns_error():
    """CLI batch command should return non-zero for missing input file."""
    result = main(["batch", "-i", "nonexistent_input_12345.csv"])
    assert result == 1


def test_batch_cli_with_path_traversal_returns_error():
    """CLI batch command should reject paths outside working directory."""
    result = main(["batch", "-i", "/etc/passwd"])
    assert result == 1


def test_batch_cli_success():
    """CLI batch command should process a valid CSV file in the working directory."""
    cwd = Path.cwd()
    input_file = cwd / "test_batch_input.csv"
    output_file = cwd / "test_batch_output.csv"
    input_file.write_text("task_id,target_identifier,primary_metric,secondary_metric,status_descriptor\nT1,KEY-01,10.0,5.0,NOMINAL\n")
    try:
        result = main(["batch", "-i", str(input_file), "-o", str(output_file)])
        assert result == 0
        assert output_file.exists()
    finally:
        if input_file.exists():
            input_file.unlink()
        if output_file.exists():
            output_file.unlink()
