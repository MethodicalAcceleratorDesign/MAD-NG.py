0.4.3 (2023/11/25)

Update GitHub Actions to always use the latest version of MAD-NG \
Update tests to be more robust.

0.4.2 (2023/10/18)

Add `to_df` method to objects, allowing for easy conversion to pandas dataframes. \

0.4.1 (2023/08/19)

Change the way `send_vars` and `recv_vars` work, they now use kwargs and args respectively. \
Fix bug with receiving lists. \
Allow tuples to be sent and received (they are converted to lists). \
Completely refactor the underlying process again (this time for symmetry). \
Update Documentation. \
Ensure that the binaries are included on PyPI. \
Allow multiple processes with different `__last__` objects. \
Allow receiving of multiple objects in the syntax `a, b = mad["a", "b"]` (for symmetry and simplistic). \
Set pymadng to now be in beta.

0.4.0 (2023/06/26)

Fix MADX issue
Move binaries to the bin folder \
Update MAD-NG binaries \
Rename files to start with madp_... \
Completely refactor underlying process and remove reliance on mad objects, mad strings and `__last__`, now the process is completely self contained and can be separated into MAD-NG itself.

List of changes to PyMAD-NG

0.3.9 (2023/03/08)

Fixed permissions on the MAD binaries

0.3.8 (2023/03/08)

Update MAD-NG binaries

0.3.7

Update MAD-NG binaries \
Fix bug with negative integer values \
Initialise CHANGELOG 
