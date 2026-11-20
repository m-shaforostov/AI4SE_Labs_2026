"""Retrieve top-n Task 3 chunks from an embedding JSON array or a task description."""

import argparse
import json
from pathlib import Path
import sys

# Task folders are siblings; reuse the existing model and ranking implementation.
TASK_3_DIRECTORY = Path(__file__).resolve().parent.parent / 'Task_3'
sys.path.insert(0, str(TASK_3_DIRECTORY))
from retrieval import embed, match_embedding, validate_index


def load_index(path):
    index = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_index(index)
    return index


def retrieve(task_embedding, n=3, index_path=TASK_3_DIRECTORY / 'embeddings.json'):
    """Load the existing index and return top-n chunks with metadata and scores."""
    return match_embedding(load_index(index_path), task_embedding, n)


def embed_task(index, description):
    """Optional text adapter using the exact saved Task 3 vocabulary and weights."""
    if not isinstance(description, str) or not description.strip():
        raise ValueError('Task description must be a nonempty string')
    model = index['model']
    return embed(description, model['vocabulary'], model['idf'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--embedding', type=Path, help='JSON file containing a numeric array')
    inputs.add_argument('--task', help='Natural-language task to embed with the saved model')
    parser.add_argument('-n', type=int, default=3, help='Number of chunks (default: 3)')
    parser.add_argument('--index', type=Path, default=TASK_3_DIRECTORY / 'embeddings.json')
    arguments = parser.parse_args()
    try:
        index = load_index(arguments.index)
        if arguments.embedding is not None:
            task_embedding = json.loads(arguments.embedding.read_text(encoding='utf-8-sig'))
        else:
            task_embedding = embed_task(index, arguments.task)
        results = match_embedding(index, task_embedding, arguments.n)
        print(json.dumps({'results': results}, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, UnicodeError, ValueError, OverflowError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
