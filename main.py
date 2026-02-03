#!/usr/bin/env python3
import argparse
import os
import sys

# Load from .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

from rich.console import Console
from orchestrator import CerebrasAttacker

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
    except KeyboardInterrupt:
        console.print("\n[yellow]Attack interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Attack failed: {str(e)}[/red]")
        raise

if __name__ == "__main__":
    main()