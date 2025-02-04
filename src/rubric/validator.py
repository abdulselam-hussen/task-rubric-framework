"""Validators for task and rubric YAML files.

Each validator:
1. Parses the YAML/JSON
2. Validates against the JSON Schema
3. Runs semantic checks that the schema cannot express
4. Returns a ValidationReport with all errors and warnings
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
import jsonschema

from .models import (
    Rubric,
    Task,
    ValidationIssue,
    ValidationReport,
)

# Load schemas once at import time
_SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"


def _load_schema(name: str) -> dict:
    path = _SCHEMA_DIR / name
    if path.exists():
        return json.loads(path.read_text())
    # Fallback: minimal schema if running outside the project root
    return {}


_TASK_SCHEMA = _load_schema("task.schema.json")
_RUBRIC_SCHEMA = _load_schema("rubric.schema.json")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML or JSON file into a dict."""
    text = path.read_text()
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _schema_errors(data: dict, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not schema:
        return issues
    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        field = ".".join(str(p) for p in err.path) or "(root)"
        issues.append(ValidationIssue(severity="error", field=field, message=err.message))
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# TaskValidator
# ──────────────────────────────────────────────────────────────────────────────

class TaskValidator:
    """Validates a task YAML file against the schema and semantic rules."""

    def validate_file(self, path: str | Path) -> ValidationReport:
        path = Path(path)
        report = ValidationReport(path=str(path), kind="task", valid=False)

        try:
            data = _load_yaml(path)
        except Exception as exc:
            report.issues.append(
                ValidationIssue(severity="error", field="(file)", message=f"Parse error: {exc}")
            )
            return report

        # JSON Schema validation
        report.issues.extend(_schema_errors(data, _TASK_SCHEMA))

        # Semantic validation (only runs if schema passes)
        if not report.errors:
            try:
                task = Task.from_dict(data)
                report.issues.extend(self._semantic_checks(task, path))
            except Exception as exc:
                report.issues.append(
                    ValidationIssue(severity="error", field="(model)", message=str(exc))
                )

        report.valid = len(report.errors) == 0
        return report

    def _semantic_checks(self, task: Task, task_path: Path) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Milestone IDs must be sequential starting from 1
        expected_ids = list(range(1, len(task.milestones) + 1))
        actual_ids = [m.id for m in task.milestones]
        if actual_ids != expected_ids:
            issues.append(ValidationIssue(
                severity="error",
                field="milestones",
                message=f"Milestone IDs must be sequential from 1, got {actual_ids}",
            ))

        # Acceptance criteria IDs must be unique
        ac_ids = [ac.id for ac in task.acceptance_criteria]
        if len(ac_ids) != len(set(ac_ids)):
            issues.append(ValidationIssue(
                severity="error",
                field="acceptance_criteria",
                message="Acceptance criteria IDs must be unique",
            ))

        # Description should be meaningful (at least 20 words)
        if len(task.description.split()) < 20:
            issues.append(ValidationIssue(
                severity="warning",
                field="description",
                message="Description is very short; consider adding more context for the agent",
            ))

        # user_intent should be a single sentence
        if task.user_intent.count(".") > 2:
            issues.append(ValidationIssue(
                severity="warning",
                field="user_intent",
                message="user_intent should be a single sentence",
            ))

        # If rubric field is set, the file should exist relative to the task file
        if task.rubric:
            rubric_path = task_path.parent / task.rubric
            if not rubric_path.exists():
                issues.append(ValidationIssue(
                    severity="warning",
                    field="rubric",
                    message=f"Rubric file not found: {rubric_path}",
                ))

        # If reference_solution is set, the file should exist
        if task.reference_solution:
            sol_path = task_path.parent / task.reference_solution
            if not sol_path.exists():
                issues.append(ValidationIssue(
                    severity="warning",
                    field="reference_solution",
                    message=f"Reference solution not found: {sol_path}",
                ))

        # Weights sum warning delegated to RubricValidator
        return issues


# ──────────────────────────────────────────────────────────────────────────────
# RubricValidator
# ──────────────────────────────────────────────────────────────────────────────

class RubricValidator:
    """Validates a rubric YAML file against the schema and semantic rules."""

    VALID_CATEGORIES = {"functionality", "test_results", "security", "requirements", "code_quality"}

    def validate_file(self, path: str | Path) -> ValidationReport:
        path = Path(path)
        report = ValidationReport(path=str(path), kind="rubric", valid=False)

        try:
            data = _load_yaml(path)
        except Exception as exc:
            report.issues.append(
                ValidationIssue(severity="error", field="(file)", message=f"Parse error: {exc}")
            )
            return report

        report.issues.extend(_schema_errors(data, _RUBRIC_SCHEMA))

        if not report.errors:
            try:
                rubric = Rubric.from_dict(data)
                report.issues.extend(self._semantic_checks(rubric))
            except Exception as exc:
                report.issues.append(
                    ValidationIssue(severity="error", field="(model)", message=str(exc))
                )

        report.valid = len(report.errors) == 0
        return report

    def _semantic_checks(self, rubric: Rubric) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Weights must sum to ~1.0
        total = rubric.total_weight
        if not (0.99 <= total <= 1.01):
            issues.append(ValidationIssue(
                severity="error",
                field="dimensions[*].weight",
                message=f"Dimension weights must sum to 1.0, got {total:.4f}",
            ))

        # Dimension IDs must be unique
        dim_ids = [d.id for d in rubric.dimensions]
        if len(dim_ids) != len(set(dim_ids)):
            issues.append(ValidationIssue(
                severity="error",
                field="dimensions[*].id",
                message="Dimension IDs must be unique",
            ))

        # At least one functionality dimension required
        cats = {d.category for d in rubric.dimensions}
        if "functionality" not in cats:
            issues.append(ValidationIssue(
                severity="warning",
                field="dimensions",
                message="No 'functionality' dimension found; consider adding one",
            ))

        # Each dimension should have a verification command
        for dim in rubric.dimensions:
            if not dim.verification:
                issues.append(ValidationIssue(
                    severity="warning",
                    field=f"dimensions.{dim.id}.verification",
                    message=f"Dimension '{dim.id}' has no verification command",
                ))

        # Disqualifying dimensions should have the highest weight
        disq = [d for d in rubric.dimensions if d.disqualifying]
        others = [d for d in rubric.dimensions if not d.disqualifying]
        if disq and others:
            max_disq = max(d.weight for d in disq)
            max_other = max(d.weight for d in others)
            if max_disq < max_other:
                issues.append(ValidationIssue(
                    severity="warning",
                    field="dimensions",
                    message=(
                        "A disqualifying dimension has lower weight than a non-disqualifying one; "
                        "consider increasing its weight to reflect its importance"
                    ),
                ))

        return issues
