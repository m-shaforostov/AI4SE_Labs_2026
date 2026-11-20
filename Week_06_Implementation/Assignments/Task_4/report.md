# Design decisions

I reused Task 3's TF-IDF model and `embeddings.json`, which contains 69 chunks with 843-dimensional unit vectors. I extracted its ranking code into `match_embedding(index, task_embedding, n)` in `Task_3/retrieval.py`. Task 3's text search now calls that shared function. `Task_4/matching.py` provides the file-loading wrapper `retrieve(task_embedding, n, index_path)` and a small command-line interface.

Matching uses cosine similarity. The input vector is normalised before comparison, so its magnitude does not affect ranking. Stored vectors are already normalised and validated, so their dot product gives cosine similarity. Results are sorted by descending score, with chunk ID breaking ties, and include the original content, path, line range, language and any additional metadata. The vector itself is omitted from results.

Direct matching returns exactly `min(n, number_of_chunks)` results, including zero-score matches when needed. Such matches have no shared terms. Task 3's existing text search keeps its positive-score filter. Empty/invalid vectors, wrong dimensions, negative or nonfinite TF-IDF values, zero norms and invalid n values are rejected. Missing, empty or malformed storage is reported as an error. A task description with no vocabulary matches also produces a zero-vector error in the Task 4 CLI.

An external input vector must use this saved vocabulary and IDF coordinate order. Equal dimensions alone cannot prove model compatibility. Retrieval remains lexical and may miss synonyms. A linear scan is sufficient for this small index.

# Usage and verification

Requires Python 3.9+ and the existing sibling Task_3 folder. No additional packages or configuration are needed. From Task_4:

```powershell
python matching.py --task "Reserve inventory stock and release the reservation if it is not committed" -n 3
python matching.py --embedding task_embedding.json -n 3
```

The supplied `task_embedding.json` is a JSON array of 843 values generated from `Calculate bulk discount pricing for an order total` using the saved Task 3 model. For other embedding files, use that same model and coordinate order. The default index is `../Task_3/embeddings.json`; override it with `--index PATH`. Paths to the default storage resolve relative to the script. Results are printed as JSON, including full chunk content. On this computer the installed interpreter can be invoked explicitly:

```powershell
& 'C:\Users\Максим\AppData\Local\Programs\Python\Python311\python.exe' .\matching.py --task 'Calculate bulk discount pricing for an order total' -n 3
```

Python integration from Task_4:

```python
from matching import embed_task, load_index, retrieve, TASK_3_DIRECTORY

index = load_index(TASK_3_DIRECTORY / 'embeddings.json')
vector = embed_task(index, 'Calculate bulk discount pricing for an order total')
results = retrieve(vector, n=3)
```

Actual top-three results for the reservation query:

| File | Chunk | Lines | Score |
| --- | --- | --- | --- |
| playground/playground/inventory.py | 2 | 78-155 | 0.340712 |
| playground/tests/test_inventory.py | 2 | 81-160 | 0.319751 |
| playground/tests/test_inventory.py | 4 | 240-318 | 0.311494 |

These contain reservation release/commit logic and inventory tests. For `Calculate bulk discount pricing for an order total`:

| File | Chunk | Lines | Score |
| --- | --- | --- | --- |
| playground/tests/test_pricing.py | 2 | 80-156 | 0.397941 |
| playground/tests/test_pricing.py | 3 | 157-168 | 0.386113 |
| playground/tests/test_orders.py | 3 | 155-232 | 0.340387 |

These cover bulk-discount thresholds, pricing edge cases and order totals. Both queries returned three correctly sorted results. Scores matched an independent cosine calculation and every result's content and metadata matched its stored chunk. Both CLI input modes passed. Requests for 1 and 1000 results returned 1 and 69 respectively. Checks also passed for self-matching, scaled vectors, zero-score filling, invalid embeddings/n, missing or malformed storage and unknown query words. Task 3's existing search retained its rankings and the saved index hash stayed unchanged.
