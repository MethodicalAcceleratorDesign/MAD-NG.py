0.4.1 (2023/06/28)

Change the way `send_vars` and `recv_vars` work, they now use kwargs and args respectively. \
Fix bug with receiving lists \
Allow tuples to be sent and received (they are converted to lists) \
Completely refactor the underlying process again (this time for symmetry) \
Update Documentation

0.4.0 (2023/06/26)

Fix MADX issue
Move binaries to the bin folder \
Update MAD-NG binaries \
Rename files to start with madp_... \
Completely refactor underlying process and remove reliance on mad objects, mad strings and \_\_last\_\_, now the process is completely self contained and can be separated into MAD-NG itself.

List of changes to PyMAD-NG

0.3.9 (2023/03/08)

Fixed permissions on the MAD binaries

0.3.8 (2023/03/08)

Update MAD-NG binaries

0.3.7

Update MAD-NG binaries \
Fix bug with negative integer values \
Initialise CHANGELOG 