#!/usr/bin/env python3
"""Provision all agents to Azure AI Foundry.

Runs provisioning scripts for all configured agents sequentially.

Usage:
    uv run python provision_all.py              # Provision all agents
    uv run python provision_all.py --list       # List agents to provision
    uv run python provision_all.py --agent X    # Provision specific agent
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def list_agents(config: dict) -> None:
    """Print list of agents to provision."""
    print("\nAgents configured for provisioning:\n")
    for agent in config.get("agents", []):
        print(f"  • {agent['name']}")
        print(f"    Path: {agent['path']}")
        print(f"    Command: {agent['command']}")
        print()


def provision_agent(agent: dict, src_dir: Path) -> bool:
    """Provision a single agent. Returns True on success."""
    name = agent["name"]
    path = agent["path"]
    command = agent["command"]

    working_dir = src_dir / path

    if not working_dir.exists():
        print(f"  ✗ Directory not found: {working_dir}")
        return False

    print(f"  Running: {command}")
    print(f"  Working dir: {working_dir}")
    print()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Provision all agents to Azure AI Foundry"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        dest="list_agents",
        help="List agents and exit",
    )
    parser.add_argument(
        "--agent",
        "-a",
        type=str,
        help="Provision only the specified agent",
    )
    args = parser.parse_args()

    # Load configuration
    if not args.config.exists():
        print(f"Config file not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)

    if args.list_agents:
        list_agents(config)
        return

    # Resolve paths
    script_dir = Path(__file__).parent.resolve()
    src_dir = (script_dir / config.get("settings", {}).get("src_dir", "../../src")).resolve()

    print(f"\n{'=' * 50}")
    print("Agent Provisioning")
    print(f"{'=' * 50}")
    print(f"Source directory: {src_dir}\n")

    # Filter agents if specific one requested
    agents = config.get("agents", [])
    if args.agent:
        agents = [a for a in agents if a["name"] == args.agent]
        if not agents:
            print(f"Agent not found: {args.agent}")
            sys.exit(1)

    # Provision agents sequentially
    results: dict[str, bool] = {}

    for agent in agents:
        name = agent["name"]
        print(f"[{name}] Provisioning...")
        success = provision_agent(agent, src_dir)
        results[name] = success

        if success:
            print(f"[{name}] ✓ Provisioned successfully\n")
        else:
            print(f"[{name}] ✗ Failed\n")

    # Summary
    print(f"{'=' * 50}")
    print("Summary")
    print(f"{'=' * 50}")

    succeeded = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    print()
    print(f"Succeeded: {succeeded}/{len(results)}")

    if failed > 0:
        print(f"Failed: {failed}")
        sys.exit(1)

    print("\n✓ All agents provisioned successfully")


if __name__ == "__main__":
    main()
