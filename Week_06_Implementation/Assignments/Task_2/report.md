# Design Decisions
The inspected repository contains 13 Python package files in `playground/playground` and 14 Python test files in 
`playground/tests`, plus `.gitignore`. Included `.py` files from both directories because tests describe expected 
behaviour for later coding tasks. Other files were skipped.

Each chunk contains at most 80 lines and stays within one file. When a file continues, prefer the last blank-line 
boundary after the first half of the window; otherwise split at 80 lines. This usually keeps small methods or tests 
together without introducing a parser. Use zero overlap so every included line appears exactly once. Larger blocks can 
still be split, imports and class headers may be left in another chunk, and line counts do not guarantee a token budget.
This is a simple first chunking stage.

Each chunk stores a relative POSIX path, deterministic path-plus-index ID, Python language label, one-based inclusive 
line numbers, and source content. Python encoding declarations are respected; line endings are normalised to LF. 
Read/encoding failures, binary NUL content, unsupported types and empty files are recorded as skips. The JSON also 
records settings, file lists and counts. No original source files are modified.

# Implementation and Usage

`chunk_repository.py` uses only the Python standard library. It walks the repository in sorted order, reads Python 
files, splits them into contiguous chunks, checks exact reconstruction, and saves `chunks.json` alongside the script. 
Default paths are relative to the script, so execution works from any current directory.

From Task_2, run with Python 3:

```powershell
python chunk_repository.py
```

Executed successfully on the actual repository: 26 nonempty files processed, 69 chunks generated. 
Representative generated chunk `playground/playground/exceptions.py::1` covers lines 1-56.
The complete chunk, including the other exception classes, is stored in `chunks.json`.
