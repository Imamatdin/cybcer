#!/usr/bin/env python3
"""
Cerebras Security Demo - Main Entry Point

Modes:
  red  - Red team autonomous pentesting (existing)
  soc  - SOC autopilot incident response (new)

Usage:
  python main.py --mode red --target http://127.0.0.1:5000
  python main.py --mode soc --bots_path data/bots --compare
"""

import argparse
import sys
from pathlib import Path


def run_red_team(args):
    """Run red team mode (existing orchestrator)."""
    try:
        from orchestrator import CerebrasAttacker
        from output import print_banner, print_summary
    except ImportError as e:
        print(f"[!] Red team mode requires: orchestrator.py, output.py")
        print(f"    Error: {e}")
        sys.exit(1)
    
    if not args.target:
        print("[!] --target required for red team mode")
        sys.exit(1)
    
    print_banner()
    
    attacker = CerebrasAttacker(
        target_url=args.target,
        api_key=args.api_key,
        model=args.model,
        max_steps=args.max_steps
    )
    
    for event in attacker.run():
        # Events are printed by orchestrator
        pass
    
    print_summary(attacker.state)


def run_soc_mode(args):
    """Run SOC autopilot mode."""
    try:
        from demo_soc import run_soc_demo
    except ImportError as e:
        print(f"[!] SOC mode requires: demo_soc.py and dependencies")
        print(f"    Error: {e}")
        sys.exit(1)
    
    run_soc_demo(
        bots_path=args.bots_path,
        rate=args.rate,
        window_size=args.window_size,
        output_dir=args.output_dir,
        compare_gemini=args.compare
    )


def main():
    parser = argparse.ArgumentParser(
        description="Cerebras Security Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Red team mode (autonomous pentesting)
  python main.py --mode red --target http://127.0.0.1:5000

  # SOC mode (incident response autopilot)
  python main.py --mode soc --bots_path data/bots

  # SOC mode with Gemini comparison
  python main.py --mode soc --compare
        """
    )
    
    # Mode selection
    parser.add_argument("--mode", "-m", choices=["red", "soc"], default="red",
                        help="Operating mode: red (pentest) or soc (incident response)")
    
    # Red team options
    parser.add_argument("--target", "-t", help="Target URL (red mode)")
    parser.add_argument("--api-key", "-k", help="Cerebras API key (or use CEREBRAS_API_KEY env)")
    parser.add_argument("--max-steps", "-s", type=int, default=20, help="Max attack steps (red mode)")
    parser.add_argument("--model", default="llama-4-scout-17b-16e-instruct", help="Cerebras model")
    parser.add_argument("--skip-genome", action="store_true", help="Skip genome analysis (red mode)")
    
    # SOC mode options
    parser.add_argument("--bots_path", "-b", help="Path to BOTS export folder (soc mode)")
    parser.add_argument("--rate", "-r", type=int, default=2000, help="Event replay rate (soc mode)")
    parser.add_argument("--window_size", "-w", type=int, default=300, help="Window size (soc mode)")
    parser.add_argument("--output_dir", "-o", default="artifacts", help="Output directory (soc mode)")
    parser.add_argument("--compare", "-c", action="store_true", help="Compare Cerebras vs Gemini (soc mode)")
    
    args = parser.parse_args()
    
    if args.mode == "red":
        run_red_team(args)
    elif args.mode == "soc":
        run_soc_mode(args)


if __name__ == "__main__":
    main()