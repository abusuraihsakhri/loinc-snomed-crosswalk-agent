"""
Command-Line Interface for OntoCrosswalk Sentinel: LOINC, SNOMED-CT & ICD-10 Semantic Harmonization Agent.
"""
import argparse
import csv
import sys
from .models import ClinicalCasePayload
from .agents import OntologyCoordinator

coordinator = OntologyCoordinator()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="loinc-snomed-crosswalk-agent", description="OntoCrosswalk Sentinel: LOINC, SNOMED-CT & ICD-10 Semantic Harmonization Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single case clinical audit")
    p_audit.add_argument("--case-id", default="CASE-2026-001")
    p_audit.add_argument("--primary", type=float, default=26.2)
    p_audit.add_argument("--secondary", type=float, default=12.5)
    p_audit.add_argument("--stat", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    # Explicit, user-supplied terminology lookup (not a clinical inference).
    p_crosswalk = subparsers.add_parser("crosswalk", help="Exact lookup in a user-provided LOINC/SNOMED mapping CSV")
    p_crosswalk.add_argument("-m", "--mapping", required=True, help="Mapping CSV with provenance")
    query_group = p_crosswalk.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--term", help="Local observation term to look up")
    query_group.add_argument("--queries", help="Query CSV with a local_term column")
    p_crosswalk.add_argument("-o", "--output", help="Optional JSON output file")

    args = parser.parse_args(argv)

    if args.command == "crosswalk":
        from loinc_snomed_crosswalk_agent.crosswalk import run_cli
        return run_cli(args)


    if args.command == "audit":
        case = ClinicalCasePayload(
            case_id=args.case_id,
            patient_synthetic_id="SYNTH-PT-881",
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_flag=args.status,
            is_stat=args.stat,
        )
        dossier = coordinator.process_case(case)
        print("=" * 80)
        print(f"  ONTOCROSSWALK SENTINEL: LOINC, SNOMED-CT & ICD-10 SEMANTIC HARMONIZATION AGENT")
        print(f"  Domain: Medical Informatics | Standard: Regenstrief LOINC & SNOMED International")
        print(f"  Case: {dossier['case_id']} | Status: [{dossier['overall_status']}] | Total Alerts: {dossier['total_alerts']}")
        print("=" * 80)
        for a in dossier["alerts"]:
            print(f"\n  [{a['urgency']}] from {a['sub_agent']}:")
            print(f"  Title: {a['title']}")
            print(f"  Finding: {a['clinical_finding']}")
            print(f"  Action: {a['actionable_recommendation']}")
        print("\n" + "=" * 80)
        return 0

    if args.command == "chat":
        ans = coordinator.query_supervisory_chat(" ".join(args.query))
        print(f"\n[OntologyCoordinator]:\n{ans}\n")
        return 0

    if args.command == "batch":
        from pathlib import Path
        cwd = Path.cwd()
        safe_input = Path(args.input).resolve()
        safe_output = Path(args.output).resolve()
        try:
            safe_input.relative_to(cwd.resolve())
            safe_output.relative_to(cwd.resolve())
        except ValueError:
            print(f"Error: Batch paths must be within the working directory.", file=sys.stderr)
            return 1
        if not safe_input.is_file():
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            return 1

        try:
            with open(safe_input, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
        except (csv.Error, OSError) as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            return 1

        out_fields = fieldnames + ["overall_status", "total_alerts", "stat_critical_alerts", "consensus_summary"]
        out_rows = []
        for r in rows:
            try:
                case = ClinicalCasePayload(
                    case_id=r.get("case_id", "CASE-01"),
                    patient_synthetic_id=r.get("patient_synthetic_id", "SYNTH-01"),
                    primary_metric=float(r.get("metric_primary", r.get("primary_metric", 15.0))),
                    secondary_metric=float(r.get("metric_secondary", r.get("secondary_metric", 5.0))),
                    status_flag=r.get("status_flag", r.get("status_text", "NORMAL")),
                    is_stat=str(r.get("is_stat", r.get("critical_flag", ""))).lower() in ("true", "1", "yes"),
                )
                dossier = coordinator.process_case(case)
            except (ValueError, TypeError) as e:
                print(f"Warning: Skipping row due to error: {e}", file=sys.stderr)
                continue
            row_dict = dict(r)
            row_dict["overall_status"] = dossier["overall_status"]
            row_dict["total_alerts"] = dossier["total_alerts"]
            row_dict["stat_critical_alerts"] = dossier["stat_critical_alerts"]
            row_dict["consensus_summary"] = dossier["consensus_summary"]
            out_rows.append(row_dict)

        try:
            with open(safe_output, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            return 1
        print(f"Batch processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
            from .server import create_app
            app = create_app()
            if app:
                print(f"Starting OntoCrosswalk Sentinel: LOINC, SNOMED-CT & ICD-10 Semantic Harmonization Agent on http://{args.host}:{args.port}")
                uvicorn.run(app, host=args.host, port=args.port)
        except ImportError:
            print("FastAPI / uvicorn not installed. Run 'pip install fastapi uvicorn'")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
