---
name: pymadng
description: Drive MAD-NG from Python with pymadng (MAD() process, send/recv, mad.twiss/track returning mtables, to_df, send_vars/recv_vars, assignment by Lua expression, MadRef objects, error handling, one process per worker). Use for any Python code that talks to MAD-NG.
---

# pymadng

`pip install pymadng` (ships a `mad` binary; use another with `MAD(mad_path="/abs/mad")`). Source and docs: https://github.com/MethodicalAcceleratorDesign/MAD-NG.py, https://pymadng.readthedocs.io. For Lua semantics see the MAD-NG manual: https://madx.web.cern.ch/releases/madng/html/.

Full reference (every call, type mapping, references, errors): `reference.md` next to this file.

## Core API
```python
from pymadng import MAD
with MAD(stdout="/abs/path/mad.log") as mad:     # context manager closes the process
    mad.send('MADX:load("/abs/lhc.seq")')
    mad.send('MADX.lhcb1.beam = beam {particle="proton", energy=6800.938}')
    mad["tws", "flw"] = mad.twiss(sequence="MADX.lhcb1", method=6, chrom=True)
    df = mad.tws.to_df()                  # tfs DataFrame; headers in df.headers (q1, dq1, ...)
    mad.send_vars(kqf=0.3)                # Python -> MAD globals
    q1 = mad.recv_vars("tws.q1")          # one name -> scalar, several -> tuple
    mad.send("py:send(MADX.lhcb1['MQ.12R1.B1'].k1)"); k1 = mad.recv()
    mad["seq['QF'].k1"] = 0.31            # assignment by Lua expression
    mad.import_module("MAD", "damap", "matrix", "vector")   # import names into Lua globals
```
- `mad.send(str)` runs Lua; `mad.recv()` reads each `py:send(...)` (`py` = `mad.py_name`). Exactly one `recv` per `py:send`, or the pipe desyncs. `py:send(tbl, true)` sends a Lua table as a dict/list.
- Bit-exact numbers: `mad.send(f"x = {mad.py_name}:recv()").send(value)` instead of formatting floats into strings. numpy arrays and lists go as MAD matrices/vectors.
- Attribute access (`mad.MADX.kqf`, `mad.tws.q1`) costs one round-trip each: batch work into one Lua chunk and send arrays back once.
- `mad.twiss(...)` / `mad.track(...)` kwargs map 1:1 to MAD-NG attributes; sequence names as strings; Lua lambdas as `"\\t -> t.q1"`.
- Call arguments: a Python **string is Lua code** (`sequence="MADX.lhcb1"`, Lua string literal `particle="'proton'"`), numbers / numpy arrays / lists go through `py:recv()` (binary, bit-exact), `None` → `nil`, `True` → `true`, dicts → Lua tables, `MadRef`s by name.
- Never format numbers into Lua code (`f"... - {x!r}"`): text loses nothing only by luck, and numpy scalars print as `np.float64(...)` (Lua error "attempt to index global 'np'"). Keep values in MAD (compute them in Lua) or `mad.send_vars(name=value)`, and reference the name in lambdas.

## Receiving
- Lua tables come back as **references** (`MadRef`); `recv_vars(name, shallow_copy=True)` / `py:send(t, true)` copies plain tables. Non-numeric mtable columns (`name`) stay references even then: use `tbl.to_df(columns=["name", "s"])`.
- Numeric mtable columns and vectors arrive as `(n, 1)` numpy arrays: `.ravel()`.
- `mtbl.name` is the table's name, not the column.
- Lua globals starting with `_` can't be read: `mad["_trk"]` raises `ValueError: Cannot retrieve private variables from MAD-NG`. Name them without the underscore.
- `py:send(tbl)` without `true` on a plain Lua table, then a bare `mad.recv()`, fails: `AssertionError: Reference must have a variable to reference to`. Use `py:send(tbl, true)`.
- `py:send(tbl, true)` is shallow: a table of tables still fails the same way on the inner tables. Send flat lists (one `send` per column) instead.
- `mad["mtbl"].to_df(columns=[..., "id", "turn"])` gives float `id`/`turn`; cast with `.astype(int)`.

