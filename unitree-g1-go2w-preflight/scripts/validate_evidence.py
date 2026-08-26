#!/usr/bin/env python3
"""Validate a Unitree preflight evidence snapshot without contacting a robot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "unitree-preflight-v1"
STATUS_VALUES = {"unknown", "observed", "not_observed", "not_applicable"}

STATUS_PATHS = (
    "network.state_stream", "network.state_freshness", "authority.mode_readback",
    "authority.command_owner", "authority.lease_or_authority", "authority.competing_publishers",
    "safety.specific_motion_authorized", "safety.site_authorized", "safety.area_clear",
    "safety.observer_ready", "safety.manual_takeover_ready", "safety.independent_stop_ready",
    "navigation.tf_contract", "navigation.odometry_fresh", "navigation.sensor_fresh",
    "navigation.timeout_zero_policy", "manipulation.arm_state", "manipulation.joint_ownership",
    "manipulation.payload_and_tool", "manipulation.navigation_interlock",
    "physical.motion_observed", "physical.stop_observed",
)

IDENTITY_PATHS = (
    "robot.model", "robot.exact_configuration", "robot.firmware",
    "software.sdk_version_or_commit", "software.application_commit",
)


def value_at(document: dict[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def known_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() != "unknown"


def all_observed(document: dict[str, Any], paths: tuple[str, ...]) -> bool:
    return all(value_at(document, path) in {"observed", "not_applicable"} for path in paths)


def validate(document: dict[str, Any]) -> tuple[list[str], list[str], str]:
    errors: list[str] = []
    warnings: list[str] = []
    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")

    for path in STATUS_PATHS:
        value = value_at(document, path)
        if value is None:
            errors.append(f"missing field: {path}")
        elif not isinstance(value, str) or value not in STATUS_VALUES:
            errors.append(f"{path} must be one of {sorted(STATUS_VALUES)}")

    missing_identity = [path for path in IDENTITY_PATHS if not known_text(value_at(document, path))]
    if missing_identity:
        warnings.append("identity incomplete: " + ", ".join(missing_identity))

    network_observed = all(
        known_text(value) for value in (
            value_at(document, "network.interface"), value_at(document, "network.local_address")
        )
    ) and all_observed(document, ("network.state_stream", "network.state_freshness"))
    authority_observed = all_observed(document, (
        "authority.mode_readback", "authority.command_owner",
        "authority.lease_or_authority", "authority.competing_publishers",
    ))
    safety_recorded = all_observed(document, (
        "safety.specific_motion_authorized", "safety.site_authorized", "safety.area_clear",
        "safety.observer_ready", "safety.manual_takeover_ready", "safety.independent_stop_ready",
    ))

    if missing_identity:
        level = "E0_UNVERIFIED"
    elif not network_observed:
        level = "E1_LOCAL_IDENTITY"
    elif not authority_observed:
        level = "E1_FRESH_STATE"
    elif not safety_recorded:
        level = "E1_AUTHORITY_RECORDED"
    else:
        level = "E1_PREFLIGHT_GATES_RECORDED"

    if value_at(document, "physical.motion_observed") == "observed":
        warnings.append("physical motion is reported; this validator does not verify or authorize it")
    if value_at(document, "physical.stop_observed") == "observed":
        warnings.append("physical stop is reported; retain measured zero-band, distance, and posture evidence")

    return errors, warnings, level


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="JSON snapshot based on the bundled template")
    args = parser.parse_args()
    try:
        document = json.loads(args.snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    if not isinstance(document, dict):
        print(json.dumps({"valid": False, "errors": ["top-level JSON must be an object"]}, ensure_ascii=False, indent=2))
        return 2

    errors, warnings, level = validate(document)
    result = {
        "valid": not errors,
        "maximum_supported_evidence": level,
        "motion_authorized": False,
        "errors": errors,
        "warnings": warnings,
        "note": "This local validator never contacts a robot and never authorizes motion.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
