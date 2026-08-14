"""Sandboxed Docker execution for agent runs.

Design decision: Each run gets its own ephemeral Docker container with:
- The target repo cloned and mounted at /workspace
- No network access (network_mode="none") — tests can't exfiltrate data
- CPU/memory/time limits — prevent resource exhaustion
- Automatic cleanup — container is destroyed after each run

Why Docker over direct subprocess: Complete filesystem isolation,
resource limits, and automatic cleanup. The target repo might have
malicious setup.py or tests that delete files.

Why docker-py over shelling out: Type-safe Python API, proper error
handling, no shell injection risk.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import docker
from docker.models.containers import Container

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DockerSandbox:
    """Ephemeral Docker container for sandboxed code execution.

    Usage:
        async with DockerSandbox(repo_url, settings) as sandbox:
            exit_code, output = await sandbox.exec("pytest tests/")
    """

    def __init__(
        self,
        repo_url: str,
        settings: Settings | None = None,
        commit_sha: str | None = None,
    ):
        self.repo_url = repo_url
        self.settings = settings or get_settings()
        self.commit_sha = commit_sha
        self.client = docker.from_env()
        self.container: Container | None = None
        self.work_dir: str | None = None
        self._temp_dir: str | None = None

    async def start(self) -> None:
        """Clone the repo and start an ephemeral container."""
        # Clone the repository to a temporary directory
        self._temp_dir = tempfile.mkdtemp(prefix="fixforge-")
        self.work_dir = self._temp_dir

        logger.info(
            "Cloning repo",
            extra={
                "repo": self.repo_url,
                "dest": self.work_dir,
            },
        )

        # Clone in a thread to avoid blocking the event loop
        await asyncio.to_thread(
            self._clone_repo, self.repo_url, self.work_dir, self.commit_sha
        )

        # Build or pull the sandbox image
        await self._ensure_image()

        # Start the container
        logger.info("Starting sandbox container")
        self.container = self.client.containers.run(
            image="fixforge-sandbox:latest",
            command="sleep infinity",  # Keep alive for exec_run calls
            volumes={
                self.work_dir: {"bind": "/workspace", "mode": "rw"},
            },
            working_dir="/workspace",
            network_mode="none",  # No network access
            mem_limit=self.settings.sandbox_mem_limit,
            nano_cpus=self.settings.sandbox_cpu_limit,
            security_opt=["no-new-privileges"],
            detach=True,
            remove=False,  # We remove manually after cleanup
        )

        logger.info(
            "Sandbox container started",
            extra={"container_id": self.container.short_id},
        )

    async def exec(
        self,
        cmd: str,
        timeout: int | None = None,
    ) -> tuple[int, str]:
        """Execute a command inside the sandbox container.

        Args:
            cmd: Command to execute.
            timeout: Timeout in seconds (defaults to settings.sandbox_timeout).

        Returns:
            (exit_code, combined_output)
        """
        if not self.container:
            raise RuntimeError("Sandbox not started. Call start() first.")

        timeout = timeout or self.settings.sandbox_timeout

        try:
            # Run in a thread with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.container.exec_run,
                    ["sh", "-c", cmd],
                    workdir="/workspace",
                    demux=True,
                ),
                timeout=timeout,
            )

            stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
            stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""

            return result.exit_code, stdout + stderr

        except TimeoutError:
            logger.warning(
                "Command timed out",
                extra={"cmd": cmd[:100], "timeout": timeout},
            )
            return -1, f"Command timed out after {timeout}s"
        except Exception as e:
            logger.exception("Command execution failed")
            return -1, f"Execution error: {e}"

    async def destroy(self) -> None:
        """Stop and remove the container, clean up temp directory."""
        if self.container:
            try:
                logger.info(
                    "Destroying sandbox container",
                    extra={"container_id": self.container.short_id},
                )
                self.container.stop(timeout=5)
                self.container.remove(force=True)
            except Exception:
                logger.exception("Error destroying container")
            finally:
                self.container = None

        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                logger.exception("Error removing temp directory")
            finally:
                self._temp_dir = None

    async def __aenter__(self) -> DockerSandbox:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.destroy()

    @staticmethod
    def _clone_repo(
        repo_url: str,
        dest: str,
        commit_sha: str | None = None,
    ) -> None:
        """Clone a git repository (runs in a thread)."""
        # Shallow clone for speed
        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            repo_url,
            dest,
        ]

        if commit_sha:
            # For specific commits, we need full clone
            cmd = ["git", "clone", repo_url, dest]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Git clone failed: {result.stderr}"
            )

        if commit_sha:
            subprocess.run(
                ["git", "checkout", commit_sha],
                cwd=dest,
                capture_output=True,
                text=True,
                check=True,
            )

    async def _ensure_image(self) -> None:
        """Ensure the sandbox Docker image exists."""
        try:
            self.client.images.get("fixforge-sandbox:latest")
            logger.info("Sandbox image found")
        except docker.errors.ImageNotFound:
            logger.info("Building sandbox image")
            # Build from the sandbox Dockerfile
            sandbox_dockerfile = (
                Path(__file__).parent.parent.parent / "sandbox.Dockerfile"
            )
            if sandbox_dockerfile.exists():
                await asyncio.to_thread(
                    self.client.images.build,
                    path=str(sandbox_dockerfile.parent),
                    dockerfile=str(sandbox_dockerfile.name),
                    tag="fixforge-sandbox:latest",
                )
            else:
                # Fallback: pull a base image
                logger.warning(
                    "No sandbox.Dockerfile found, "
                    "pulling python:3.12-slim"
                )
                await asyncio.to_thread(
                    self.client.images.pull,
                    "python:3.12-slim",
                )
                self.client.images.get("python:3.12-slim").tag(
                    "fixforge-sandbox", "latest"
                )