## Streaming data during a long command (live plots, progress)
```python
mad.send('function cmd () local tw = twiss{...}; py:send({tw.s, tw.beta11}, true); return tw end')
result = mad.match(command=mad.cmd, variables=[...], equalities=[...])   # returns at once (async)
mad.send(f"{mad.py_name}:send(nil)")                                     # sentinel, queued after match
while (msg := mad.recv()) is not None:                                   # one message per command call
    update_plot(*msg)
mad["status", "fmin", "ncall"] = result                                  # unpack only AFTER the loop
```
- `mad[...] = mad.match(...)` before the loop does a `len()` round trip and reads a streamed message instead ("'list' object cannot be interpreted as an integer").

## Errors
- Lua errors raise `RuntimeError("MAD Errored (see the MAD error output)")` on the next `recv`; the real message (`***pymad.run: [string "..."]:16: ...`) is in MAD's output. Send `stdout=` to a file and read it.
- Completion check: `mad.send(f"{mad.py_name}:send('success')")` then assert `mad.recv() == 'success'`.

## Processes
- One MAD process per worker/process; never share one between threads. Always close (`with` or `.close()`).
- Point `stdout=` at a log file, not the terminal, in parallel runs.

## Pitfalls
- Never format floats into Lua source (`f"volt={v:.16e}"`): send them with `mad.send(value)` and read `py:recv()` in the script.
- A 2-D numpy array sent with `mad.send` becomes a MAD `matrix`; `m[i]` is linear row-major and returns a number (`col[i]`, never `col[i][1]`).
- Element names are upper case after `MADX:load`; Lua patterns are case sensitive and `.` is a wildcard.
- A Lua pattern (e.g. `^BR3%.BPM.*3$`) is not a Python regex: `re.match` with it silently matches nothing. Translate (`%.`→`\.`, `%d/%a/%w/%s/%l/%u`) before filtering names in Python.
- `mad["a","b"] = mad.track(...)` fails ("Incorrect number of values to unpack") when particles are lost (extra returns). Use `mad.send("py_trk = track{...}")`, then `mad.py_trk.to_df()` (`to_df` is Python-side only).
- Don't share one `.mad` translation cache file across parallel loaders (they race on the file).

## Verified transfer rules (pymadng 0.9.6 and 0.10.0)
- **Order matters:** non-string data (`send_tpsa`, arrays, numbers) must be consumed by a `py:recv()` in a chunk sent **before** it. Data sent with no pending `py:recv()` is read as code and the MAD process dies ("bad argument #1 to 'load' (function expected, got table)").
- numpy: only **2D** arrays are sent (`arr.reshape(-1, 1)` for a vector; 1D raises "Matrix must be of two dimensions"). `(n,1)` arrives as a MAD vector.
- Python lists → Lua tables (`t[1]` is Python index 0); ints arrive back as `np.int32`.
- TPSA: `py:send(tpsa)` → Python `(monomials uint8 2D, coefficients)`. `mad.send_tpsa(monos, coefs)` arrives in Lua as a **table** (`t[i]` = monomial string, `t[mono]` = coefficient), not a TPSA: rebuild with `tpsa:set`.
- Damaps, objects, functions arrive as references: `mad.recv("lua_name")` (a bare `recv()` asserts "Reference must have a variable").
- Anonymous results (`mad.MAD.matrix(2)`, `mad.twiss(...)` unassigned) occupy one of `num_temp_vars=8` `_last` slots until the Python ref is deleted; the 9th raises "Assigned too many anonymous variables". Assign into MAD (`mad["x"] = ...`) for long-lived values.
- After a MAD error the queue can desync: messages from chunks sent after the failing one are still in the pipe (`mad.eval("1+1")` returned a stale `1`). Restart the process or drain until a known sentinel.
- `mad.send_vars(name=np.array(...))` with a 1-D array fails ("Matrix must be of two dimensions"): send `mad.send("v = py:recv()").send(arr.reshape(-1, 1))`.
- `mad.send(...)` returns the MAD object: end a notebook cell with `;` to avoid printing it.
- Start with `MAD(stdout=log, redirect_stderr=True)` so MAD-NG's messages (match tables, warnings) go to the log file; use one log per run (concurrent runs writing the same `mad.log` overwrite each other).
- Lua `local` names do not survive between `mad.send` chunks: use globals or `mad.load("MAD", "twiss", "track", ...)`; `mad.load("MAD.element", "quadrupole", ...)` for element classes.
- A MAD process started by `jupyter nbconvert` stays alive until the kernel is shut down: kill orphaned `ipykernel` / `mad_Linux` processes (by PID) after interrupted notebook runs.
