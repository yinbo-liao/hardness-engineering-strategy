"""
Hardness Plugin CLI — governance, evaluation, planning for Claude Code.

Commands:
  hardness init     Initialize .hardness/ config in current directory
  hardness check    Run constraint checks against project code
  hardness evaluate Run multi-dimensional quality evaluation
  hardness plan     DAG task decomposition guidance
  hardness bench    Run performance benchmarks
  hardness metrics  Show/export session metrics
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="hardness",
    help="Hardness Engineering: governance and evaluation for Claude Code",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    path: str = typer.Option(".", help="Project root directory"),
    scope: str = typer.Option("general", help="Project scope: api, ui, db, infra, test, security"),
    force: bool = typer.Option(False, help="Overwrite existing config"),
    if_missing: bool = typer.Option(False, help="Only create if config doesn't exist"),
):
    """Initialize .hardness/ configuration."""
    from hardness_plugin.project_config import DEFAULT_CONFIG
    import yaml

    project_root = Path(path).resolve()
    hardness_dir = project_root / ".hardness"
    config_file = hardness_dir / "config.yaml"

    if config_file.exists():
        if if_missing:
            return  # Silent no-op
        if not force:
            console.print(f"[yellow]Config exists at {config_file}[/yellow]")
            return

    hardness_dir.mkdir(parents=True, exist_ok=True)

    config = dict(DEFAULT_CONFIG)
    config["project"]["name"] = project_root.name
    config["project"]["scope"] = scope

    config_file.write_text(yaml.dump(config, default_flow_style=False))
    console.print(f"[green]Created {config_file}[/green]")


@app.command()
def check(
    path: str = typer.Option(".", help="Project root directory"),
    scope: Optional[str] = typer.Option(None, help="Override project scope"),
    files: Optional[str] = typer.Option(None, help="Comma-separated file paths to check"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for machine parsing"),
):
    """Run constraint checks against the project code."""
    from hardness_plugin.governance import Governance
    from hardness_plugin.project_config import load_project_config, find_project_root

    project_root = find_project_root(path) if path == "." else Path(path).resolve()
    config = load_project_config(project_root)
    gov = Governance()
    task_scope = scope or config.get("project", {}).get("scope", "general")

    file_list = []
    if files:
        file_list = [Path(f.strip()) for f in files.split(",")]
    else:
        exclude = {".git", "node_modules", "__pycache__", ".venv", "venv", ".hardness", ".claude"}
        for ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".sql"):
            for f in project_root.rglob(f"*{ext}"):
                if not any(p in f.parts for p in exclude):
                    file_list.append(f)

    all_violations = []
    checked = 0
    for fp in file_list:
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        checked += 1
        result = gov.check_constraint(
            action="write_file",
            params={"file_path": str(fp), "content": content},
            task_scope=task_scope,
        )
        for v in result.get("violations", []):
            v["file"] = str(fp)
            all_violations.append(v)

    output = {
        "passed": len(all_violations) == 0,
        "files_checked": checked,
        "violations_count": len(all_violations),
        "violations": all_violations,
    }

    if json_output:
        console.print(json.dumps(output, indent=2))
    else:
        if not all_violations:
            console.print(f"[green]No violations in {checked} file(s)[/green]")
        else:
            for v in all_violations:
                sev = v.get("severity", "low")
                color = {"critical": "red", "high": "yellow", "medium": "blue"}.get(sev, "white")
                console.print(
                    f"[{color}][{sev.upper()}] {v['message']}[/{color}] "
                    f"[dim]in {v.get('file', '?')}[/dim]"
                )
            console.print(f"\n[yellow]{len(all_violations)} violation(s) in {checked} file(s)[/yellow]")

    if all_violations:
        raise typer.Exit(1)


@app.command()
def evaluate(
    path: str = typer.Option(".", help="File or directory to evaluate"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Run multi-dimensional quality evaluation on code files."""
    from hardness_plugin.evaluator import evaluate_code_quality

    target = Path(path).resolve()
    if target.is_file():
        py_files = [target] if target.suffix == ".py" else []
    else:
        exclude = {".git", "node_modules", "__pycache__", ".venv", "venv", ".hardness", ".claude"}
        py_files = [f for f in target.rglob("*.py") if not any(p in f.parts for p in exclude)]

    if not py_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    results = []
    passed_count = 0
    for f in py_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        r = evaluate_code_quality(str(f), content)
        results.append(r)
        if r["passed"]:
            passed_count += 1

    overall_passed = passed_count == len(results)

    if json_output:
        console.print(json.dumps({
            "passed": overall_passed,
            "files_evaluated": len(results),
            "files_passed": passed_count,
            "results": results,
        }, indent=2))
    else:
        table = Table(title=f"Evaluation: {passed_count}/{len(results)} files passed")
        table.add_column("File", style="cyan", max_width=50)
        table.add_column("Score", justify="right")
        table.add_column("Tests", justify="center")
        table.add_column("Types", justify="center")
        table.add_column("Lint", justify="center")
        table.add_column("Security", justify="center")
        table.add_column("Status")

        for r in results:
            dims = r["dimensions"]
            table.add_row(
                r["file"][-48:],
                f"{r['weighted_score']:.1%}",
                "PASS" if dims["unit_tests"]["passed"] else "FAIL",
                "PASS" if dims["type_check"]["passed"] else "FAIL",
                "PASS" if dims["lint"]["passed"] else "FAIL",
                "PASS" if dims["security_scan"]["passed"] else "FAIL",
                "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]",
            )
        console.print(table)

    if not overall_passed:
        raise typer.Exit(1)


