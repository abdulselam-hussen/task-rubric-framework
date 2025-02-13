"""Tests for the Task & Rubric Design Framework.

Covers models, TaskValidator, and RubricValidator using the example
task and rubric YAML files as fixtures.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from rubric.models import (
    AcceptanceCriterion,
    HiddenEdgeCase,
    Milestone,
    Rubric,
    RubricDimension,
    Task,
    ValidationReport,
)
from rubric.validator import RubricValidator, TaskValidator


# ── Paths to example files ────────────────────────────────────────────────────

EXAMPLES = Path(__file__).parent.parent / "examples"
TASK_1 = EXAMPLES / "tasks" / "fix-null-dereference-001.yaml"
TASK_2 = EXAMPLES / "tasks" / "add-jwt-auth-002.yaml"
RUBRIC_1 = EXAMPLES / "rubrics" / "fix-null-dereference-001.yaml"
RUBRIC_2 = EXAMPLES / "rubrics" / "add-jwt-auth-002.yaml"


# ════════════════════════════════════════════════════════════════════════════
# Model tests
# ════════════════════════════════════════════════════════════════════════════

class TestTaskModel:
    def test_from_dict_required_fields(self):
        data = yaml.safe_load(TASK_1.read_text())
        task = Task.from_dict(data)
        assert task.id == "fix-null-dereference-001"
        assert task.version == "1.0"
        assert task.user_intent != ""

    def test_milestones_parsed(self):
        data = yaml.safe_load(TASK_1.read_text())
        task = Task.from_dict(data)
        assert len(task.milestones) >= 4
        assert all(isinstance(m, Milestone) for m in task.milestones)
        assert task.milestones[0].id == 1

    def test_acceptance_criteria_parsed(self):
        data = yaml.safe_load(TASK_1.read_text())
        task = Task.from_dict(data)
        assert len(task.acceptance_criteria) >= 3
        assert all(isinstance(ac, AcceptanceCriterion) for ac in task.acceptance_criteria)

    def test_hidden_edge_cases_parsed(self):
        data = yaml.safe_load(TASK_1.read_text())
        task = Task.from_dict(data)
        assert len(task.hidden_edge_cases) >= 2
        assert all(isinstance(hec, HiddenEdgeCase) for hec in task.hidden_edge_cases)

    def test_defaults(self):
        task = Task.from_dict({
            "id": "t1",
            "version": "1.0",
            "name": "Test task",
            "description": "A test task description with enough words to be valid.",
            "user_intent": "I want something.",
            "milestones": [{"id": 1, "description": "Do it."}],
            "acceptance_criteria": [{"id": "ac-1", "criterion": "It works."}],
        })
        assert task.difficulty == "medium"
        assert task.repo_ref == "main"
        assert task.timeout_seconds == 300


class TestRubricModel:
    def test_from_dict(self):
        data = yaml.safe_load(RUBRIC_1.read_text())
        rubric = Rubric.from_dict(data)
        assert rubric.task_id == "fix-null-dereference-001"
        assert len(rubric.dimensions) >= 5

    def test_total_weight_near_one(self):
        data = yaml.safe_load(RUBRIC_1.read_text())
        rubric = Rubric.from_dict(data)
        assert abs(rubric.total_weight - 1.0) < 0.01

    def test_disqualifying_dimension(self):
        data = yaml.safe_load(RUBRIC_1.read_text())
        rubric = Rubric.from_dict(data)
        disq = [d for d in rubric.dimensions if d.disqualifying]
        assert len(disq) >= 1

    def test_removed_criteria_parsed(self):
        data = yaml.safe_load(RUBRIC_1.read_text())
        rubric = Rubric.from_dict(data)
        assert len(rubric.removed_criteria) >= 1
        assert rubric.removed_criteria[0].reason != ""


# ════════════════════════════════════════════════════════════════════════════
# TaskValidator tests
# ════════════════════════════════════════════════════════════════════════════

class TestTaskValidator:
    @pytest.fixture()
    def validator(self):
        return TaskValidator()

    def test_valid_task_1(self, validator):
        report = validator.validate_file(TASK_1)
        assert report.valid, f"Expected valid, errors: {[i.message for i in report.errors]}"

    def test_valid_task_2(self, validator):
        report = validator.validate_file(TASK_2)
        assert report.valid, f"Expected valid, errors: {[i.message for i in report.errors]}"

    def test_missing_required_field(self, validator, tmp_path):
        data = yaml.safe_load(TASK_1.read_text())
        del data["user_intent"]
        path = tmp_path / "bad_task.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        assert not report.valid
        assert any("user_intent" in i.message or "user_intent" in i.field for i in report.errors)

    def test_non_sequential_milestones(self, validator, tmp_path):
        data = yaml.safe_load(TASK_1.read_text())
        data["milestones"] = [
            {"id": 1, "description": "Step one."},
            {"id": 3, "description": "Skipped step two."},  # gap
        ]
        path = tmp_path / "bad_milestones.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        # Semantic check should catch the gap
        errors_and_warnings = report.errors + report.warnings
        assert any("sequential" in i.message.lower() or "milestones" in i.field
                   for i in errors_and_warnings)

    def test_duplicate_acceptance_criteria_ids(self, validator, tmp_path):
        data = yaml.safe_load(TASK_1.read_text())
        data["acceptance_criteria"] = [
            {"id": "ac-1", "criterion": "First."},
            {"id": "ac-1", "criterion": "Duplicate."},  # same ID
        ]
        path = tmp_path / "dup_ac.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        assert any("unique" in i.message.lower() for i in report.errors)

    def test_parse_error_reported(self, validator, tmp_path):
        path = tmp_path / "broken.yaml"
        path.write_text(":\n  - [invalid yaml{{{{")
        report = validator.validate_file(path)
        assert not report.valid
        assert report.errors

    def test_report_kind_is_task(self, validator):
        report = validator.validate_file(TASK_1)
        assert report.kind == "task"


# ════════════════════════════════════════════════════════════════════════════
# RubricValidator tests
# ════════════════════════════════════════════════════════════════════════════

class TestRubricValidator:
    @pytest.fixture()
    def validator(self):
        return RubricValidator()

    def test_valid_rubric_1(self, validator):
        report = validator.validate_file(RUBRIC_1)
        assert report.valid, f"Expected valid, errors: {[i.message for i in report.errors]}"

    def test_valid_rubric_2(self, validator):
        report = validator.validate_file(RUBRIC_2)
        assert report.valid, f"Expected valid, errors: {[i.message for i in report.errors]}"

    def test_weights_not_summing_to_one(self, validator, tmp_path):
        data = yaml.safe_load(RUBRIC_1.read_text())
        # Bump first weight so total > 1.0
        data["dimensions"][0]["weight"] = 0.99
        path = tmp_path / "bad_weights.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        assert not report.valid
        assert any("1.0" in i.message for i in report.errors)

    def test_duplicate_dimension_ids(self, validator, tmp_path):
        data = yaml.safe_load(RUBRIC_1.read_text())
        data["dimensions"][1]["id"] = data["dimensions"][0]["id"]  # create duplicate
        # Rebalance weights so weight-sum check passes
        n = len(data["dimensions"])
        for d in data["dimensions"]:
            d["weight"] = round(1.0 / n, 4)
        data["dimensions"][-1]["weight"] = round(
            1.0 - sum(d["weight"] for d in data["dimensions"][:-1]), 4
        )
        path = tmp_path / "dup_dims.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        assert any("unique" in i.message.lower() for i in report.errors)

    def test_missing_task_id(self, validator, tmp_path):
        data = yaml.safe_load(RUBRIC_1.read_text())
        del data["task_id"]
        path = tmp_path / "no_task_id.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        assert not report.valid

    def test_report_kind_is_rubric(self, validator):
        report = validator.validate_file(RUBRIC_1)
        assert report.kind == "rubric"

    def test_missing_verification_produces_warning(self, validator, tmp_path):
        data = yaml.safe_load(RUBRIC_1.read_text())
        data["dimensions"][0].pop("verification", None)
        # Ensure weights still sum to 1
        path = tmp_path / "no_verification.yaml"
        path.write_text(yaml.dump(data))
        report = validator.validate_file(path)
        # Should be valid but with a warning
        assert any(i.severity == "warning" and "verification" in i.field for i in report.warnings)
