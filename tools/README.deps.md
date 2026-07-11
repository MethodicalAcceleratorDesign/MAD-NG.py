# Building MAD-NG dependencies

This directory contains the Linux dependency builder used by the MAD-NG
compile workflow. It builds static third-party libraries from source; it does
not build or publish `pymadng` itself.

## Release route

Publishing a GitHub release runs these workflows in order:

1. `python-publish.yml` calls `compile_madng.yml`.
2. The Linux job copies this script into the checked-out MAD-NG source and runs
   it. The macOS job builds its dependencies directly in the workflow.
3. Both jobs compile MAD-NG and upload a `mad` artifact.
4. The publish job installs the artifacts as
   `src/pymadng/bin/mad_Linux` and `src/pymadng/bin/mad_Darwin`, builds the
   Python distributions, and publishes them to PyPI.

To temporarily use the old pre-built-download route, set the GitHub repository
variable `PYMADNG_BUILD_MADNG_FROM_SOURCE` to `false`. Delete the variable, or
set it to any other value, to compile from source again.

## Manual Linux route

Run the script from the root of a MAD-NG checkout:

```bash
JOBS="$(nproc)" CC=gcc CXX=g++ FC=gfortran \
  AR=ar RANLIB=ranlib ./tools/build_madng_deps_linux.sh
```

If an option is omitted, the script prompts for it and suggests a default.
It downloads sources into `lib/` and writes these archives to `bin/linux/`:

- `libluajit.a`, `liblfs.a`, `liblpeg.a`
- `liblapack.a`, `librefblas.a`
- `libfftw3.a`, `libnfft3.a`, `libnlopt.a`

Source versions and repositories can be overridden with `LUAJIT_REPO`,
`LUAJIT_REF`, `LFS_REPO`, `LFS_REF`, `LPEG_VERSION`, `FFTW_VERSION`,
`NFFT_VERSION`, `NLOPT_REF`, and `LAPACK_REF`.
