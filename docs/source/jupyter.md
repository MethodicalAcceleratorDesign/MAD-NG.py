```{eval-rst}
.. currentmodule:: pymadng
```

# Jupyter and IPython

[`examples/ex-jupyter/ex-jupyter.ipynb`](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/blob/main/examples/ex-jupyter/ex-jupyter.ipynb) uses {class}`MAD` from a notebook; `tests/test_jupyter_output.py` runs it in a real kernel.

## Output

No `stdout=` argument is needed. The output of MAD-NG (`print`, `io.write`, warnings) appears under the cell that runs it. MAD-NG writes its output asynchronously, so a line can appear under the next cell when the first cell has already finished.

## Tab completion

Completion with jedi evaluates the objects it completes, and completing on a MAD-NG reference blocks until MAD-NG answers (3 s while a 3 s loop runs). `MAD()` therefore turns jedi off in every IPython shell, terminal and Jupyter. Completion of `mad.<name>` still works. Nested tables such as `mad.mytable.<name>` and other objects (a DataFrame, for example) lose their completions for the rest of the session. To keep jedi:

```python
mad = MAD(ipython_use_jedi=True)
```
