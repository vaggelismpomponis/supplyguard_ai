"""Coding pattern: inspect -> run tests -> repair -> run tests again.

Start Docker Desktop in Linux-container mode, then:
    docker pull python:3.12-slim
    uv add 'deepagents==0.7.35'
    uv run --env-file .env coding_demo/deep_agent_coding.py

Place coding_demo beside your p06_reactAgents package.
Generated code executes in local Docker. make_model() determines the LLM provider.
The repair limit in the prompt is advisory; recursion_limit bounds graph steps.
"""
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deepagents import create_deep_agent
from p10_deep_agents.deep_agent_local_sandbox import LocalDockerSandbox
from p06_reactAgents.model_config import make_model

# Deliberately broken code, so the agent has something concrete to repair.
STARTER = "def average(values):\n    return sum(values)\n"
TESTS = '''import unittest
from stats import average

class TestAverage(unittest.TestCase):
    def test_multiple_values(self):
        self.assertAlmostEqual(average([10, 20, 30]), 20)

    def test_single_value(self):
        self.assertEqual(average([5]), 5)

    def test_negative_values(self):
        self.assertAlmostEqual(average([-2, -4]), -3)

    def test_empty_values(self):
        with self.assertRaises(ValueError):
            average([])

if __name__ == "__main__":
    unittest.main()
'''
TEST_COMMAND = "cd /workspace && python -m unittest -v test_stats"


def upload(sandbox, files):
    for result in sandbox.upload_files(files):
        if result.error:
            raise RuntimeError(f"Upload failed: {result.path}: {result.error}")


def main():
    llm = make_model()
    sandbox = LocalDockerSandbox()
    try:
        upload(sandbox, [("/workspace/stats.py", STARTER.encode()),
                         ("/workspace/test_stats.py", TESTS.encode())])
        agent = create_deep_agent(
            model=llm,
            backend=sandbox,
            system_prompt="""You are a Python coding agent. Work in /workspace.
1. Read the existing source and tests.
2. Execute the tests before changing anything and inspect failures.
3. Fix the implementation using edit_file or write_file.
4. Execute the tests again; use failures to guide further fixes.
Allow at most three repair attempts, then report any unresolved failures.
Do not change tests, install packages, or delegate. Use only the standard library.
Only claim tests passed if execute returned a successful test run.""",
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content":
                "Fix average(values) in stats.py. It must return the arithmetic "
                "mean and raise ValueError for an empty list. Run " + TEST_COMMAND}]},
            config={"recursion_limit": 40},
        )
        print("\nAGENT REPORT:\n", result["messages"][-1].content)

        # Restore the original tests and verify the final code, independently
        # of what the agent says. This is a demo check, not adversarial grading.
        upload(sandbox, [("/workspace/test_stats.py", TESTS.encode())])
        check = sandbox.execute(TEST_COMMAND)
        print("\nFINAL TEST OUTPUT:\n", check.output)
        print("Exit code:", check.exit_code)

        # Preserve the code and tests before deleting the container.
        folder = Path("coding_output") / uuid4().hex[:8]
        folder.mkdir(parents=True)
        for file in sandbox.download_files(["/workspace/stats.py", "/workspace/test_stats.py"]):
            if file.error:
                raise RuntimeError(f"Download failed: {file.path}: {file.error}")
            (folder / Path(file.path).name).write_bytes(file.content)
        print("Saved files:", folder.resolve())
        if check.exit_code != 0:
            raise RuntimeError("Final verification failed; inspect the saved implementation.")
    finally:
        sandbox.close()


if __name__ == "__main__":
    main()
