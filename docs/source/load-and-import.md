```{eval-rst}
.. currentmodule:: pymadng
```

# Load and import files and modules

## MAD-X sequences

`MADX:load` reads a MAD-X file and writes the MAD-NG equivalent. Strings sent to MAD-NG are Lua source, so a file name needs its own quotes:

```python
mad.MADX.load("'lhc.seq'", "'lhc.mad'")
mad.import_module("MADX", "lhcb1")   # a Python name for MADX.lhcb1
```

## Modules: `import_module`

{func}`MAD.import_module` takes a module path and the names to import from it:

```python
mad.import_module("MAD.gphys", "melmcol")
```

## Files: `import_file`

{func}`MAD.import_file` runs a MAD-NG file and imports names from the table the file returns:

```python
mad.import_file("ps_ring.mad", "ps")   # ps_ring.mad ends with: return { ps = PS }
```

## `load` and `loadfile`

`mad.load` and `mad.loadfile` are MAD-NG's own Lua functions, `load (ld [, source [, mode [, env]]])` and `loadfile (filename [, mode [, env]])`, with no Python wrapper. Like every string sent to MAD-NG, each string argument is a Lua expression, so a literal needs its own quotes and a MAD-NG variable is passed bare. This is what lets a chunk, a file name or an environment come from a variable already in MAD-NG:

```python
chunk = mad.load("'return 1 + 1'")        # quoted: the Lua string  return 1 + 1
mad.send("src = 'return 2 + 2'")
chunk = mad.load("src")                   # bare: the MAD-NG variable src
chunk = mad.loadfile("'setup.mad'")
mad.load("'x = 1'", "'=chunk'", "'t'", "custom_env")()   # source name, mode, env (a MAD-NG variable)
```

Without the inner quotes, MAD-NG receives `load(return 1 + 1)` and raises a syntax error.

`loadfile` needs a filename: with none, MAD-NG reads its standard input, which is the pipe from Python, and blocks.

A compiled chunk is a reference: call it to run it, and `.eval()` brings its result to Python. A chunk that does not compile returns `nil, message`, which `.eval()` gives as `{2: message}`:

```python
mad.load("'return +'").eval()    # {2: '[string "return +"]:1: unexpected symbol near <eof>'}
```

## Moving from 0.9

Before 0.10.0, `load` imported a module and `loadfile` imported a file. Those calls are now `import_module` and `import_file`:

| 0.9                                  | 0.10.0                                         |
|--------------------------------------|------------------------------------------------|
| `mad.load("MADX", "lhcb1")`          | `mad.import_module("MADX", "lhcb1")`           |
| `mad.loadfile("setup.mad", "knob")`  | `mad.import_file("setup.mad", "knob")`         |
