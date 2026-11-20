"""Build a persistent TF-IDF code index and retrieve chunks with cosine similarity."""

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile


MODEL = 'code-tfidf-v1'
STOP_WORDS = set('a an and are as at be by for from how i in is it of on or that the this to with'.split())


def tokens(text):
    """Split snake_case and CamelCase in both code and natural-language queries."""
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    return [word for word in re.findall(r'[a-zA-Z]+', text.lower())
            if word not in STOP_WORDS]


def embed(text, vocabulary, idf):
    counts = Counter(tokens(text))
    vector = [(1 + math.log(counts[term])) * weight if counts[term] else 0.0
              for term, weight in zip(vocabulary, idf)]
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def validate_chunks(chunks):
    if not isinstance(chunks, list) or not chunks:
        raise ValueError('Input must contain a nonempty chunks list')
    identifiers = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError('Each chunk must be an object')
        for field in ('chunk_id', 'relative_path', 'language', 'content'):
            if not isinstance(chunk.get(field), str):
                raise ValueError(f'Chunk field {field} must be a string')
        if not chunk['chunk_id'] or not chunk['relative_path']:
            raise ValueError('Chunk ID and relative path must be nonempty')
        if chunk['chunk_id'] in identifiers:
            raise ValueError(f"Duplicate chunk ID: {chunk['chunk_id']}")
        identifiers.add(chunk['chunk_id'])
        start, end = chunk.get('start_line'), chunk.get('end_line')
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError(f"Invalid line range: {chunk['chunk_id']}")


