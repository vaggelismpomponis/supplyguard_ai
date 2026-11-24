"""Upload the 105 held-out cases to LangSmith as a dataset (#83).

Usage:
    python -m eval.upload_dataset            # upload
    python -m eval.upload_dataset --dry-run  # validate only, no network

Reads LANGSMITH_API_KEY and LANGSMITH_ENDPOINT from .env. The dataset name defaults to
"supplyguard-eval-105" and can be changed with LANGSMITH_DATASET. If the dataset already exists
the script stops instead of adding duplicate examples; delete or rename it to refresh it.
"""

import argparse
import os
import sys
from collections import Counter

from eval.dataset import CASES_PATH, REPO_ROOT, load_examples

DEFAULT_DATASET_NAME = "supplyguard-eval-105"
DESCRIPTION = (
    "SupplyGuard AI: 105 held-out disruption cases (MC-17 reference incident, impact, ambiguity, "
    "prompt injection, follow-ups, restart, policy) with expected outputs for the evaluators."
)


def dataset_name() -> str:
    return os.environ.get("LANGSMITH_DATASET", DEFAULT_DATASET_NAME)


def main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="validate the file, do not upload")
    args = parser.parse_args()

    examples = load_examples()
    name = dataset_name()
    counts = Counter(e["metadata"]["category"] for e in examples)
    print(f"Loaded {len(examples)} examples from {CASES_PATH.relative_to(REPO_ROOT)}")
    for category, n in sorted(counts.items()):
        print(f"  {category:<26}{n:>4}")
    if args.dry_run:
        print(f"Dry run: would upload to dataset {name!r}")
        return 0

    if not os.environ.get("LANGSMITH_API_KEY", "").strip() or os.environ[
        "LANGSMITH_API_KEY"
    ].startswith("your_"):
        print("LANGSMITH_API_KEY is not set (see .env.example).", file=sys.stderr)
        return 1

    from langsmith import Client

    client = Client()
    if client.has_dataset(dataset_name=name):
        print(f"Dataset {name!r} already exists; not uploading duplicates.", file=sys.stderr)
        return 1

    dataset = client.create_dataset(name, description=DESCRIPTION)
    client.create_examples(
        dataset_id=dataset.id,
        inputs=[e["inputs"] for e in examples],
        outputs=[e["outputs"] for e in examples],
        metadata=[e["metadata"] for e in examples],
    )
    print(f"Created dataset {name!r} with {len(examples)} examples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
