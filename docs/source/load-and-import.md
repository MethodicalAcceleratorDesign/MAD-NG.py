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

{func}`MAD.load` and {func}`MAD.loadfile` follow the Lua functions of the same name. They compile a chunk and return a reference to it without running it, or `(None, message)` when the chunk does not compile:

```python
chunk = mad.load("return 1 + 1")      # load (ld [, source [, mode [, env]]])
chunk = mad.loadfile("setup.mad")     # loadfile (filename [, mode [, env]])
chunk, err = mad.load("return +")     # (None, '[string "return +"]:1: unexpected symbol near <eof>')
```

`filename` is required, because the standard input of MAD-NG is the pipe from Python.

## Moving from 0.9

Before 0.10.0, `load` imported a module and `loadfile` imported a file. Those calls are now `import_module` and `import_file`:

| 0.9                                  | 0.10.0                                         |
|--------------------------------------|------------------------------------------------|
| `mad.load("MADX", "lhcb1")`          | `mad.import_module("MADX", "lhcb1")`           |
| `mad.loadfile("setup.mad", "knob")`  | `mad.import_file("setup.mad", "knob")`         |
