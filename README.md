# Task & Rubric Design Framework

A Python framework for authoring, validating, and managing evaluation tasks and binary scoring rubrics for agentic coding systems. Provides structured templates for user intent, milestones, acceptance criteria, hidden edge cases, and reference solutions; plus binary rubrics covering functionality, test results, security, and requirement compliance.

**Stack:** Python · YAML · JSON Schema · Click

---

## Features

- **Structured task templates** covering user intent, ordered milestones, binary acceptance criteria, and hidden edge cases not disclosed to the agent.
- **Binary rubrics** — every dimension is either pass (full weight) or fail (0); no partial credit, no subjectivity.
- **Five rubric categories:** functionality, test_results, security, requirements, code_quality.
- **Disqualifying dimensions** — a single critical failure (e.g. all tests pass) scores the entire submission 0.
- **Calibration trail** — each rubric records model attempts, removed ambiguous criteria, and difficulty notes.
- **JSON Schema validation** — schema errors are caught before any task runs.
- **Semantic validation** — sequential milestone IDs, unique criteria IDs, weights summing to 1.0, missing verification commands.
- **CLI** — `rubric validate`, `rubric new`, `rubric score`.
- **23 unit tests** — models, TaskValidator, and RubricValidator all exercised against the example files.

---

## Project Layout

```
task-rubric-framework/
├── src/rubric/
│   ├── __init__.py
│   ├── cli.py          # Click CLI: validate, new, score
│   ├── models.py       # Task, Rubric, ValidationReport dataclasses
│   └── validator.py    # TaskValidator, RubricValidator (schema + semantic)
├── schemas/
│   ├── task.schema.json
│   └── rubric.schema.json
├── templates/
│   ├── task_template.yaml
│   └── rubric_template.yaml
├── examples/
│   ├── tasks/
│   │   ├── fix-null-dereference-001.yaml
│   │   └── add-jwt-auth-002.yaml
│   ├── rubrics/
│   │   ├── fix-null-dereference-001.yaml
│   │   └── add-jwt-auth-002.yaml
│   └── solutions/
│       ├── fix-null-dereference-001.py
│       └── add-jwt-auth-002.py
├── tests/
│   └── test_framework.py
└── pyproject.toml
```

---

## Quick Start

### 1 — Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2 — Create a task from the template

```bash
rubric new task --output my_task.yaml
# Edit my_task.yaml, then:
rubric validate task my_task.yaml
```

### 3 — Create a rubric from the template

```bash
rubric new rubric --output my_rubric.yaml
# Edit my_rubric.yaml, then:
rubric validate rubric my_rubric.yaml
```

### 4 — Validate all examples at once

```bash
rubric validate all examples/
```

Output:
```
Scanning examples/ …
  ✓ VALID  examples/tasks/fix-null-dereference-001.yaml
  ✓ VALID  examples/tasks/add-jwt-auth-002.yaml
  ✓ VALID  examples/rubrics/fix-null-dereference-001.yaml
  ✓ VALID  examples/rubrics/add-jwt-auth-002.yaml

4/4 file(s) valid
```

### 5 — Inspect a rubric's weight breakdown

```bash
rubric score examples/rubrics/fix-null-dereference-001.yaml
```

Output:
```
Rubric: fix-null-dereference-001.yaml  (task: fix-null-dereference-001)
----------------------------------------------------------------------

  CODE_QUALITY  (10% total)
    d-qual-1        5%  No new linting errors
    d-qual-2        5%  Fix is minimal (no unrelated changes)

  FUNCTIONALITY  (60% total)
    d-func-1       30%  All tests pass [DISQUALIFYING]
    d-func-2       20%  None input returns empty list
    d-func-3       10%  Empty dict input returns empty list
  …
----------------------------------------------------------------------
  Total weight: 1.0000
```

---

## Task YAML Schema

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✓ | Unique kebab-case identifier |
| `version` | ✓ | Schema version (`"1.0"`) |
| `name` | ✓ | Short task name |
| `description` | ✓ | Full problem statement shown to the agent |
| `user_intent` | ✓ | One-sentence goal from the user's perspective |
| `milestones` | ✓ | Ordered steps (`id` must be sequential from 1) |
| `acceptance_criteria` | ✓ | Binary observable conditions; IDs must be unique |
| `category` | | `debugging` \| `feature` \| `refactor` \| `security` \| `infrastructure` \| `maintenance` |
| `difficulty` | | `easy` \| `medium` \| `hard` |
| `hidden_edge_cases` | | Not shown to the agent; used for depth scoring |
| `eval_commands` | | Commands run by the harness |
| `expected_artifacts` | | Files that must exist after evaluation |
| `reference_solution` | | Path to the reference solution (relative) |
| `rubric` | | Path to the companion rubric (relative) |

---

## Rubric YAML Schema

| Field | Required | Description |
|-------|----------|-------------|
| `task_id` | ✓ | Must match the task's `id` |
| `version` | ✓ | Schema version |
| `dimensions` | ✓ | List of binary scoring dimensions |
| `dimensions[].category` | ✓ | `functionality` \| `test_results` \| `security` \| `requirements` \| `code_quality` |
| `dimensions[].weight` | ✓ | All weights must sum to `1.0` |
| `dimensions[].verification` | | Shell command used to verify the dimension |
| `dimensions[].disqualifying` | | If `true`, failure scores the submission 0 |
| `difficulty_notes` | | How difficulty was calibrated |
| `removed_criteria` | | Criteria removed with reasons |

---

## Validation Checks

### Task

| Check | Type | Description |
|-------|------|-------------|
| JSON Schema | error | Required fields present, correct types, valid enums |
| Milestone IDs sequential | error | IDs must be 1, 2, 3, … |
| Acceptance criteria IDs unique | error | No duplicate `id` values |
| Description length | warning | Fewer than 20 words |
| Rubric file exists | warning | Path in `rubric` field resolves |
| Reference solution exists | warning | Path in `reference_solution` field resolves |

### Rubric

| Check | Type | Description |
|-------|------|-------------|
| JSON Schema | error | Required fields, valid category enum |
| Weights sum to 1.0 | error | Total must be within ±0.01 |
| Dimension IDs unique | error | No duplicate `id` values |
| Functionality dimension present | warning | At least one `functionality` dimension recommended |
| Verification command present | warning | Per-dimension check |

---

## Running Tests

```bash
pytest tests/ -v
```

```
23 passed in 0.16s
```

---

## Designing Good Tasks

**User intent first.** Write the one-sentence user_intent before anything else. If you cannot express it in one sentence, the task scope is too broad.

**Make acceptance criteria observable and automatable.** "Code is readable" fails; "flake8 src/ exits 0" passes.

**Add hidden edge cases after writing the task.** Think about None inputs, empty collections, wrong types, boundary values, and missing keys. Do not disclose them in the description.

**Tune difficulty by running model attempts.** If a frontier model passes on the first attempt, add a hidden edge case or tighten a rubric dimension. If no model ever passes, remove an ambiguous criterion and document it in `removed_criteria`.

**Keep rubric dimensions binary.** Partial credit introduces subjectivity. If a dimension is too coarse, split it into two binary ones.
