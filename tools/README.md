# Building MAD-NG

`build_madng.sh <MAD-NG checkout>` builds the `mad` executable (`<checkout>/src/mad`) on Linux x86_64 or
macOS arm64. It is run by `.github/workflows/compile_madng.yml`, which is started by hand
(`workflow_dispatch`, optionally with a MAD-NG branch, tag or commit) and uploads `mad-Linux` and `mad-Darwin`.
The workflow then runs the test suite against each binary. The binaries are not published; the PyPI package
uses the released binaries.

## Linux

Uses the static archives in the MAD-NG `bin` submodule and `Makefile.lxplus`. Only LuaJIT (bytecode
compiler) is built, and the FFTW, NFFT and NLopt sources are downloaded for their headers. Needs static
`libgfortran`, `libquadmath` and `libstdc++` (`libgfortran-static`, `libquadmath-static`, `libstdc++-static`
on Rocky Linux 9).

## macOS arm64

The macOS archives in the `bin` submodule are Intel, so LuaJIT, LuaFileSystem, LPeg, FFTW, NFFT, NLopt and
LAPACK/BLAS are built from source into `$DEPS/arm64` (default `<checkout>/lib/arm64`) and copied over them.
Each archive is skipped if it already exists, so `$DEPS` can be cached. `macos_arm64.patch` changes
`Makefile.macosx` (no `-ld_classic`, no x86 SSE sources, arm64 archive check, `CPUFLAGS`) and adds a missing
`#include <stdlib.h>`. Needs Homebrew `gcc` and `cmake`. The binary is compiled with `-mcpu=apple-m1`.

## Local run

```bash
git clone --recurse-submodules https://github.com/MethodicalAcceleratorDesign/MAD-NG
JOBS=8 tools/build_madng.sh MAD-NG
```

`DEPS` and `JOBS` can be set in the environment.
