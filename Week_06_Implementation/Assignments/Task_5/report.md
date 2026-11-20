# Task 5 report

I apologise for inconvenience! Due to some circumstances, unfortunately, I do the 5th task already after the deadline, so the API key provided the 
course is already expired, so I tried to use `gpt-6-luna` through the installed Codex CLI and its existing 
ChatGPT login. This completed the generation without an API key. The tool processed all 10 tasks in `missing_code.json` 
and successfully inserted all 10 generated method bodies. Each prompt included exactly five chunks retrieved through 
Task 4, plus the task description, original signature, imports and current class context.

The script checks the generated method's signature, parses and compiles the candidate file, and verifies that unrelated 
Python structure is unchanged before replacing the stub body. The original encoding and line endings are preserved. 
Already implemented methods are skipped on subsequent runs. No embeddings were regenerated and no tests were modified. The saved responses were checked against all ten inserted method bodies.

## Unit test results
From `Task_1/AI4SE_Playground/playground`, the suite was run with:

```powershell
python -B -m unittest discover -s tests -v
```
Actual results were **481 tests, 480 passed, 1 failed, 0 errored**. 
An independent rerun reproduced the result. The original baseline was 429 passed, 35 failed and 17 errored.

The remaining failure is 
`test_inventory.InventoryLedgerContainsLenIterTests.test_contains_present_even_if_zero_on_hand_after_commit`. 
The generated `InventoryLedger.__contains__` returns false once on-hand stock reaches zero. 
The test expects true because the SKU remains registered in the ledger. 
This exposes a conflict with the task description, which asks for positive on-hand stock. The generated method followed that description. This is a behavior mismatch, with no environment or dependency error. The generated result is retained for this evaluation; no automatic repair was performed.

## Usage

Requires Python 3.9+, the existing Task 3/4 files and a Codex installation signed in with ChatGPT. No third-party Python packages or API credentials are needed for the default Codex backend.

From Task_5:

```powershell
& 'C:\Users\Максим\AppData\Local\Programs\Python\Python311\python.exe' .\implement_missing.py --backend codex --model gpt-6-luna
```

The script finds Codex on PATH or under the Windows desktop installation. `--codex-executable PATH` overrides discovery. `--repo`, `--tasks` and `--index` override input locations. Only models listed in the assignment are accepted. The optional API backend is available separately.

`implement_task(...)` accepts a textual task and explicit file/class/method target. Generation uses one call per missing method, with no repair loop. `execution_results.json` contains the successful run's prompts, retrieved chunk references, generated methods, per-task outcomes and full test tracebacks. A later run skips implemented methods and replaces this execution log, so the current log is the evidence for the completed generation run.