@app.command()
def plan(
    task_description: str = typer.Argument(..., help="Task description to decompose"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Generate DAG task decomposition guidance."""
    guide = {
        "task_description": task_description,
        "suggested_approach": {
            "step_1": "Identify independent sub-tasks",
            "step_2": "Determine dependencies between sub-tasks",
            "step_3": "Order sub-tasks using topological sort",
            "step_4": "Execute in dependency order with checkpoints",
        },
        "code_example": {
            "imports": "from hardness_plugin.planner import TaskPlanner, TaskNode",
            "usage": (
                "planner = TaskPlanner()\n"
                "planner.add_task(TaskNode(id='1', description='Step one'))\n"
                "planner.add_task(TaskNode(id='2', description='Step two', deps=['1']))\n"
                "order = planner.get_execution_order()  # ['1', '2']"
            ),
        },
    }

    if json_output:
        console.print(json.dumps(guide, indent=2))
    else:
        console.print(Panel.fit(
            f"[bold]Task:[/bold] {task_description}\n\n"
            "Decompose into a DAG of sub-tasks:\n"
            "1. Identify independent units of work\n"
            "2. Define explicit dependencies\n"
            "3. Use TaskPlanner for topological ordering\n"
            "4. Execute with checkpoints for recovery",
            title="Task Planning Guide",
        ))
        console.print("\n[dim]Usage:[/dim]")
        console.print("  from hardness_plugin.planner import TaskPlanner, TaskNode")
        console.print("  planner = TaskPlanner()")
        console.print("  planner.add_task(TaskNode(id='step-1', description='...'))")


@app.command()
def bench(
    iterations: int = typer.Option(10, help="Number of benchmark iterations"),
    output: Optional[str] = typer.Option(None, help="Output JSON file"),
):
    """Run performance benchmarks on core modules."""
    import asyncio

    from hardness_plugin.benchmarks import BenchmarkRunner
    from hardness_plugin.governance import Governance
    from hardness_plugin.token_optimizer import TokenOptimizer

    runner = BenchmarkRunner()
    console.print("[bold]Hardness Performance Benchmarks[/bold]\n")

    async def run():
        results = {}

        # Constraint check benchmark
        gov = Governance()

        def run_constraint():
            return gov.check_constraint(
                "write_file",
                {"content": "requests.get('http://ex.com')\npassword='secret'", "file_path": "test.py"},
                "api",
            )

        r1 = await runner.benchmark("constraint_check", run_constraint, iterations=iterations)
        results["constraint_check"] = r1.to_dict()
        console.print(f"  Constraint check:  p50={r1.p50_time_ms:.2f}ms  p95={r1.p95_time_ms:.2f}ms  mean={r1.avg_time_ms:.2f}ms")

        # Token optimizer benchmark
        opt = TokenOptimizer(8000)
        sample = {"layers": {"global": {"content": "x" * 5000, "token_estimate": 1250}}}

        def run_optimize():
            return opt.optimize_context(sample, "api", "balanced")

        r2 = await runner.benchmark("token_optimizer", run_optimize, iterations=iterations)
        results["token_optimizer"] = r2.to_dict()
        console.print(f"  Token optimizer:   p50={r2.p50_time_ms:.2f}ms  p95={r2.p95_time_ms:.2f}ms  mean={r2.avg_time_ms:.2f}ms")

        # Summary table
        table = Table(title="Performance Summary")
        table.add_column("Benchmark", style="cyan")
        table.add_column("p50 (ms)", justify="right")
        table.add_column("p95 (ms)", justify="right")
        table.add_column("mean (ms)", justify="right")

        for name, r in results.items():
            table.add_row(name, f"{r['p50']:.2f}", f"{r['p95']:.2f}", f"{r['mean']:.2f}")

        console.print()
        console.print(table)

        if output:
            Path(output).write_text(json.dumps(results, indent=2))
            console.print(f"\n[dim]Results saved to {output}[/dim]")

    asyncio.run(run())


@app.command()
def metrics(
    increment: Optional[str] = typer.Option(None, help="Increment a named counter"),
    render: bool = typer.Option(False, help="Render Prometheus-format metrics"),
    reset: bool = typer.Option(False, help="Reset all counters"),
):
    """Show or manage session metrics."""
    from hardness_plugin.metrics import MetricsCollector

    collector = MetricsCollector()

    if increment:
        collector.counter(increment)
        console.print(f"[dim]Incremented: {increment}[/dim]")

    if render:
        console.print(collector.render_prometheus())
    elif not increment:
        all_m = collector.get_all()
        if all_m:
            for m in all_m:
                console.print(f"  {m.name}: {m.value}")
        else:
            console.print("[dim]No metrics recorded[/dim]")

    if reset:
        collector._gauges.clear()
        collector._counters.clear()
        collector._histograms.clear()
        console.print("[dim]Metrics reset[/dim]")


if __name__ == "__main__":
    app()
