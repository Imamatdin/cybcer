#!/usr/bin/env python3
import argparse
import os
import sys
from rich.console import Console
from orchestrator import CerebrasAttacker
from blue_team import BlueTeamAnalyzer, print_blue_team_analysis
from genome_analysis import SecurityGenomeAnalyzer, print_genome_analysis
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
    
    args = parser.parse_args()
    
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
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Attack interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Attack failed: {str(e)}[/red]")
        raise

if __name__ == "__main__":
    main()