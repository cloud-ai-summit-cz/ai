#!/usr/bin/env python3
"""Local development runner for Cofilot AI Platform.

Starts all enabled agents and MCP servers with unified log streaming.
Each service's output is prefixed with a colored tag for easy identification.

Usage:
    uv run python run_all.py                    # Use default config.yaml
    uv run python run_all.py --config my.yaml   # Use custom config
    uv run python run_all.py --list             # List available services
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.text import Text

console = Console()

# ANSI color codes for service tags
COLORS: dict[str, str] = {
    "cyan": "\033[36m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "bright_blue": "\033[94m",
    "bright_green": "\033[92m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_yellow": "\033[93m",
    "white": "\033[37m",
}
RESET = "\033[0m"


@dataclass
class ServiceConfig:
    """Configuration for a single service."""

    name: str
    service_type: str  # "agent" or "mcp"
    enabled: bool
    port: int | None = None
    provision_only: bool = False  # If True, runs once (provisioning script) instead of long-running
    color: str = "white"
    command: str | None = None
    working_dir: Path | None = None


@dataclass
class RunnerConfig:
    """Full runner configuration."""

    services: list[ServiceConfig] = field(default_factory=list)
    src_dir: Path = field(default_factory=lambda: Path("../../src"))
    log_level: str = "INFO"


def load_config(config_path: Path) -> RunnerConfig:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        data = yaml.safe_load(f)

    runner = RunnerConfig()

    # Get settings
    settings = data.get("settings", {})
    runner.src_dir = Path(settings.get("src_dir", "../../src"))
    runner.log_level = settings.get("log_level", "INFO")

    # Get color mappings
    color_config = settings.get("colors", {})
    agent_colors = color_config.get("agents", {})
    mcp_colors = color_config.get("mcp_servers", {})

    # Parse agents
    agents_data = data.get("agents", {})
    for name, cfg in agents_data.items():
        if isinstance(cfg, dict):
            service = ServiceConfig(
                name=name,
                service_type="agent",
                enabled=cfg.get("enabled", True),
                provision_only=cfg.get("provision_only", False),
                color=agent_colors.get(name, "cyan"),
                command=cfg.get("command"),
            )
            runner.services.append(service)

    # Parse MCP servers
    mcp_data = data.get("mcp_servers", {})
    for name, cfg in mcp_data.items():
        if isinstance(cfg, dict):
            service = ServiceConfig(
                name=name,
                service_type="mcp",
                enabled=cfg.get("enabled", True),
                port=cfg.get("port"),
                color=mcp_colors.get(name, "green"),
                command=cfg.get("command"),
            )
            runner.services.append(service)

    return runner


def get_service_command(service: ServiceConfig, src_dir: Path) -> tuple[str, Path] | None:
    """Get the command and working directory for a service."""
    # Determine folder name
    if service.service_type == "agent":
        folder_name = f"agent-{service.name}"
        if service.provision_only:
            # Foundry Native agents run provisioning script (files directly in folder)
            default_cmd = "uv run python provision.py create"
        else:
            # MAF/LangGraph agents run as long-running services with uvicorn's built-in reload
            default_cmd = "uv run python main.py"
    else:
        folder_name = f"mcp-{service.name}"
        module_name = f"mcp_{service.name.replace('-', '_')}"
        port = service.port or 8000
        default_cmd = f"uv run uvicorn {module_name}.main:app --host 0.0.0.0 --port {port} --reload"

    working_dir = src_dir / folder_name
    command = service.command or default_cmd

    return command, working_dir


class ServiceProcess:
    """Manages a single service subprocess with log streaming."""

    def __init__(
        self,
        service: ServiceConfig,
        command: str,
        working_dir: Path,
        env: dict[str, str],
    ) -> None:
        self.service = service
        self.command = command
        self.working_dir = working_dir
        self.env = env
        self.process: asyncio.subprocess.Process | None = None
        self._stopped = False

        # Create colored tag using Rich
        tag_width = 18
        tag_text = f"{service.service_type[:3]}-{service.name}"[:tag_width]
        self.tag = f"[{service.color}][{tag_text:<{tag_width}}][/{service.color}]"
        # Plain tag for subprocess output (no Rich markup)
        color_code = COLORS.get(service.color, COLORS["white"])
        self.plain_tag = f"{color_code}[{tag_text:<{tag_width}}]{RESET}"

    async def start(self) -> None:
        """Start the service process."""
        if not self.working_dir.exists():
            console.print(f"{self.tag} [red]ERROR: Directory not found: {self.working_dir}[/red]")
            return

        # Check if pyproject.toml exists
        pyproject = self.working_dir / "pyproject.toml"
        if not pyproject.exists():
            console.print(f"{self.tag} [yellow]SKIP: No pyproject.toml found[/yellow]")
            return

        console.print(f"{self.tag} Starting in {self.working_dir}")
        console.print(f"{self.tag} Command: {self.command}")

        try:
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.working_dir,
                env={**os.environ, **self.env},
            )

            # Start log streaming
            asyncio.create_task(self._stream_logs())

        except Exception as e:
            console.print(f"{self.tag} [red]Failed to start: {e}[/red]")

    async def _stream_logs(self) -> None:
        """Stream logs from the process with tagged output."""
        if not self.process or not self.process.stdout:
            return

        try:
            async for line in self.process.stdout:
                if self._stopped:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    print(f"{self.plain_tag} {text}")
        except Exception:
            pass  # Process ended

    async def stop(self) -> None:
        """Stop the service process."""
        self._stopped = True
        if self.process and self.process.returncode is None:
            console.print(f"{self.tag} Stopping...")
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    console.print(f"{self.tag} Force killing...")
                    self.process.kill()
                    await self.process.wait()
            except ProcessLookupError:
                pass  # Already exited
            console.print(f"{self.tag} Stopped")


class LocalRunner:
    """Manages all service processes."""

    def __init__(self, config: RunnerConfig, env_file: Path | None = None) -> None:
        self.config = config
        self.processes: list[ServiceProcess] = []
        self._shutdown_event = asyncio.Event()

        # Load environment variables
        self.env: dict[str, str] = {}
        if env_file and env_file.exists():
            load_dotenv(env_file)
            console.print(f"[dim]Loaded environment from {env_file}[/dim]")

        # Set log level and ensure UTF-8 encoding for subprocesses
        self.env["LOG_LEVEL"] = config.log_level
        self.env["PYTHONIOENCODING"] = "utf-8"
        self.env["PYTHONUTF8"] = "1"

    def list_services(self) -> None:
        """Print list of available services."""
        console.print("\n[bold]Available Services[/bold]\n")

        console.print("[bold cyan]Agents:[/bold cyan]")
        for svc in self.config.services:
            if svc.service_type == "agent":
                status = "[green]enabled[/green]" if svc.enabled else "[dim]disabled[/dim]"
                mode = " [yellow](provision)[/yellow]" if svc.provision_only else ""
                console.print(f"  • {svc.name}: {status}{mode}")

        console.print("\n[bold green]MCP Servers:[/bold green]")
        for svc in self.config.services:
            if svc.service_type == "mcp":
                status = "[green]enabled[/green]" if svc.enabled else "[dim]disabled[/dim]"
                port_info = f" (port {svc.port})" if svc.port else ""
                console.print(f"  • {svc.name}: {status}{port_info}")

        console.print()

    async def start_all(self) -> None:
        """Start all enabled services."""
        script_dir = Path(__file__).parent.resolve()
        src_dir = (script_dir / self.config.src_dir).resolve()

        console.print(f"\n[bold]Starting Cofilot AI Platform[/bold]")
        console.print(f"[dim]Source directory: {src_dir}[/dim]\n")

        # Separate provision-only and long-running services
        enabled_services = [svc for svc in self.config.services if svc.enabled]
        provision_services = [svc for svc in enabled_services if svc.provision_only]
        longrunning_services = [svc for svc in enabled_services if not svc.provision_only]

        if not enabled_services:
            console.print("[yellow]No services enabled.[/yellow]")
            return

        # First, run provisioning scripts (they complete and exit) - all in parallel
        if provision_services:
            console.print(f"[bold]Provisioning {len(provision_services)} Foundry agents in parallel...[/bold]\n")
            provision_procs: list[ServiceProcess] = []

            for service in provision_services:
                result = get_service_command(service, src_dir)
                if result is None:
                    continue

                command, working_dir = result
                service.working_dir = working_dir
                proc = ServiceProcess(service, command, working_dir, self.env)
                provision_procs.append(proc)

            # Start all provisioning scripts in parallel
            await asyncio.gather(*[proc.start() for proc in provision_procs])

            # Wait for all provisioning to complete
            async def wait_for_provision(proc: ServiceProcess) -> None:
                if proc.process:
                    await proc.process.wait()
                    if proc.process.returncode == 0:
                        console.print(f"{proc.tag} [green]✓ Provisioned[/green]")
                    else:
                        console.print(f"{proc.tag} [red]✗ Failed (exit code {proc.process.returncode})[/red]")

            await asyncio.gather(*[wait_for_provision(proc) for proc in provision_procs])

            console.print()  # Blank line after provisioning

        # Then start long-running services
        if longrunning_services:
            console.print(f"[bold]Starting {len(longrunning_services)} services in parallel...[/bold]\n")

            # Prepare all service processes
            for service in longrunning_services:
                result = get_service_command(service, src_dir)
                if result is None:
                    continue

                command, working_dir = result
                service.working_dir = working_dir

                proc = ServiceProcess(service, command, working_dir, self.env)
                self.processes.append(proc)

            # Start all services in parallel
            await asyncio.gather(*[proc.start() for proc in self.processes])

            console.print(f"\n[bold green]✓ Started {len(self.processes)} services[/bold green]")
            console.print("[dim]Press Ctrl+C to stop all services[/dim]\n")

            # Wait for shutdown signal
            await self._shutdown_event.wait()
        else:
            console.print("[green]✓ All provisioning complete. No long-running services to start.[/green]")

    async def stop_all(self) -> None:
        """Stop all running services."""
        console.print("\n[bold yellow]Shutting down...[/bold yellow]")

        # Stop all processes in parallel
        await asyncio.gather(*[proc.stop() for proc in self.processes])

        console.print("[bold green]✓ All services stopped[/bold green]")

    def signal_shutdown(self) -> None:
        """Signal that shutdown should occur."""
        self._shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Local development runner for Cofilot AI Platform"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--env",
        "-e",
        type=Path,
        default=Path(__file__).parent / ".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        dest="list_services",
        help="List available services and exit",
    )
    args = parser.parse_args()

    # Load configuration
    if not args.config.exists():
        console.print(f"[red]Config file not found: {args.config}[/red]")
        sys.exit(1)

    config = load_config(args.config)
    runner = LocalRunner(config, args.env if args.env.exists() else None)

    if args.list_services:
        runner.list_services()
        return

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def handle_signal() -> None:
        runner.signal_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: handle_signal())

    try:
        await runner.start_all()
    finally:
        await runner.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
