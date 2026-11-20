# Design decisions
Reused the 69 chunks in `Task_2/chunks.json`, keeping their code and metadata unchanged. Coding assistant chose TF-IDF 
as a lightweight lexical embedding method because this repository has descriptive Python identifiers, docstrings and 
tests. It runs offline with the Python standard library. These vectors represent term importance; synonym-heavy queries 
can perform poorly compared with a trained semantic model.

Each document is its relative path followed by its code. The tokenizer splits snake_case and CamelCase, 
lowercase words and removes a small fixed list of common English words. A sorted vocabulary is fitted once across all 
chunks. Each vector is L2-normalised. Queries use the same tokenizer, saved vocabulary and saved IDF weights. 
Unknown query words are ignored.

`embeddings.json` stores the fitted model, 843-dimensional vectors, all original chunk fields, 
Task 2's top-level metadata, the input SHA-256 and skipped empty IDs. JSON is sufficient for 69 chunks; 
this index is 1,112,503 bytes. Search embeds only the query, scores every stored vector with cosine similarity, 
and returns the top-k positive matches with full content and metadata. For unit vectors, cosine is their dot product. 
Ties are resolved by chunk ID. No matching vocabulary produces an empty result list. Rebuild the index after changing 
the chunks or tokenizer.

The code rejects malformed inputs, duplicate IDs, unsupported model versions, nonfinite vector values and inconsistent 
dimensions. Empty chunks are skipped and recorded. Index writes use a temporary file and atomic replacement. 
Fitting or validation errors produce a clear CLI error and a nonzero exit status. The linear scan and dense JSON vectors
are practical for this repository, but storage and search costs grow with the collection.

# Implementation and usage

Requires Python 3.9+. From `Task_3` dir, run:

```powershell
python retrieval.py build
python retrieval.py search "Reserve inventory stock and release the reservation if it is not committed" --top-k 3
```

Build reads `../Task_2/chunks.json` and saves `Task_3/embeddings.json`. 
Override paths with `build --chunks PATH --index PATH` or `search QUERY --index PATH`. 
Search prints JSON containing the query and result objects with score, original code and metadata. 
