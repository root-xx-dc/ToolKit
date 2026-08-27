"""
rootx.docker_center
===================
Docker management center. Requires docker CLI to be installed.
Prerequisite: utils.command_exists("docker")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from . import utils


@dataclass
class Container:
    container_id: str
    image: str
    command: str
    created: str
    status: str
    ports: str
    name: str


@dataclass
class DockerImage:
    repository: str
    tag: str
    image_id: str
    created: str
    size: str


def is_available() -> bool:
    return utils.command_exists("docker")


def list_containers(all_containers: bool = False) -> List[Container]:
    """List containers. all_containers=True includes stopped ones."""
    cmd = [
        "docker",
        "ps",
        "--format",
        "{{.ID}}\t{{.Image}}\t{{.Command}}\t{{.CreatedAt}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}",
    ]
    if all_containers:
        cmd.append("-a")
    result = utils.run(cmd, timeout=15)
    containers: List[Container] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 7:
            containers.append(Container(*parts[:7]))
    return containers


def list_images() -> List[DockerImage]:
    """List docker images."""
    result = utils.run(
        [
            "docker",
            "images",
            "--format",
            "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}",
        ],
        timeout=15,
    )
    images: List[DockerImage] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 5:
            images.append(DockerImage(*parts[:5]))
    return images


def container_logs(name: str, lines: int = 50) -> str:
    result = utils.run(["docker", "logs", "--tail", str(lines), name], timeout=15)
    return result.stdout or result.stderr or result.error or "No output."


def start_container(name: str) -> utils.CommandResult:
    return utils.run(["docker", "start", name], timeout=30)


def stop_container(name: str) -> utils.CommandResult:
    return utils.run(["docker", "stop", name], timeout=30)


def restart_container(name: str) -> utils.CommandResult:
    return utils.run(["docker", "restart", name], timeout=30)


def remove_container(name: str) -> utils.CommandResult:
    return utils.run(["docker", "rm", name], timeout=30)


def remove_image(name: str) -> utils.CommandResult:
    return utils.run(["docker", "rmi", name], timeout=30)


def prune() -> utils.CommandResult:
    return utils.run(["docker", "system", "prune", "-f"], timeout=120)


def prune_estimate() -> str:
    """Show disk usage of docker objects (estimate before prune)."""
    result = utils.run(["docker", "system", "df"], timeout=15)
    return result.stdout or "Could not estimate."
