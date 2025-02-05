"""CLI for the Task & Rubric Design Framework.

Commands
--------
  rubric validate task path/to/task.yaml
  rubric validate rubric path/to/rubric.yaml
  rubric validate all path/to/examples/
  rubric new task --output path/to/new_task.yaml
  rubric new rubric --output path/to/new_rubric.yaml
  rubric score path/to/rubric.yaml
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click

from .validator import RubricValidator, TaskValidator
from .models import ValidationReport


_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


# ─────────────────────────────────────────────────────────────────────────────

def _print_report(report: ValidationReport, *, verbose: bool = False) -> None:
    status = click.style("✓ VALID", fg="green") if report.valid else click.style("✗ INVALID", fg="red")
    click.echo(f"  {status}  {report.path}")

    for issue in report.issues:
        colour = "red" if issue.severity == "error" else "yellow"
        icon = "✗" if issue.severity == "error" else "⚠"
        click.echo(
            f"    {click.style(icon, fg=colour)} [{issue.field}] {issue.message}"
        )

    if verbose and report.valid and not report.issues:
        click.echo("    (no issues)")


# ─────────────────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version="0.1.0", prog_name="rubric")
def main() -> None:
    """Task & Rubric Design Framework – create and validate evaluation tasks."""


# ─────────────────────────────────────────────────────────────────────────────
# rubric validate
# ─────────────────────────────────────────────────────────────────────────────

@main.group()
def validate() -> None:
    """Validate task or rubric files."""


@validate.command("task")
@click.argument("path", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True)
def validate_task(path: str, verbose: bool) -> None:
    """Validate one or more task YAML files."""
    p = Path(path)
    files = sorted(p.glob("*.yaml")) + sorted(p.glob("*.yml")) if p.is_dir() else [p]
    if not files:
        click.echo(f"No YAML files found in {path}", err=True)
        sys.exit(1)

    validator = TaskValidator()
    failed = 0
    for f in files:
        report = validator.validate_file(f)
        _print_report(report, verbose=verbose)
        if not report.valid:
            failed += 1

    _exit_summary(len(files), failed)


@validate.command("rubric")
@click.argument("path", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True)
def validate_rubric(path: str, verbose: bool) -> None:
    """Validate one or more rubric YAML files."""
    p = Path(path)
    files = sorted(p.glob("*.yaml")) + sorted(p.glob("*.yml")) if p.is_dir() else [p]
    if not files:
        click.echo(f"No YAML files found in {path}", err=True)
        sys.exit(1)

    validator = RubricValidator()
    failed = 0
    for f in files:
        report = validator.validate_file(f)
        _print_report(report, verbose=verbose)
        if not report.valid:
            failed += 1

    _exit_summary(len(files), failed)


@validate.command("all")
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-v", "--verbose", is_flag=True)
def validate_all(directory: str, verbose: bool) -> None:
    """Validate all tasks and rubrics found under DIRECTORY."""
    base = Path(directory)
    task_files = list(base.rglob("*.yaml")) + list(base.rglob("*.yml"))

    task_validator = TaskValidator()
    rubric_validator = RubricValidator()
    failed = 0

    click.echo(f"Scanning {base} …")
    for f in sorted(task_files):
        rel = f.relative_to(base)
        # Heuristic: files under rubrics/ are rubrics, others are tasks
        if "rubric" in f.stem or "rubrics" in str(rel):
            validator = rubric_validator  # type: ignore[assignment]
        else:
            validator = task_validator
        report = validator.validate_file(f)  # type: ignore[assignment]
        _print_report(report, verbose=verbose)
        if not report.valid:
            failed += 1

    _exit_summary(len(task_files), failed)


# ─────────────────────────────────────────────────────────────────────────────
# rubric new
# ─────────────────────────────────────────────────────────────────────────────

@main.group("new")
def new() -> None:
    """Create a new task or rubric from the template."""


@new.command("task")
@click.option(
    "--output", "-o",
    default="new_task.yaml",
    show_default=True,
    help="Output file path.",
)
def new_task(output: str) -> None:
    """Create a new task YAML from the template."""
    src = _TEMPLATES_DIR / "task_template.yaml"
    dst = Path(output)
    if dst.exists():
        click.confirm(f"{dst} already exists. Overwrite?", abort=True)
    shutil.copy(src, dst)
    click.echo(f"Task template written to {dst}")
    click.echo("Edit the file and run:  rubric validate task " + str(dst))


@new.command("rubric")
@click.option(
    "--output", "-o",
    default="new_rubric.yaml",
    show_default=True,
    help="Output file path.",
)
def new_rubric(output: str) -> None:
    """Create a new rubric YAML from the template."""
    src = _TEMPLATES_DIR / "rubric_template.yaml"
    dst = Path(output)
    if dst.exists():
        click.confirm(f"{dst} already exists. Overwrite?", abort=True)
    shutil.copy(src, dst)
    click.echo(f"Rubric template written to {dst}")
    click.echo("Edit the file and run:  rubric validate rubric " + str(dst))


# ─────────────────────────────────────────────────────────────────────────────
# rubric score   (show dimension breakdown)
# ─────────────────────────────────────────────────────────────────────────────

@main.command("score")
@click.argument("rubric_path", type=click.Path(exists=True))
def score(rubric_path: str) -> None:
    """Show the weight breakdown of a rubric file."""
    from .validator import _load_yaml
    from .models import Rubric

    path = Path(rubric_path)
    try:
        data = _load_yaml(path)
        rubric = Rubric.from_dict(data)
    except Exception as exc:
        click.echo(f"Error loading {rubric_path}: {exc}", err=True)
        sys.exit(1)

    click.echo(f"\nRubric: {path.name}  (task: {rubric.task_id})")
    click.echo("-" * 70)

    by_category: dict[str, list] = {}
    for dim in rubric.dimensions:
        by_category.setdefault(dim.category, []).append(dim)

    for cat, dims in sorted(by_category.items()):
        cat_weight = sum(d.weight for d in dims)
        click.echo(f"\n  {click.style(cat.upper(), bold=True)}  ({cat_weight:.0%} total)")
        for dim in dims:
            disq_flag = click.style(" [DISQUALIFYING]", fg="red") if dim.disqualifying else ""
            click.echo(f"    {dim.id:<15} {dim.weight:.0%}  {dim.name}{disq_flag}")

    click.echo("-" * 70)
    click.echo(f"  Total weight: {rubric.total_weight:.4f}")
    click.echo()


# ─────────────────────────────────────────────────────────────────────────────

def _exit_summary(total: int, failed: int) -> None:
    passed = total - failed
    click.echo(f"\n{passed}/{total} file(s) valid")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
