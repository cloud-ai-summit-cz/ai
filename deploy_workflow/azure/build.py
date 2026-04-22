#!/usr/bin/env python3
"""ACR Build Script (Workflow)

Builds and pushes container images to Azure Container Registry using ACR Tasks.
ACR Tasks perform remote builds, so no local Docker installation is required.

Usage:
    python build.py                       # Build all containers
    python build.py --container backend   # Build specific container
    python build.py --acr-name myacr      # Specify ACR name directly
    python build.py --list                # List available containers
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def get_script_dir() -> Path:
    """Get the directory containing this script."""
    return Path(__file__).parent.resolve()


def load_config(config_path: Path) -> dict:
    """Load build configuration from YAML file."""
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def get_terraform_output(terraform_dir: Path, output_name: str) -> str | None:
    """Read a single Terraform output value via `terraform output -raw`.

    Returns None if the output is missing or terraform fails.
    """
    try:
        import os

        # NOTE: Do not use shell=True with a list of args on Unix/macOS.
        # It will drop all arguments except the first one ("terraform").
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if stderr:
            print(
                f"Warning: terraform output '{output_name}' failed: {stderr}",
                file=sys.stderr,
            )
        return None
    except FileNotFoundError:
        print("Warning: terraform not found in PATH", file=sys.stderr)
        return None


def get_acr_name_from_terraform(terraform_dir: Path) -> str | None:
    """Get ACR name from Terraform output."""
    return get_terraform_output(terraform_dir, "acr_name")


def get_resource_group_name_from_terraform(terraform_dir: Path) -> str | None:
    """Get Azure resource group name from Terraform output."""
    return get_terraform_output(terraform_dir, "resource_group_name")


def build_container(
    acr_name: str,
    resource_group_name: str | None,
    container: dict,
    base_path: Path,
) -> bool:
    """Build and push a container using ACR Tasks."""
    name = container["name"]
    image = container["image"]
    tag = container.get("tag", "latest")
    context_path = (base_path / container["path"]).resolve()
    dockerfile_rel = container.get("dockerfile", "Dockerfile")

    if not context_path.exists():
        print(f"Error: Build context not found: {context_path}", file=sys.stderr)
        return False

    dockerfile = context_path / dockerfile_rel
    if not dockerfile.exists():
        print(f"Error: Dockerfile not found: {dockerfile}", file=sys.stderr)
        return False

    full_image = f"{image}:{tag}"
    print(f"\n{'=' * 60}")
    print(f"Building: {name}")
    print(f"  Image: {acr_name}.azurecr.io/{full_image}")
    print(f"  Context: {context_path}")
    if dockerfile_rel != "Dockerfile":
        print(f"  Dockerfile: {dockerfile_rel}")
    print(f"{'=' * 60}\n")

    cmd = [
        "az",
        "acr",
        "build",
        "--registry",
        acr_name,
        "--image",
        full_image,
    ]

    if resource_group_name:
        cmd.extend(["--resource-group", resource_group_name])

    if dockerfile_rel != "Dockerfile":
        cmd.extend(["--file", str(dockerfile)])

    cmd.append(str(context_path))

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Successfully built {name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to build {name}: {e}", file=sys.stderr)
        return False


def list_containers(config: dict) -> None:
    """List available containers from config."""
    print("\nAvailable containers:")
    print("-" * 40)
    for container in config.get("containers", []):
        name = container["name"]
        image = container["image"]
        tag = container.get("tag", "latest")
        path = container["path"]
        dockerfile = container.get("dockerfile")
        print(f"  {name}")
        print(f"    Image: {image}:{tag}")
        print(f"    Path:  {path}")
        if dockerfile:
            print(f"    Dockerfile: {dockerfile}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build container images using Azure Container Registry Tasks",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to build config YAML (default: build-config.yaml in script directory)",
    )
    parser.add_argument(
        "--acr-name",
        dest="acr_name",
        help="Azure Container Registry name (auto-detected from Terraform if not specified)",
    )
    parser.add_argument(
        "--resource-group",
        dest="resource_group",
        help="Azure Resource Group name (auto-detected from Terraform if not specified)",
    )
    parser.add_argument(
        "--container",
        "-c",
        dest="containers",
        action="append",
        help="Specific container to build (can be specified multiple times)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available containers and exit",
    )

    args = parser.parse_args()

    script_dir = get_script_dir()
    config_path = args.config or (script_dir / "build-config.yaml")
    terraform_dir = script_dir / "terraform"

    config = load_config(config_path)

    if args.list:
        list_containers(config)
        return

    acr_name = args.acr_name or config.get("acr_name")
    if not acr_name:
        print("Detecting ACR name from Terraform output...")
        acr_name = get_acr_name_from_terraform(terraform_dir)

    resource_group_name = args.resource_group or config.get("resource_group_name")
    if not resource_group_name:
        print("Detecting Resource Group name from Terraform output...")
        resource_group_name = get_resource_group_name_from_terraform(terraform_dir)

    if not acr_name:
        print(
            "Error: ACR name not specified and could not be detected from Terraform.\n"
            "Please specify --acr-name or run 'terraform apply' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Using ACR: {acr_name}")
    if resource_group_name:
        print(f"Using Resource Group: {resource_group_name}")

    all_containers = config.get("containers", [])
    if not all_containers:
        print("Error: No containers defined in config", file=sys.stderr)
        sys.exit(1)

    if args.containers:
        container_names = set(args.containers)
        containers_to_build = [c for c in all_containers if c["name"] in container_names]

        known_names = {c["name"] for c in all_containers}
        unknown = container_names - known_names
        if unknown:
            print(f"Error: Unknown containers: {', '.join(sorted(unknown))}", file=sys.stderr)
            print(f"Available: {', '.join(sorted(known_names))}", file=sys.stderr)
            sys.exit(1)
    else:
        if config.get("build_all_by_default", True):
            containers_to_build = all_containers
        else:
            print("Error: No containers specified and build_all_by_default is false")
            print("Use --container to specify which containers to build")
            sys.exit(1)

    results: list[tuple[str, bool]] = []
    for container in containers_to_build:
        success = build_container(acr_name, resource_group_name, container, config_path.parent)
        results.append((container["name"], success))

    print(f"\n{'=' * 60}")
    print("Build Summary")
    print(f"{'=' * 60}")

    success_count = sum(1 for _, success in results if success)
    fail_count = len(results) - success_count

    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    print()
    print(f"Total: {len(results)}, Succeeded: {success_count}, Failed: {fail_count}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
