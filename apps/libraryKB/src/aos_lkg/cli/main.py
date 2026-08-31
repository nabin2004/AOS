"""CLI interface for AOS Mathematical & Computational Knowledge Graph (LKG)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from aos_lkg.config import LKGConfig, LibraryConfig
from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.schema.nodes import NodeType
from aos_lkg.extractor.crawler import PackageCrawler
from aos_lkg.ontology.enrichment import enrich_knowledge_graph
from aos_lkg.storage.graph_store import GraphStore
from aos_lkg.storage.api_index import ApiIndex
from aos_lkg.storage.semantic_index import SemanticIndex
from aos_lkg.retriever.task_retriever import TaskRetriever
from aos_lkg.retriever.prompt_formatter import PromptFormatter
from aos_lkg.validator.health_report import generate_health_report
from aos_lkg.benchmark.evaluator import BenchmarkEvaluator

console = Console()

DEFAULT_CONFIG_PATH = Path("lkg_config.yaml")
DEFAULT_DATA_DIR = Path("data")


def load_configuration(config_path: Optional[Path] = None) -> LKGConfig:
    """Load configuration from file or use default."""
    target_path = config_path or DEFAULT_CONFIG_PATH
    if target_path.exists():
        try:
            return LKGConfig.from_yaml(target_path)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not parse {target_path} ({e}). Using default config.[/yellow]")
    return LKGConfig.default_config()


def build_pipeline(
    config: Optional[LKGConfig] = None,
    config_path: Optional[Path] = None,
    data_dir_override: Optional[Path] = None,
    quick: bool = False,
) -> Tuple[GraphStore, ApiIndex, SemanticIndex]:
    """Crawl configured Python libraries, enrich with math/Manim ontology, and save indices."""
    active_config = config or load_configuration(config_path)
    data_dir = data_dir_override or Path(active_config.data_dir)

    console.print(Panel(f"[bold green]Building AOS Mathematical & Computational Knowledge Graph[/bold green]\n"
                        f"[dim]Libraries configured: {len(active_config.libraries)} | Storage: {data_dir}[/dim]"))

    combined_kg = KnowledgeGraph()

    for lib in active_config.libraries:
        depth = 2 if quick else lib.max_depth
        crawler = PackageCrawler(
            max_depth=depth,
            include_submodules=True,
            extract_sources=lib.extract_sources,
        )

        console.print(f"[cyan]Introspecting[/cyan] {lib.name} (submodules: {lib.submodules or 'all'}, depth: {depth})...")
        try:
            pkg_kg = crawler.crawl_package(
                lib.name,
                target_submodules=lib.submodules,
                exclude_patterns=lib.exclude_patterns,
            )
            for node in pkg_kg.nodes.values():
                combined_kg.add_node(node)
            for edge in pkg_kg.edges:
                combined_kg.add_edge(edge)
            console.print(f"  [green]+[/green] Extracted {len(pkg_kg.nodes)} nodes from {lib.name}")
        except Exception as e:
            console.print(f"  [yellow]![/yellow] Failed crawling {lib.name}: {e}")

    console.print("[cyan]Enriching with Computational Capabilities & Manim Mappings...[/cyan]")
    enriched_kg = enrich_knowledge_graph(combined_kg)

    graph_store = GraphStore(enriched_kg)
    data_dir.mkdir(parents=True, exist_ok=True)
    graph_store.save_jsonl(data_dir / "library_graph.jsonl")

    console.print("[cyan]Building API & Semantic Indices...[/cyan]")
    api_idx = ApiIndex.from_knowledge_graph(enriched_kg)
    api_idx.save_jsonl(data_dir / "api_index.jsonl")

    sem_idx = SemanticIndex.from_knowledge_graph(enriched_kg)

    console.print(f"[bold green]Build Complete![/bold green] Total Nodes: {len(enriched_kg.nodes)}, Total Edges: {len(enriched_kg.edges)}")
    return graph_store, api_idx, sem_idx


def load_or_build_pipeline(
    data_dir: Path = DEFAULT_DATA_DIR,
    config_path: Optional[Path] = None,
) -> Tuple[GraphStore, ApiIndex, SemanticIndex]:
    """Load existing graph files or build on demand."""
    graph_path = data_dir / "library_graph.jsonl"
    if not graph_path.exists():
        return build_pipeline(config_path=config_path, data_dir_override=data_dir, quick=True)

    graph_store = GraphStore.load_jsonl(graph_path)
    api_path = data_dir / "api_index.jsonl"
    if api_path.exists():
        api_idx = ApiIndex.load_jsonl(api_path)
    else:
        api_idx = ApiIndex.from_knowledge_graph(graph_store.graph)

    sem_idx = SemanticIndex.from_knowledge_graph(graph_store.graph)
    return graph_store, api_idx, sem_idx


def cmd_build(args):
    cfg_path = Path(args.config) if args.config else None
    data_dir = Path(args.output_dir) if args.output_dir else None
    build_pipeline(config_path=cfg_path, data_dir_override=data_dir, quick=args.quick)


def cmd_add_library(args):
    cfg_path = Path(args.config) if args.config else DEFAULT_CONFIG_PATH
    config = load_configuration(cfg_path)

    submodules = [s.strip() for s in args.submodules.split(",") if s.strip()] if args.submodules else None
    config.add_library(
        name=args.library,
        submodules=submodules,
        domain=args.domain,
        max_depth=args.depth,
    )
    config.to_yaml(cfg_path)
    console.print(f"[bold green]Successfully added/updated library '{args.library}' in {cfg_path}[/bold green]")

    if args.build:
        build_pipeline(config=config, quick=args.quick)


def cmd_retrieve(args):
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR
    cfg_path = Path(args.config) if args.config else None
    graph_store, api_idx, sem_idx = load_or_build_pipeline(data_dir, config_path=cfg_path)

    retriever = TaskRetriever(graph_store, api_idx, sem_idx)
    slice_data = retriever.retrieve(args.query)
    formatted = PromptFormatter.format_llm_context(slice_data)

    console.print(Panel(f"[bold magenta]LLM Slice for Task:[/bold magenta] {args.query}"))
    console.print(formatted)


def resolve_inspect_node(target: str, graph: KnowledgeGraph, api_idx: ApiIndex, sem_idx: SemanticIndex):
    """Hierarchically resolve a user inspection target to the most accurate graph node."""
    target_clean = target.strip()

    # 1. Exact Node ID match
    node = graph.get_node(target_clean)
    if node:
        return node

    # 2. Check standard ID prefixes
    prefixes = [
        "lib:",
        "mod:",
        "manim:",
        "cap:",
        "pattern:",
        "rule:",
        "concept:",
        "algo:",
        "cls:",
        "fn:",
        "example:",
    ]
    for p in prefixes:
        candidate_id = f"{p}{target_clean}"
        candidate = graph.get_node(candidate_id)
        if candidate:
            return candidate

    # 3. Exact match on qualified_name
    for n in graph.nodes.values():
        if hasattr(n, "qualified_name") and n.qualified_name == target_clean:
            return n

    # 4. Exact match on name, prioritizing high-level entities (Library -> Module -> ManimMapping -> Capability -> Concept -> Algorithm -> Class -> Function)
    type_priority = [
        NodeType.LIBRARY,
        NodeType.MODULE,
        NodeType.MANIM_MAPPING,
        NodeType.CAPABILITY,
        NodeType.CONCEPT,
        NodeType.ALGORITHM,
        NodeType.CLASS,
        NodeType.FUNCTION,
    ]
    by_type_matches: dict = {}
    for n in graph.nodes.values():
        if n.name.lower() == target_clean.lower():
            by_type_matches.setdefault(n.type, []).append(n)
        elif getattr(n, "pattern_name", None) and n.pattern_name.lower() == target_clean.lower():
            by_type_matches.setdefault(n.type, []).append(n)

    for ptype in type_priority:
        if ptype in by_type_matches and by_type_matches[ptype]:
            return by_type_matches[ptype][0]

    # 5. Check API index (by qualname or short name)
    entry = api_idx.get_by_qualname(target_clean)
    if entry:
        node = graph.get_node(entry.id)
        if node:
            return node

    name_matches = api_idx.search_by_name(target_clean)
    if name_matches:
        node = graph.get_node(name_matches[0].id)
        if node:
            return node

    # 6. Fallback to BM25 Semantic Index search
    results = sem_idx.search(target_clean, top_k=1)
    if results:
        return graph.get_node(results[0].node_id)

    return None


def cmd_inspect(args):
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR
    cfg_path = Path(args.config) if args.config else None
    graph_store, api_idx, sem_idx = load_or_build_pipeline(data_dir, config_path=cfg_path)

    node = resolve_inspect_node(args.target, graph_store.graph, api_idx, sem_idx)

    if not node:
        console.print(f"[red]Error: Node '{args.target}' not found.[/red]")
        return

    console.print(Panel(f"[bold cyan]Node Inspection:[/bold cyan] {node.name} ({node.id})"))
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Property", style="dim", width=20)
    table.add_column("Value")

    for k, v in node.model_dump().items():
        if k not in ("docstring", "source_code", "example_code"):
            table.add_row(k, str(v))
    console.print(table)

    out_edges = graph_store.graph.get_outgoing_edges(node.id)
    if out_edges:
        console.print("\n[bold yellow]Outgoing Edges:[/bold yellow]")
        for e in out_edges:
            console.print(f"  -> [{e.type.value}] {e.target}")

    in_edges = graph_store.graph.get_incoming_edges(node.id)
    if in_edges:
        console.print("\n[bold yellow]Incoming Edges:[/bold yellow]")
        for e in in_edges:
            console.print(f"  <- [{e.type.value}] {e.source}")


def cmd_verify(args):
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR
    cfg_path = Path(args.config) if args.config else None
    graph_store, _, _ = load_or_build_pipeline(data_dir, config_path=cfg_path)

    console.print("[cyan]Running runtime verification suite across live packages...[/cyan]")
    report = generate_health_report(graph_store.graph, sample_api_limit=args.limit)

    console.print(report.to_markdown())


def cmd_stats(args):
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR
    cfg_path = Path(args.config) if args.config else None
    graph_store, _, _ = load_or_build_pipeline(data_dir, config_path=cfg_path)

    table = Table(title="AOS Knowledge Graph Statistics", show_header=True)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Count", style="green")

    table.add_row("Total Nodes", str(len(graph_store.graph.nodes)))
    table.add_row("Total Edges", str(len(graph_store.graph.edges)))

    type_counts = {}
    for n in graph_store.graph.nodes.values():
        t = n.type.value if hasattr(n.type, "value") else str(n.type)
        type_counts[t] = type_counts.get(t, 0) + 1

    for t, c in sorted(type_counts.items()):
        table.add_row(f"Node Type: {t}", str(c))

    console.print(table)


def cmd_benchmark(args):
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR
    cfg_path = Path(args.config) if args.config else None
    graph_store, api_idx, sem_idx = load_or_build_pipeline(data_dir, config_path=cfg_path)

    retriever = TaskRetriever(graph_store, api_idx, sem_idx)
    evaluator = BenchmarkEvaluator(retriever)

    console.print("[bold cyan]Running AOS Mathematical Animation Benchmark Suite...[/bold cyan]\n")
    summary = evaluator.evaluate_all()

    table = Table(title="AOS-LKG Mathematical Benchmark Results", show_header=True, header_style="bold magenta")
    table.add_column("Test ID", style="dim", width=22)
    table.add_column("Query", width=38)
    table.add_column("Cap", justify="center", width=5)
    table.add_column("API", justify="center", width=5)
    table.add_column("Dim", justify="center", width=5)
    table.add_column("Retrieved API", style="cyan")

    for ev in summary.test_evaluations:
        c_mark = "[green]OK[/green]" if ev.capability_passed else "[red]FAIL[/red]"
        a_mark = "[green]OK[/green]" if ev.api_passed else "[red]FAIL[/red]"
        d_mark = "[green]OK[/green]" if ev.dimension_passed else "[yellow]?[/yellow]"
        table.add_row(
            ev.test_id,
            ev.query[:35] + ("..." if len(ev.query) > 35 else ""),
            c_mark,
            a_mark,
            d_mark,
            ev.retrieved_api or "[dim]None[/dim]",
        )

    console.print(table)

    summary_panel = Panel(
        f"[bold]Total Benchmark Queries[/bold]: {summary.total_tests}\n"
        f"[bold green]Top-1 Capability Accuracy[/bold green]: {summary.capability_accuracy}%\n"
        f"[bold green]Top-1 Primary API Accuracy[/bold green]: {summary.api_accuracy}%\n"
        f"[bold green]Dimensionality Accuracy[/bold green]: {summary.dimension_accuracy}%\n"
        f"[bold green]Manim Mapping Accuracy[/bold green]: {summary.manim_accuracy}%\n"
        f"-----------------------------------------\n"
        f"[bold cyan]Overall Benchmark Score[/bold cyan]: {summary.overall_benchmark_score}%",
        title="[bold yellow]Benchmark Summary Scorecard[/bold yellow]",
        border_style="green" if summary.overall_benchmark_score >= 85.0 else "yellow",
    )
    console.print(summary_panel)


def main():
    parser = argparse.ArgumentParser(
        prog="aos-lkg",
        description="AOS Mathematical & Computational Knowledge Graph (LKG) for Manim Code Generation",
    )
    parser.add_argument("--config", "-c", help="Path to YAML configuration file (default: lkg_config.yaml)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Crawl libraries from config and build the knowledge graph")
    p_build.add_argument("--output-dir", "-o", help="Output directory for graph files")
    p_build.add_argument("--quick", action="store_true", help="Quick mode (reduced depth)")
    p_build.add_argument("--config", "-c", help="Custom YAML config path")
    p_build.set_defaults(func=cmd_build)

    # add-library
    p_add = subparsers.add_parser("add-library", help="Add a Python library to lkg_config.yaml")
    p_add.add_argument("library", help="Python package name (e.g. 'sklearn', 'cv2', 'jax')")
    p_add.add_argument("--submodules", "-s", help="Comma-separated submodules (e.g. 'cluster,decomposition')")
    p_add.add_argument("--domain", "-d", help="Mathematical domain")
    p_add.add_argument("--depth", type=int, default=3, help="Max crawl depth")
    p_add.add_argument("--build", "-b", action="store_true", help="Immediately rebuild the knowledge graph")
    p_add.add_argument("--quick", action="store_true", help="Quick build mode")
    p_add.add_argument("--config", "-c", help="Custom YAML config path")
    p_add.set_defaults(func=cmd_add_library)

    # retrieve
    p_ret = subparsers.add_parser("retrieve", help="Retrieve minimal LLM context slice for a task")
    p_ret.add_argument("query", help="Animation task query (e.g. 'Animate Newton method for sqrt(2)')")
    p_ret.add_argument("--data-dir", "-d", help="Data directory containing graph files")
    p_ret.add_argument("--config", "-c", help="Custom YAML config path")
    p_ret.set_defaults(func=cmd_retrieve)

    # inspect
    p_ins = subparsers.add_parser("inspect", help="Inspect a specific API, capability, or node")
    p_ins.add_argument("target", help="Node ID or API name (e.g. 'scipy.optimize.brentq')")
    p_ins.add_argument("--data-dir", "-d", help="Data directory")
    p_ins.add_argument("--config", "-c", help="Custom YAML config path")
    p_ins.set_defaults(func=cmd_inspect)

    # verify
    p_ver = subparsers.add_parser("verify", help="Run live self-verification suite")
    p_ver.add_argument("--limit", type=int, default=50, help="Sample limit for API checks")
    p_ver.add_argument("--data-dir", "-d", help="Data directory")
    p_ver.add_argument("--config", "-c", help="Custom YAML config path")
    p_ver.set_defaults(func=cmd_verify)

    # stats
    p_stat = subparsers.add_parser("stats", help="Display graph metrics and statistics")
    p_stat.add_argument("--data-dir", "-d", help="Data directory")
    p_stat.add_argument("--config", "-c", help="Custom YAML config path")
    p_stat.set_defaults(func=cmd_stats)

    # benchmark
    p_bm = subparsers.add_parser("benchmark", help="Run automated benchmark evaluation across canonical animation queries")
    p_bm.add_argument("--data-dir", "-d", help="Data directory")
    p_bm.add_argument("--config", "-c", help="Custom YAML config path")
    p_bm.set_defaults(func=cmd_benchmark)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
