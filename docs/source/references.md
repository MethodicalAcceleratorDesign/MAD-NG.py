```{eval-rst}
.. currentmodule:: pymadng
```

# References and variables

PyMAD-NG keeps large or structured objects inside MAD-NG. Python holds a reference to the object, and asks MAD-NG for a value only when you request one.

## References

Accessing or calling anything on a {class}`MAD` object returns a reference and runs nothing in Python:

```python
ref = mad.math.exp(1)
print(type(ref))     # a reference object
print(ref.eval())    # 2.718281828459045
```

References compose, and MAD-NG evaluates the whole expression:

```python
expr = mad.math.sin(1) + mad.math.cos(1)
print(expr.eval())
```

Use `.eval()` for a Python value, and `.to_df()` for a table returned by `twiss` or `survey`:

```python
df = mad.tbl.to_df()   # a TfsDataFrame if tfs-pandas is installed, else a DataFrame
```

`.to_df()` raises `TypeError` on an object that is not a table. A reference shows no properties until it is evaluated, so `dir()` on it lists only Python attributes.

## Set variables

Square brackets create or overwrite a variable in MAD-NG:

```python
mad["energy"] = 6500
mad["tbl", "flw"] = mad.twiss(sequence=mad.seq)   # several names for several results
```

`mad.energy = 6500` only sets an attribute of the Python object, and MAD-NG does not see it.

(temporary-variables-last)=
## Temporary variables (`_last`)

A call that returns a value without a name stores it in a reserved MAD-NG table, `_last[1]`, `_last[2]`, and so on, and the Python reference points to that slot. A slot is held while the Python reference is alive and freed when the reference is deleted. When all `num_temp_vars` slots (default 8) are held, the next call raises `AssertionError: Assigned too many anonymous variables`. Name a result to keep it in MAD-NG, or raise the limit with `MAD(num_temp_vars=16)`:

```python
result = mad.math.sqrt(2) + mad.math.log(10)
mad["my_var"] = result
```

## Scope

MAD-NG uses Lua scoping. A variable declared with `local` in one `mad.send` is not visible in the next:

```python
mad.send("a = 10")                    # global: persists
mad.send("local b = 20")              # local: gone after this chunk
mad.send("py:send(a)")
print(mad.recv())                     # 10
```

Prefer `local` in code you send, so the global MAD-NG namespace stays clean.
