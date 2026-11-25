"""Local Docker sandbox for Deep Agents (backend checked with deepagents 0.7.35).

Setup:
    Start Docker Desktop in Linux-container mode (or Docker Engine on Linux).
    docker pull python:3.12-slim
    uv add 'deepagents==0.7.35'
    uv run --env-file .env deep_agent_local_sandbox.py

Keep the existing dependencies used by p06_reactAgents.model_config.
Only code execution is necessarily local: make_model() chooses the LLM provider.
For a fully local run, configure it to return a local tool-calling model and
turn off cloud tracing. The image and Python packages need downloading once.
"""

import subprocess
import uuid

from deepagents import create_deep_agent
from deepagents.backends.sandbox import BaseSandbox
from deepagents.backends.protocol import (
    ExecuteResponse, FileDownloadResponse, FileUploadResponse,
)


class LocalDockerSandbox(BaseSandbox):
    """Route backend operations through Docker, never a shell on the host."""

    def __init__(self):
        self.container = "deep-agent-" + uuid.uuid4().hex[:12]
        subprocess.run(
            [
                "docker", "run", "-d", "--rm", "--pull=never",
                "--name", self.container,
                "--network=none", "--memory=256m", "--cpus=1",
                "--pids-limit=64", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--read-only",
                "--user=1000:1000",
                "--tmpfs", "/workspace:rw,size=64m,uid=1000,gid=1000,mode=700",
                "--tmpfs", "/tmp:rw,size=32m,mode=1777",
                "--workdir=/workspace", "--env", "HOME=/workspace",
                "python:3.12-slim", "sleep", "1800",
            ],
            check=True, capture_output=True, text=True,
        )

    @property
    def id(self) -> str:
        return self.container

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        seconds = min(max(timeout or 30, 1), 120)
        print("\nSANDBOX COMMAND:", command)
        try:
            result = subprocess.run(
                ["docker", "exec", self.container,
                 "timeout", "--kill-after=2", str(seconds), "sh", "-c", command],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=seconds + 10,
            )
        except subprocess.TimeoutExpired:
            # Killing the Docker client alone would not stop container processes.
            self.close()
            raise RuntimeError("Sandbox timed out and was removed.") from None
        return ExecuteResponse(
            output=result.stdout + result.stderr, exit_code=result.returncode,
        )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        results = []
        for path, content in files:
            try:
                subprocess.run(
                    ["docker", "exec", "-i", self.container, "python", "-c",
                     "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                     "p.parent.mkdir(parents=True,exist_ok=True); "
                     "p.write_bytes(sys.stdin.buffer.read())", path],
                    input=content, capture_output=True, check=True, timeout=30,
                )
                results.append(FileUploadResponse(path=path))
            except (subprocess.SubprocessError, OSError):
                results.append(FileUploadResponse(path=path, error="permission_denied"))
        return results

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        results = []
        for path in paths:
            try:
                result = subprocess.run(
                    ["docker", "exec", self.container, "python", "-c",
                     "import pathlib,sys; sys.stdout.buffer.write("
                     "pathlib.Path(sys.argv[1]).read_bytes())", path],
                    capture_output=True, check=True, timeout=30,
                )
                results.append(FileDownloadResponse(path=path, content=result.stdout))
            except (subprocess.SubprocessError, OSError):
                results.append(FileDownloadResponse(path=path, error="file_not_found"))
        return results

    def close(self):
        result = subprocess.run(
            ["docker", "rm", "-f", self.container], capture_output=True, text=True,
        )
        if result.returncode and "No such container" not in result.stderr:
            print("Container cleanup failed:", result.stderr)


def main():
    from p06_reactAgents.model_config import make_model

    llm = make_model()
    sandbox = LocalDockerSandbox()
    try:
        agent = create_deep_agent(
            model=llm,
            backend=sandbox,
            system_prompt="""You are a Python assistant. Work in /workspace.
Use write_file to create code and execute to run it. Use only the Python
standard library: this container has no network access. Do not delegate.
Report actual execution output, and never claim success if execution failed.""",
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": """Create
/workspace/analysis.py. Calculate the total and average of
[120, 150, 90, 200, 140]. Assert total == 700 and average == 140.
Print both values. Run python /workspace/analysis.py and explain the output."""}]},
            config={"recursion_limit": 30},
        )
        print("\nFINAL ANSWER:\n", result["messages"][-1].content)
    finally:
        # Files are temporary and disappear when the container is removed.
        sandbox.close()


if __name__ == "__main__":
    main()
