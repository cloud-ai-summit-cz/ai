#!/usr/bin/env python3
"""Provision invoice workflow agents to Azure AI Foundry.

Runs provisioning scripts for all configured agents sequentially.

Usage:
    uv run python provision_all.py                    # Provision all agents (create)
    uv run python provision_all.py --list             # List agents to provision
    uv run python provision_all.py --agent X          # Provision specific agent
    uv run python provision_all.py --action destroy   # Destroy instead of create

Notes:
- Each agent's provisioning script is expected to be idempotent for `create`.
- Agent directories are resolved relative to `settings.src_dir` in config.yaml.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

import yaml


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


_ENV_VAR_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]+)=")


def _supported_env_vars_for_agent(agent_dir: Path) -> set[str]:
    """Infer supported env vars for an agent by reading its `.env.example`.

    This keeps `provision_all.py` decoupled from each agent's CLI implementation and
    avoids passing flags an agent doesn't recognize.
    """
    env_example = agent_dir / ".env.example"
    if not env_example.exists():
        return set()

    supported: set[str] = set()
    for line in env_example.read_text(encoding="utf-8").splitlines():
        match = _ENV_VAR_PATTERN.match(line.strip())
        if match:
            supported.add(match.group(1))
    return supported


def _env_var_to_flag(env_var: str) -> str | None:
    """Map env var names to provision.py CLI flags."""
    mapping = {
        "AZURE_AI_FOUNDRY_ENDPOINT": "--azure-ai-foundry-endpoint",
        "MODEL_DEPLOYMENT_NAME": "--model-deployment-name",
        "MCP_INVOICE_DATA_URL": "--mcp-invoice-data-url",
        "APPLICATIONINSIGHTS_CONNECTION_STRING": "--applicationinsights-connection-string",
    }
    return mapping.get(env_var)


def _inject_flags(command: str, flags: list[tuple[str, str]]) -> str:
    """Inject flags into a command string before the final subcommand token.

    Assumes commands look like: `uv run python provision.py create`.
    """
    if not flags:
        return command

    tokens = command.strip().split()
    if not tokens:
        return command

    subcommand_index = len(tokens)
    if tokens[-1] in {"create", "destroy", "list"}:
        subcommand_index = len(tokens) - 1

    flag_tokens: list[str] = []
    for flag, value in flags:
        flag_tokens.append(flag)
        flag_tokens.append(shlex.quote(value))

    tokens = tokens[:subcommand_index] + flag_tokens + tokens[subcommand_index:]
    return " ".join(tokens)


def list_agents(config: dict) -> None:
    """Print list of agents to provision."""
    print("\nAgents configured for provisioning:\n")
    for agent in config.get("agents", []):
        print(f"  • {agent['name']}")
        print(f"    Path: {agent['path']}")
        print(f"    Command: {agent['command']}")
        overrides = agent.get("overrides")
        if overrides:
            print(f"    Overrides: {overrides}")
        print()


def _command_for_action(agent: dict, action: str) -> str:
    command = agent["command"].strip()

    if action == "create":
        return command

    if action == "destroy":
        # Convention: replace trailing " create" with " destroy".
        # If the command doesn't match that pattern, user should set command explicitly in config.
        if command.endswith(" create"):
            return command[: -len(" create")] + " destroy"
        return command.replace(" create ", " destroy ")

    raise ValueError(f"Unsupported action: {action}")


def run_agent(agent: dict, src_dir: Path, action: str) -> bool:
    """Run provisioning for a single agent. Returns True on success."""
    name = agent["name"]
    path = agent["path"]

    working_dir = src_dir / path

    if not working_dir.exists():
        print(f"  ✗ Directory not found: {working_dir}")
        return False

    command = _command_for_action(agent, action)

    # Build effective overrides.
    # Precedence (lowest -> highest): config.settings.env_overrides -> agent.overrides -> CLI overrides.
    config_overrides = agent.get("_config_env_overrides", {})
    agent_overrides = agent.get("overrides", {})
    cli_overrides = agent.get("_cli_env_overrides", {})
    effective_overrides: dict[str, str] = {
        **{k: str(v) for k, v in (config_overrides or {}).items() if v is not None},
        **{k: str(v) for k, v in (agent_overrides or {}).items() if v is not None},
        **{k: str(v) for k, v in (cli_overrides or {}).items() if v is not None},
    }

    supported_env_vars = _supported_env_vars_for_agent(working_dir)
    flags_to_inject: list[tuple[str, str]] = []
    for env_var, value in effective_overrides.items():
        if env_var not in supported_env_vars:
            continue
        flag = _env_var_to_flag(env_var)
        if not flag:
            continue
        flags_to_inject.append((flag, value))

    command = _inject_flags(command, flags_to_inject)

    print(f"  Action: {action}")
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
    parser = argparse.ArgumentParser(description="Provision workflow agents to Azure AI Foundry")
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
        help="Run only the specified agent (by name)",
    )
    parser.add_argument(
        "--action",
        choices=["create", "destroy"],
        default="create",
        help="Action to run for each agent",
    )

    # Optional env-var overrides (mirrors agent `.env.example` variables)
    parser.add_argument(
        "--azure-ai-foundry-endpoint",
        dest="azure_ai_foundry_endpoint",
        help="Overrides AZURE_AI_FOUNDRY_ENDPOINT for provisioners that support it",
    )
    parser.add_argument(
        "--model-deployment-name",
        dest="model_deployment_name",
        help="Overrides MODEL_DEPLOYMENT_NAME for provisioners that support it",
    )
    parser.add_argument(
        "--mcp-invoice-data-url",
        dest="mcp_invoice_data_url",
        help="Overrides MCP_INVOICE_DATA_URL for provisioners that support it",
    )
    parser.add_argument(
        "--applicationinsights-connection-string",
        dest="applicationinsights_connection_string",
        help="Overrides APPLICATIONINSIGHTS_CONNECTION_STRING for provisioners that support it",
    )

    args = parser.parse_args()

    if not args.config.exists():
        print(f"Config file not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)

    if args.list_agents:
        list_agents(config)
        return

    script_dir = Path(__file__).parent.resolve()
    src_dir = (script_dir / config.get("settings", {}).get("src_dir", "../../src")).resolve()

    print(f"\n{'=' * 60}")
    print("Workflow Agent Provisioning")
    print(f"{'=' * 60}")
    print(f"Source directory: {src_dir}")
    print(f"Action: {args.action}\n")

    agents = config.get("agents", [])
    if args.agent:
        agents = [a for a in agents if a["name"] == args.agent]
        if not agents:
            print(f"Agent not found: {args.agent}")
            sys.exit(1)

    config_env_overrides = config.get("settings", {}).get("env_overrides", {}) or {}
    cli_env_overrides = {
        "AZURE_AI_FOUNDRY_ENDPOINT": args.azure_ai_foundry_endpoint,
        "MODEL_DEPLOYMENT_NAME": args.model_deployment_name,
        "MCP_INVOICE_DATA_URL": args.mcp_invoice_data_url,
        "APPLICATIONINSIGHTS_CONNECTION_STRING": args.applicationinsights_connection_string,
    }

    results: dict[str, bool] = {}

    for agent in agents:
        agent["_config_env_overrides"] = config_env_overrides
        agent["_cli_env_overrides"] = cli_env_overrides
        name = agent["name"]
        print(f"[{name}] Starting...")
        success = run_agent(agent, src_dir, args.action)
        results[name] = success

        if success:
            print(f"[{name}] ✓ Success\n")
        else:
            print(f"[{name}] ✗ Failed\n")

    print(f"{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")

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

    print("\n✓ All workflow agents processed successfully")


if __name__ == "__main__":
    main()
