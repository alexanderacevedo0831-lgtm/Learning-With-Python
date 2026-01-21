import json
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from pathlib import Path

# =========================
# SYSTEM CONSTANTS
# =========================

THRESHOLDS = {
    "OK": (0, 90000),
    "WARN": (90001, 95000),
    "CRITICAL": (95001, 100000),
    "SENSOR_ERROR": (100001, float("inf")),
}

REQUIRED_FIELDS = {"timestamp", "metric", "value", "source"}
FIXED_METRIC = "weight_lb"
FIXED_SOURCE = "IND570_scale_01"

MAX_INVALID_RATIO = 0.30
MAX_CRITICAL_PER_DAY = 3

# =========================
# ENTRYPOINT
# =========================

def main():
    base_dir = Path(__file__).resolve().parent
    data_path = base_dir / "logs.json"
    report_path = base_dir / "report.txt"

    records, invalid_records = load_data(data_path)
    analysis = analyze_data(records)
    system_health = evaluate_system_health(analysis, invalid_records)
    generate_report(analysis, invalid_records, system_health, report_path)


# =========================
# DATA INGESTION
# =========================

def load_data(filepath: Path) -> Tuple[List[Dict], List[Dict]]:
    """
    Loads raw JSON data and separates valid and invalid records.
    Invalid records always include an explicit failure reason.
    """
    records = []
    invalid_records = []

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError("input_file_not_found")
    except json.JSONDecodeError:
        raise ValueError("invalid_json_format")

    if not data:
        invalid_records.append({"reason": "empty_file"})
        return records, invalid_records

    for entry in data:
        if not isinstance(entry, dict):
            invalid_records.append({
                "record": entry,
                "reason": "non_object_record"
            })
            continue

        reason = validate_record(entry)

        if reason:
            invalid_records.append({
                "record": entry,
                "reason": reason
            })
        else:
            records.append(entry)

    return records, invalid_records


# =========================
# VALIDATION
# =========================

def validate_record(entry: Dict) -> Optional[str]:
    """
    Validates structural and semantic correctness of a record.
    Returns reason string if invalid, otherwise None.
    """
    if not REQUIRED_FIELDS.issubset(entry):
        return "missing_required_fields"

    if entry["metric"] != FIXED_METRIC:
        return "invalid_metric"

    if entry["source"] != FIXED_SOURCE:
        return "invalid_source"

    if not isinstance(entry["value"], int) or entry["value"] <= 0:
        return "invalid_value_type_or_range"

    try:
        datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        return "invalid_timestamp_format"

    if entry["value"] >= THRESHOLDS["SENSOR_ERROR"][0]:
        return "sensor_error_out_of_range"

    return None


# =========================
# ANALYSIS (EVIDENCE)
# =========================

def analyze_data(records: List[Dict]) -> Dict:
    """
    Classifies validated records into WARN and CRITICAL evidence.
    """
    analysis = {
        "total_events": len(records),
        "warnings": [],
        "criticals": [],
    }

    for record in records:
        value = record["value"]

        if THRESHOLDS["CRITICAL"][0] <= value <= THRESHOLDS["CRITICAL"][1]:
            analysis["criticals"].append(
                build_event(record, "critical_weight")
            )

        elif THRESHOLDS["WARN"][0] <= value <= THRESHOLDS["WARN"][1]:
            analysis["warnings"].append(
                build_event(record, "warning_weight")
            )

    return analysis


def build_event(record: Dict, reason: str) -> Dict:
    """
    Builds immutable evidence object for reporting.
    """
    return {
        "timestamp": record["timestamp"],
        "source": record["source"],
        "metric": record["metric"],
        "value": record["value"],
        "reason": reason,
    }


# =========================
# SYSTEM HEALTH
# =========================

def evaluate_system_health(
    analysis: Dict,
    invalid_records: List[Dict],
) -> Dict:
    """
    Determines overall system health based on data integrity and operational risk.
    This function assumes:
    - analysis was produced ONLY from trusted, validated records
    - invalid_records contains rejected records WITH reasons
    """

    total_valid = analysis.get("total_events", 0)
    total_invalid = len(invalid_records)
    total_records = total_valid + total_invalid

    invalid_ratio = (
        total_invalid / total_records
        if total_records > 0
        else 0
    )

    unhealthy = False
    reasons = []

    # Data integrity failure
    if invalid_ratio >= MAX_INVALID_RATIO:
        unhealthy = True
        reasons.append("excessive_invalid_records")

    # Operational risk failure
    if len(analysis.get("criticals", [])) >= MAX_CRITICAL_PER_DAY:
        unhealthy = True
        reasons.append("excessive_critical_events")

    return {
        "status": "UNHEALTHY" if unhealthy else "HEALTHY",
        "reasons": reasons,
        "metrics": {
            "total_valid": total_valid,
            "total_invalid": total_invalid,
            "invalid_ratio": round(invalid_ratio, 2),
            "critical_events": len(analysis.get("criticals", [])),
        },
    }


# =========================
# REPORTING
# =========================

def generate_report(
    analysis: Dict,
    invalid_records: List[Dict],
    system_health: str,
    output_file: Path,
) -> None:
    """
    Writes a human-readable operational report.
    """
    with output_file.open("w") as f:
        # Header
        f.write("SYSTEM HEALTH REPORT\n")
        f.write("====================\n\n")

        # System health summary (highest priority evidence)
        f.write(f"System Health Status: {system_health}\n\n")

        # Valid data summary
        f.write("VALID DATA SUMMARY\n")
        f.write("------------------\n")
        f.write(f"Total Valid Records: {analysis['total_events']}\n")
        f.write(f"Warning Events: {len(analysis['warnings'])}\n")
        f.write(f"Critical Events: {len(analysis['criticals'])}\n\n")

        # Critical events first (worst issues surface first)
        if analysis["criticals"]:
            f.write("CRITICAL EVENTS\n")
            f.write("---------------\n")
            for event in analysis["criticals"]:
                f.write(f"- {event}\n")
            f.write("\n")

        # Warning events
        if analysis["warnings"]:
            f.write("WARNING EVENTS\n")
            f.write("--------------\n")
            for event in analysis["warnings"]:
                f.write(f"- {event}\n")
            f.write("\n")

        # Invalid records (never mixed with valid evidence)
        if invalid_records:
            f.write("INVALID RECORDS (DATA INTEGRITY ISSUES)\n")
            f.write("--------------------------------------\n")
            f.write(f"Total Invalid Records: {len(invalid_records)}\n\n")
            for item in invalid_records:
                f.write(f"- {item}\n")
            f.write("\n")

        # Explicit end-of-report marker
        f.write("END OF REPORT\n")

if __name__ == "__main__":
    main()