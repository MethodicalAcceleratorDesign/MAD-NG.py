# MAD-NG dependency build scripts

These scripts download/build the third-party **static** libraries MAD-NG expects, and copy the resulting `*.a` files into the OS-specific `bin/` directory (matching the historical layout in `my_lib/`).

## Linux

```bash
chmod +x tools/build_madng_deps_linux.sh
./tools/build_madng_deps_linux.sh
```

Outputs into `bin/linux/`:

- `libluajit.a`
- `liblfs.a`
- `liblpeg.a`
- `liblapack.a`
- `librefblas.a`
- `libfftw3.a`
- `libnfft3.a`
- `libnlopt.a`

## macOS

Prereqs (typical Homebrew setup):

```bash
brew install cmake gcc make automake libtool pkg-config
```

Then:

```bash
chmod +x tools/build_madng_deps_macos.sh
./tools/build_madng_deps_macos.sh
```

Outputs into `bin/macosx/` (same filenames as Linux).

## “Fill in the necessary things”

All knobs can be supplied as environment variables (no prompts), or left unset to be prompted:

- Build tools: `JOBS`, `CC`, `CXX`, `FC`, `AR`, `RANLIB`
- LuaJIT: `LUAJIT_REPO`, `LUAJIT_REF`
- LuaFileSystem: `LFS_REPO`, `LFS_REF`
- Versions/refs: `LPEG_VERSION`, `FFTW_VERSION`, `NFFT_VERSION`, `NLOPT_REF`, `LAPACK_REF`
- macOS only: `MACOSX_DEPLOYMENT_TARGET`

Example (Linux):

```bash
JOBS=16 CC=clang FC=gfortran LUAJIT_REF=mad-patch ./tools/build_madng_deps_linux.sh
```

## Header-only staging (no rebuild)

If you already have `*.a` archives in `bin/linux` or `bin/macosx`, but your build
fails on missing headers (e.g. `lua.h`, `fftw3.h`, `nlopt.h`), use:

- `tools/stage_madng_headers_linux.sh`
- `tools/stage_madng_headers_macos.sh`

They populate `lib/luajit`, `lib/nlopt`, `lib/fftw3`, `lib/nfft3` with the
expected header layout (by cloning/downloading sources, or by symlinking from
your provided include directories).
