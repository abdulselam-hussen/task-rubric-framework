"""Data models for the Task & Rubric Design Framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Milestone:
    id: int
    description: str
    optional: bool = False


@dataclass
class AcceptanceCriterion:
    id: str
    criterion: str
    automated: bool = True


@dataclass
class HiddenEdgeCase:
    id: str
    description: str
    input: Any
    expected: Any


@dataclass
class Task:
    """Parsed representation of a task YAML file."""

    id: str
    version: str
    name: str
    description: str
    user_intent: str
    milestones: list[Milestone]
    acceptance_criteria: list[AcceptanceCriterion]
    category: str = "debugging"
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)
    repo_url: str = ""
    repo_ref: str = "main"
    hidden_edge_cases: list[HiddenEdgeCase] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)
    eval_commands: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    reference_solution: str = ""
    rubric: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        milestones = [Milestone(**m) for m in data.get("milestones", [])]
        acceptance_criteria = [
            AcceptanceCriterion(**ac) for ac in data.get("acceptance_criteria", [])
        ]
        hidden_edge_cases = [
            HiddenEdgeCase(**hec) for hec in data.get("hidden_edge_cases", [])
        ]
        return cls(
            id=data["id"],
            version=data["version"],
            name=data["name"],
            description=data["description"],
            user_intent=data["user_intent"],
            milestones=milestones,
            acceptance_criteria=acceptance_criteria,
            category=data.get("category", "debugging"),
            difficulty=data.get("difficulty", "medium"),
            tags=data.get("tags", []),
            repo_url=data.get("repo_url", ""),
            repo_ref=data.get("repo_ref", "main"),
            hidden_edge_cases=hidden_edge_cases,
            setup_commands=data.get("setup_commands", []),
            eval_commands=data.get("eval_commands", []),
            expected_artifacts=data.get("expected_artifacts", []),
            timeout_seconds=data.get("timeout_seconds", 300),
            reference_solution=data.get("reference_solution", ""),
            rubric=data.get("rubric", ""),
        )


@dataclass
class RubricDimension:
    id: str
    name: str
    category: str
    criterion: str
    weight: float
    verification: str = ""
    disqualifying: bool = False


@dataclass
class RemovedCriterion:
    criterion: str
    reason: str


@dataclass
class Rubric:
    """Parsed representation of a rubric YAML file."""

    task_id: str
    version: str
    dimensions: list[RubricDimension]
    description: str = ""
    difficulty_notes: str = ""
    removed_criteria: list[RemovedCriterion] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rubric":
        dimensions = [RubricDimension(**d) for d in data.get("dimensions", [])]
        removed = [RemovedCriterion(**r) for r in data.get("removed_criteria", [])]
        return cls(
            task_id=data["task_id"],
            version=data["version"],
            dimensions=dimensions,
            description=data.get("description", ""),
            difficulty_notes=data.get("difficulty_notes", ""),
            removed_criteria=removed,
        )

    @property
    def total_weight(self) -> float:
        return sum(d.weight for d in self.dimensions)


@dataclass
class ValidationIssue:
    severity: str   # "error" | "warning"
    field: str
    message: str


@dataclass
class ValidationReport:
    path: str
    kind: str          # "task" | "rubric"
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]
