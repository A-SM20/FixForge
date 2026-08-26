"""Sandboxed execution for agent runs.

Supports:
1. Docker Sandbox (ephemeral containers with no network access, CPU/RAM caps)
2. Local Sandbox Fallback (isolated temp directory execution when Docker
   daemon is not available, e.g. on Render/cloud platforms).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DockerSandbox:
    """Ephemeral sandbox for code execution with Docker or Local fallback.

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
        self.client = None
        self.use_docker = False
        self.container = None
        self.work_dir: str | None = None
        self._temp_dir: str | None = None

        # Check if Docker is available
        try:
            import docker
            self.client = docker.from_env()
            self.client.ping()
            self.use_docker = True
            logger.info("Docker daemon connected successfully — using container sandbox")
        except Exception as e:
            self.use_docker = False
            logger.info(
                "Docker daemon not available (%s) — using isolated local filesystem sandbox",
                e,
            )

    async def start(self) -> None:
        """Clone the repo and start sandbox environment."""
        self._temp_dir = tempfile.mkdtemp(prefix="fixforge-")
        # Clone into a child directory so git doesn't fail on an existing dir
        clone_dest = os.path.join(self._temp_dir, "repo")
        self.work_dir = clone_dest

        logger.info(
            "Cloning repo",
            extra={
                "repo": self.repo_url,
                "dest": self.work_dir,
                "mode": "docker" if self.use_docker else "local",
            },
        )

        # Clone in a thread to avoid blocking the event loop
        try:
            await asyncio.to_thread(
                self._clone_repo, self.repo_url, clone_dest, self.commit_sha
            )
        except Exception as e:
            logger.warning("Git clone failed (%s) — initializing empty repo", e)
            # Create a mock minimal git repo in work_dir so agent tools don't crash
            os.makedirs(clone_dest, exist_ok=True)
            await asyncio.to_thread(self._init_fallback_repo, clone_dest)

        if self.use_docker and self.client:
            try:
                await self._ensure_image()
                self.container = self.client.containers.run(
                    image="fixforge-sandbox:latest",
                    command="sleep infinity",
                    volumes={
                        self.work_dir: {"bind": "/workspace", "mode": "rw"},
                    },
                    working_dir="/workspace",
                    network_mode="none",
                    mem_limit=self.settings.sandbox_mem_limit,
                    nano_cpus=self.settings.sandbox_cpu_limit,
                    security_opt=["no-new-privileges"],
                    detach=True,
                    remove=False,
                )
                logger.info(
                    "Sandbox container started",
                    extra={"container_id": self.container.short_id},
                )
            except Exception as e:
                logger.warning(
                    "Failed to start Docker container (%s), falling back to local mode", e
                )
                self.use_docker = False
                
                # Attempt to create a local virtualenv for isolation to avoid
                # contaminating the host python environment (e.g. on Render)
                try:
                    import subprocess
                    subprocess.run(
                        ["python", "-m", "venv", ".venv_sandbox"],
                        cwd=self.work_dir,
                        check=False,
                    )
                except Exception as venv_err:
                    logger.warning("Could not create local fallback venv: %s", venv_err)

    async def exec(
        self,
        cmd: str,
        timeout: int | None = None,
    ) -> tuple[int, str]:
        """Execute a command inside the sandbox.

        Args:
            cmd: Command to execute.
            timeout: Timeout in seconds.

        Returns:
            (exit_code, combined_output)
        """
        timeout = timeout or self.settings.sandbox_timeout

        if self.use_docker and self.container:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.container.exec_run,
                        ["sh", "-c", cmd],
                        workdir="/workspace",
                        demux=True,
                    ),
                    timeout=timeout,
                )
                out_b = result.output[0]
                err_b = result.output[1]
                stdout = out_b.decode("utf-8", errors="replace") if out_b else ""
                stderr = err_b.decode("utf-8", errors="replace") if err_b else ""
                return result.exit_code, stdout + stderr
            except TimeoutError:
                return -1, f"Command timed out after {timeout}s"
            except Exception as e:
                return -1, f"Execution error: {e}"

        # Local fallback execution inside work_dir
        venv_cmd = cmd
        if os.path.exists(os.path.join(self.work_dir, ".venv_sandbox")):
            if os.name == "nt":
                venv_cmd = f".venv_sandbox\\Scripts\\activate.bat && {cmd}"
            else:
                venv_cmd = f". .venv_sandbox/bin/activate && {cmd}"

        try:
            proc = await asyncio.create_subprocess_shell(
                venv_cmd,
                cwd=self.work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                return proc.returncode or 0, stdout + stderr
            except TimeoutError:
                proc.kill()
                return -1, f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, f"Local execution error: {e}"

    async def destroy(self) -> None:
        """Stop and remove container and clean up temp directory."""
        if self.container:
            try:
                self.container.stop(timeout=5)
                self.container.remove(force=True)
            except Exception:
                pass
            finally:
                self.container = None

        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
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
        """Clone a git repository."""
        cmd = ["git", "clone", "--depth", "1", repo_url, dest]
        if commit_sha:
            cmd = ["git", "clone", repo_url, dest]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")

        if commit_sha:
            subprocess.run(
                ["git", "checkout", commit_sha],
                cwd=dest,
                capture_output=True,
                text=True,
                check=True,
            )

    @staticmethod
    def _init_fallback_repo(dest: str) -> None:
        """Initialize an empty git repo if cloning is unavailable."""
        subprocess.run(["git", "init"], cwd=dest, capture_output=True, text=True)
        placeholder = Path(dest) / "README.md"
        placeholder.write_text("# Sandbox Workspace\n")
        subprocess.run(["git", "add", "."], cwd=dest, capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=dest, capture_output=True, text=True
        )

    async def _ensure_image(self) -> None:
        """Ensure the sandbox Docker image exists."""
        if not self.client:
            return
        import docker
        try:
            self.client.images.get("fixforge-sandbox:latest")
        except docker.errors.ImageNotFound:
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
                await asyncio.to_thread(self.client.images.pull, "python:3.12-slim")
                self.client.images.get("python:3.12-slim").tag(
                    "fixforge-sandbox", "latest"
                )
