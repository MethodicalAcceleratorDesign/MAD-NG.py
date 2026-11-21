# pymadng reference

## MAD(...)
`MAD(mad_path=None, py_name="py", raise_on_madng_error=True, debug=False, stdout=None, redirect_stderr=False, num_temp_vars=8, ipython_use_jedi=False)`
- Starts `mad` as a subprocess and imports `element sequence mtable twiss beta0 beam survey object track match` from `MAD` into Lua globals. Anything else: `mad.load("MAD", "damap", "matrix")` or `local x in MAD` inside a chunk.
- `stdout=` path or file: MAD's prints and error tracebacks go there. `debug=True` records every sent chunk (`mad.history()`; empty otherwise) and logs the byte stream.
- Use `with MAD() as mad:` or `mad.close()`. One process per thread/worker.

## Sending
| Call | What MAD receives |
|---|---|
| `mad.send("lua code")` | runs the chunk (non-blocking for Python) |
| `mad.send(value)` | data for a `py:recv()` **already pending** in an earlier chunk; otherwise MAD dies (`bad argument #1 to 'load' (function expected, got table)`) |
| `mad["x"] = v`, `mad.send_vars(x=v, y=w)` | `x = py:recv()` then the binary value (bit-exact) |
| `mad["a", "b"] = mad.twiss(...)` | multiple assignment; calls `len()` on the result (a round trip) |
| `mad.psend("code")` | protected send; only differs from `send` when `raise_on_madng_error=False` |
| `mad.send_tpsa(monos_uint8_2d, coefs)` | a Lua **table** `{[i]=mono_string, [mono_string]=coef}`, not a TPSA |
| `mad.send_range(a, b, n)`, `send_logrange` | MAD range objects |
| `mad.evaluate_in_madx_environment("kqf = 0.3")` | `MADX:open_env() ... MADX:close_env()` |
| `mad.loadfile("/abs/file.mad", "name")` | `require` the file and bind the named members |
Python → Lua types: `float`/`np.float64` → number (binary), `int` < 2³¹ → integer, `bool`, `None` → nil, `str` → string **when sent as data**, `list`/`tuple` → table (Python index 0 = Lua 1), `dict` → table, `complex`, 2D `float64`/`complex128`/`int32` arrays → matrix/cmatrix/imatrix (`(n,1)` = vector), `range` → irange. 1D arrays are rejected, **after** `name = py:recv()` was already sent: MAD is left waiting, the next chunk is consumed as the value and the session breaks (BrokenPipeError). Always `reshape(-1, 1)` first.

## Calling MAD functions/commands from Python
- `mad.twiss(sequence=mad.lhcb1, method=6)`, `mad.MAD.matrix(2)`, `mad.MADX.load("'/abs/file.seq'")`: returns a `_last[i]` reference immediately (asynchronous).
- Argument rules: a Python **string is Lua code** (`"MADX.lhcb1"`, `"'proton'"` for a Lua string, `"\\t -> t.q1"` for a lambda); numbers/arrays/lists go binary via `py:recv()`; `MadRef`s by name; dicts/lists of these are built recursively.
- Methods: `mad.tws.write(...)`, `mad.seq.select(...)` pass the parent as `self` automatically.
- Anonymous results hold one of `num_temp_vars` (8) `_last` slots until the Python object is garbage-collected; the 9th raises "Assigned too many anonymous variables". Assign into MAD (`mad["tws", "flw"] = ...`) instead of keeping many `_last` refs.

## Receiving
| Call | Result |
|---|---|
| `mad.recv()` | next `py:send(...)` value; exactly one per `py:send` |
| `mad.recv("lua_name")` | needed when the value is a table/object/damap/function (sent as a reference) |
| `mad.x`, `mad["x"]`, `mad.recv_vars("x", "y")` | value(s) of Lua expressions (one round trip each) |
| `mad.recv_vars("t", shallow_copy=True)` | plain Lua table → Python list/dict |
| `mad.eval("1+1")` | evaluates an expression via a `_last` slot |
| `mad.recv_and_exec(env)` | receives a string and `exec`s it in Python with `mad` and `np` in scope |
Lua → Python: numbers → `np.float64`, integers → `np.int32`, vectors/matrices → 2D numpy (`(n,1)`; `.ravel()`), complex → complex, TPSA → `(monomials uint8 (nterms, nv), coefficients)`, ranges → numpy, tables (`py:send(t, true)`) → list/dict, anything else (damap, mtable, sequence, element, function) → `MadRef`/`MadObject`/`MadFunc`.

## MadRef / MadObject
- Attribute/index access is lazy: `mad.tws.q1`, `mad.lhcb1["IP5"]`, `ref[0]` (Python 0 → Lua 1). Each access is a round trip.
- `ref.eval()` → value (shallow copy); `len(ref)` → `#ref`; arithmetic `ref + x` builds a new `_last` ref in MAD.
- Assignment: `mad.lhcb1.beam = mad.beam(...)`, `ref["key"] = value`.
- `mtable.to_df(columns=None, force_pandas=False)`: `tfs.TfsDataFrame` (headers in `.headers`) if tfs is installed, else pandas (headers in `.attrs`). Works for string columns (`name`) that stay references otherwise. Sends columns as vectors (fast).
- `mad.create_deferred_expression(k1="MADX.kqf*2")`: a deferred table; `dq.k1` follows `MADX.kqf` (checked: 0.5 → 1).
- `mad.globals()` lists Lua globals; `dir(ref)` lists keys.

## Errors
- With `raise_on_madng_error=True` (default) a Lua error makes the **next** `recv` raise `RuntimeError("MAD Errored (see the MAD error output)")`; the traceback (`***pymad.run: [string "..."]:1: ...`) goes to MAD's stdout/stderr.
- Chunks sent after the failing one still run and their messages stay queued: after catching the error, the next `recv` returns the next queued message. Either restart the process or send a sentinel and read up to it.

## Patterns
- Streaming during a long command (live plots): see SKILL.md.
- Bulk results: compute in one Lua chunk and `py:send` matrices once; avoid per-element attribute access from Python.
