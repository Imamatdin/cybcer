#!/usr/bin/env python3
import argparse
import os
import sys
import time
from rich.console import Console
from orchestrator import CerebrasAttacker
from blue_team import BlueTeamAnalyzer, print_blue_team_analysis
from attack_graph import AttackGraphGenerator, print_attack_graph
from genome_analysis import SecurityGenomeAnalyzer, print_genome_analysis
from benchmark import BenchmarkHarness, print_benchmark
from json_export import generate_json_report, save_json_report, print_json_summary
from executive_summary import generate_executive_summary, print_executive_summary


# Load .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")
console = Console()

def main():
    parser = argparse.ArgumentParser(
        description="Cerebras Red Team Simulator - Autonomous AI Penetration Testing"
    )
    parser.add_argument(
        "--target", "-t",
        required=True,
        help="Target URL to attack (e.g., http://localhost:5000)"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=os.environ.get("CEREBRAS_API_KEY"),
        help="Cerebras API key (or set CEREBRAS_API_KEY env var)"
    )
    parser.add_argument(
        "--max-steps", "-s",
        type=int,
        default=20,
        help="Maximum attack steps (default: 20)"
    )
    parser.add_argument(
        "--model", "-m",
        default="llama3.1-8b",
        help="Cerebras model to use"
    )
    parser.add_argument(
        "--skip-genome",
        
        action="store_true",
        help="Skip genome analysis after attack"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run speed benchmark after attack"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Generate JSON report file"
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with code 1 if critical findings found (for CI/CD)"
    )
    parser.add_argument(
        "--allowed-hosts",
        type=str,
        default=None,
        help="Comma-separated list of allowed target hosts (safety check)"
    )

    args = parser.parse_args()
    # Safety check: allowlist
    if args.allowed_hosts:
        allowed = [h.strip() for h in args.allowed_hosts.split(",")]
        target_host = args.target.replace("http://", "").replace("https://", "").split("/")[0]
        if target_host not in allowed:
            console.print(f"[red]Error: Target {target_host} not in allowed hosts: {allowed}[/red]")
            sys.exit(1)
    
    if not args.api_key:
        console.print("[red]Error: Cerebras API key required. Set CEREBRAS_API_KEY or use --api-key[/red]")
        sys.exit(1)
    
    # Initialize attacker
    attacker = CerebrasAttacker(
        api_key=args.api_key,
        target_url=args.target,
        model=args.model
    )
    
    # Run attack
    try:
        for event in attacker.run(max_steps=args.max_steps):
            pass  # Events are logged by AttackLogger
        
        # Print executive summary first (right after attack)
        from executive_summary import generate_executive_summary, print_executive_summary
        exec_summary = generate_executive_summary(
            state=attacker.state,
            attack_time=time.time() - attacker.start_time if attacker.start_time else 10,
            genome={},
            benchmark=None
        )
        print_executive_summary(exec_summary)
        
        # Run genome analysis if attack completed and not skipped
        if not args.skip_genome and attacker.state.attack_log:
            console.print()
            console.print("[bold cyan]Running Security Genome Analysis...[/bold cyan]")
            console.print()
            
            analyzer = SecurityGenomeAnalyzer(
                api_key=args.api_key,
                model=args.model
            )
            
            result = analyzer.analyze(
                attack_log=attacker.state.attack_log,
                state=attacker.state
            )
            
            print_genome_analysis(result)
            
            # Run blue team analysis
            console.print()
            console.print("[bold blue]Running Blue Team Replay Analysis...[/bold blue]")
            console.print()
            
            blue_analyzer = BlueTeamAnalyzer(
                api_key=args.api_key,
                model=args.model
            )
            
            blue_result = blue_analyzer.analyze(
                attack_log=attacker.state.attack_log,
                state=attacker.state
            )
            
            print_blue_team_analysis(blue_result)
            
            # Run attack graph generation
            console.print()
            console.print("[bold yellow]Generating Attack Graph...[/bold yellow]")
            console.print()
            
            graph_gen = AttackGraphGenerator(
                api_key=args.api_key,
                model=args.model
            )
            
            graph_result = graph_gen.generate(
                attack_log=attacker.state.attack_log,
                state=attacker.state
            )
            
            print_attack_graph(graph_result)
            
            # Run benchmark if requested
            if args.benchmark:
                console.print()
                console.print("[bold magenta]Running Speed Benchmark...[/bold magenta]")
                console.print()
                
                bench = BenchmarkHarness(api_key=args.api_key)
                bench_results = bench.run_benchmark(num_runs=2)
                print_benchmark(bench_results)
            
            # Generate JSON report if requested
            if args.json_output:
                json_report = generate_json_report(
                    state=attacker.state,
                    genome=result,
                    blue_team=blue_result,
                    attack_graph=graph_result,
                    benchmark=bench_results if args.benchmark else None
                )
                save_json_report(json_report)
                print_json_summary(json_report)
                # CI exit code
            if args.fail_on_critical and attacker.state.loot:
                console.print("[red]CI CHECK FAILED: Critical data exfiltration detected[/red]")
                sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Attack interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Attack failed: {str(e)}[/red]")
        raise

if __name__ == "__main__":
    main()