def build_index(source):
    source_bytes = source.read_bytes()
    data = json.loads(source_bytes.decode('utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('Chunk input must be a JSON object')
    chunks = data.get('chunks')
    validate_chunks(chunks)
    included = [chunk for chunk in chunks if chunk['content'].strip()]
    skipped = [chunk['chunk_id'] for chunk in chunks if not chunk['content'].strip()]
    if not included:
        raise ValueError('No nonempty chunks to embed')
    if any('embedding' in chunk for chunk in included):
        raise ValueError('Input chunks already contain an embedding field')
    texts = [chunk['relative_path'] + '\n' + chunk['content'] for chunk in included]
    document_frequency = Counter()
    for text in texts:
        document_frequency.update(set(tokens(text)))
    vocabulary = sorted(document_frequency)
    if not vocabulary:
        raise ValueError('No searchable terms found')
    idf = [1 + math.log((1 + len(texts)) / (1 + document_frequency[term]))
           for term in vocabulary]
    return {
        'schema_version': 1,
        'model': {'name': MODEL, 'vocabulary': vocabulary, 'idf': idf,
                  'dimensions': len(vocabulary), 'normalization': 'l2',
                  'representation': 'relative_path + newline + content'},
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'source_metadata': {key: value for key, value in data.items() if key != 'chunks'},
        'skipped_empty_chunks': skipped,
        'chunks': [{**chunk, 'embedding': embed(text, vocabulary, idf)}
                   for chunk, text in zip(included, texts)],
    }


def validate_index(index):
    """Reject incompatible models, corrupt dimensions and invalid vector values."""
    if not isinstance(index, dict) or index.get('schema_version') != 1:
        raise ValueError('Unsupported index format')
    model = index.get('model')
    if not isinstance(model, dict) or model.get('name') != MODEL:
        raise ValueError('Unsupported embedding model; rebuild the index')
    vocabulary, idf = model.get('vocabulary'), model.get('idf')
    if (not isinstance(vocabulary, list) or not vocabulary
            or not all(isinstance(term, str) and term for term in vocabulary)
            or vocabulary != sorted(set(vocabulary))):
        raise ValueError('Invalid model vocabulary')
    dimensions = len(vocabulary)
    if (type(model.get('dimensions')) is not int or model['dimensions'] != dimensions
            or not isinstance(idf, list) or len(idf) != dimensions
            or model.get('normalization') != 'l2'
            or model.get('representation') != 'relative_path + newline + content'):
        raise ValueError('Inconsistent model settings or dimensions')
    if not all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in idf):
        raise ValueError('Invalid IDF weights')
    validate_chunks(index.get('chunks'))
    for chunk in index['chunks']:
        vector = chunk.get('embedding')
        if not isinstance(vector, list) or len(vector) != dimensions:
            raise ValueError(f"Embedding dimension mismatch: {chunk['chunk_id']}")
        if not all(type(value) in (int, float) and math.isfinite(value) and value >= 0
                   for value in vector):
            raise ValueError(f"Invalid embedding values: {chunk['chunk_id']}")
        if not math.isclose(sum(value * value for value in vector), 1.0, abs_tol=1e-8):
            raise ValueError(f"Embedding must have unit norm: {chunk['chunk_id']}")


def save_index(index, destination):
    """Replace the old index only after writing the complete new JSON file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=destination.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(index, temporary, ensure_ascii=False, indent=2, allow_nan=False)
            temporary.write('\n')
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def match_embedding(index, task_embedding, n=3, *, positive_only=False):
    """Rank stored chunks against a nonzero vector in the saved model's space.

    Return min(n, chunk_count) results unless positive_only is requested.
    The caller must use this index's vocabulary and IDF coordinate system.
    """
    validate_index(index)
    if type(n) is not int or n < 1:
        raise ValueError('n must be a positive integer')
    if not isinstance(task_embedding, (list, tuple)) or not task_embedding:
        raise ValueError('Input embedding must be a nonempty list or tuple')
    if len(task_embedding) != index['model']['dimensions']:
        raise ValueError(f"Input embedding must have {index['model']['dimensions']} dimensions")
    if not all(type(value) in (int, float) and math.isfinite(value) and value >= 0
               for value in task_embedding):
        raise ValueError('TF-IDF input embedding must contain finite nonnegative numbers')
    scale = max(task_embedding)
    if scale == 0:
        raise ValueError('Input embedding must have a nonzero norm')
    # Scaling first avoids overflow/underflow for non-unit input vectors.
    scaled = [value / scale for value in task_embedding]
    norm = math.sqrt(sum(value * value for value in scaled))
    query_vector = [value / norm for value in scaled]
    results = []
    for chunk in index['chunks']:
        score = sum(left * right for left, right in zip(query_vector, chunk['embedding']))
        score = min(1.0, max(0.0, score))
        if positive_only and score <= 0:
            continue
        results.append({**{key: value for key, value in chunk.items() if key != 'embedding'},
                        'score': score})
    return sorted(results, key=lambda result: (-result['score'], result['chunk_id']))[:n]


def search(index, query, top_k=3):
    validate_index(index)
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Query must be a nonempty string')
    if type(top_k) is not int or top_k < 1:
        raise ValueError('top_k must be a positive integer')
    model = index['model']
    query_vector = embed(query, model['vocabulary'], model['idf'])
    if not any(query_vector):
        return []
    return match_embedding(index, query_vector, top_k, positive_only=True)


def main():
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build', help='Fit and save embeddings from Task 2')
    build.add_argument('--chunks', type=Path, default=directory.parent / 'Task_2/chunks.json')
    build.add_argument('--index', type=Path, default=directory / 'embeddings.json')
    retrieve = commands.add_parser('search', help='Search a previously saved index')
    retrieve.add_argument('query')
    retrieve.add_argument('--top-k', type=int, default=3)
    retrieve.add_argument('--index', type=Path, default=directory / 'embeddings.json')
    arguments = parser.parse_args()
    try:
        if arguments.command == 'build':
            if arguments.chunks.resolve() == arguments.index.resolve():
                raise ValueError('Index output must differ from input chunks')
            index = build_index(arguments.chunks)
            validate_index(index)
            save_index(index, arguments.index)
            print(f"Saved {len(index['chunks'])} embeddings, "
                  f"{index['model']['dimensions']} dimensions to {arguments.index}")
            print(f"Skipped {len(index['skipped_empty_chunks'])} empty chunks")
        else:
            index = json.loads(arguments.index.read_text(encoding='utf-8'))
            results = search(index, arguments.query, arguments.top_k)
            print(json.dumps({'query': arguments.query, 'results': results},
                             ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, UnicodeError, ValueError, OverflowError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
