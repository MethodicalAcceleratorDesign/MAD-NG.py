#!/usr/bin/env bash
set -euo pipefail

# Builds MAD-NG third-party *static* libraries into: ./bin/linux
#
# This script is intentionally "fill-in friendly": override variables via env
# or interactively when prompted.
#
# Example:
#   ./tools/build_madng_deps_linux.sh
#
# Outputs (matching historical `my_lib`):
#   bin/linux/libluajit.a
#   bin/linux/liblfs.a
#   bin/linux/liblpeg.a
#   bin/linux/liblapack.a
#   bin/linux/librefblas.a
#   bin/linux/libfftw3.a
#   bin/linux/libnfft3.a
#   bin/linux/libnlopt.a

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OS_TAG="linux"
BIN_DIR="${ROOT}/bin/${OS_TAG}"
LIB_DIR="${ROOT}/lib"

JOBS="${JOBS:-}"
CC="${CC:-}"
CXX="${CXX:-}"
FC="${FC:-}"
AR="${AR:-}"
RANLIB="${RANLIB:-}"

LUAJIT_REF="${LUAJIT_REF:-mad-patch}"
LUAJIT_REPO="${LUAJIT_REPO:-https://github.com/MethodicalAcceleratorDesign/LuaJIT.git}"

LFS_REF="${LFS_REF:-}"
LFS_REPO="${LFS_REPO:-https://github.com/MethodicalAcceleratorDesign/luafilesystem.git}"

LPEG_VERSION="${LPEG_VERSION:-1.1.0}"
FFTW_VERSION="${FFTW_VERSION:-3.3.10}"
NFFT_VERSION="${NFFT_VERSION:-3.5.3}"
NLOPT_REF="${NLOPT_REF:-v2.7.1}"
LAPACK_REF="${LAPACK_REF:-v3.12.1}"

prompt_default() {
  local var_name="$1"
  local prompt="$2"
  local default="$3"
  local current="${!var_name:-}"

  if [[ -n "${current}" ]]; then
    return 0
  fi

  local reply=""
  read -r -p "${prompt} [${default}]: " reply || true
  if [[ -z "${reply}" ]]; then
    reply="${default}"
  fi
  printf -v "${var_name}" "%s" "${reply}"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

fetch_tarball() {
  local url="$1"
  local out="$2"
  if [[ -f "${out}" ]]; then
    return 0
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail "${url}" -o "${out}"
  else
    need_cmd wget
    wget -O "${out}" "${url}"
  fi
}

ensure_dirs() {
  mkdir -p "${BIN_DIR}"
  mkdir -p "${LIB_DIR}"
}

build_luajit() {
  echo "== LuaJIT (${LUAJIT_REF}) =="
  need_cmd git
  need_cmd make

  local dir="${LIB_DIR}/luajit"
  if [[ ! -d "${dir}/.git" ]]; then
    git clone "${LUAJIT_REPO}" "${dir}"
  fi
  ( cd "${dir}"
    git fetch --all --tags
    git checkout "${LUAJIT_REF}"
    git pull --ff-only || true
    make clean
    make -j"${JOBS}" amalg PREFIX="$(pwd)"
    make install PREFIX="$(pwd)"
    cp -f src/libluajit.a "${BIN_DIR}/libluajit.a"
  )
}

build_lfs() {
  echo "== LuaFileSystem ${LFS_REF:+(${LFS_REF})} =="
  need_cmd git
  need_cmd make

  local dir="${LIB_DIR}/lfs"
  if [[ ! -d "${dir}/.git" ]]; then
    git clone "${LFS_REPO}" "${dir}"
  fi
  ( cd "${dir}"
    git fetch --all --tags
    git pull --ff-only || true
    if [[ -n "${LFS_REF}" ]]; then
      git checkout "${LFS_REF}" || git checkout -B "${LFS_REF}" "origin/${LFS_REF}"
    fi
    make clean || true
    make -j"${JOBS}" AR="${AR}" lfs.a
    cp -f liblfs.a "${BIN_DIR}/liblfs.a"
  )
}

build_lpeg() {
  echo "== LPeg (${LPEG_VERSION}) =="
  need_cmd make
  need_cmd sed
  need_cmd ar

  local tar="lpeg-${LPEG_VERSION}.tar.gz"
  local url="http://www.inf.puc-rio.br/~roberto/lpeg/${tar}"
  local tar_path="${LIB_DIR}/${tar}"
  local src_dir="${LIB_DIR}/lpeg-${LPEG_VERSION}"
  local dir="${LIB_DIR}/lpeg"

  if [[ ! -d "${src_dir}" ]]; then
    fetch_tarball "${url}" "${tar_path}"
    ( cd "${LIB_DIR}" && tar xzf "${tar}" )
  fi
  if [[ ! -e "${dir}" ]]; then
    ln -s "lpeg-${LPEG_VERSION}" "${dir}"
  fi

  local luajit_inc="${LIB_DIR}/luajit/include/luajit-2.1"
  local luajit_lib="${LIB_DIR}/luajit/lib/libluajit-5.1.a"
  if [[ ! -f "${luajit_lib}" ]]; then
    echo "LuaJIT static library not found at ${luajit_lib}" >&2
    echo "Run LuaJIT step first (or adjust paths)." >&2
    exit 1
  fi

  ( cd "${dir}"
    if [[ ! -f makefile.mad.orig ]]; then
      cp -f makefile makefile.mad.orig
    else
      cp -f makefile.mad.orig makefile
    fi
    sed -i -E \
      -e "s|^[#[:space:]]*LUADIR[[:space:]]*=.*|LUADIR = ${luajit_inc}|" \
      -e "s|^[#[:space:]]*LUALIB[[:space:]]*=.*|LUALIB = ${luajit_lib}|" \
      -e "s|^[#[:space:]]*COPT[[:space:]]*=.*|COPT = -O3|" \
      makefile
    make clean || true
    make -j"${JOBS}" CC="${CC}" LUADIR="${luajit_inc}" lpvm.o lpcap.o lptree.o lpcode.o lpprint.o lpcset.o
    "${AR}" -r liblpeg.a lpvm.o lpcap.o lptree.o lpcode.o lpprint.o lpcset.o
    "${RANLIB}" liblpeg.a
    cp -f liblpeg.a "${BIN_DIR}/liblpeg.a"
  )
}

build_lapack() {
  echo "== LAPACK (${LAPACK_REF}) =="
  need_cmd git
  need_cmd make

  local dir="${LIB_DIR}/lapack"
  if [[ ! -d "${dir}/.git" ]]; then
    git clone https://github.com/Reference-LAPACK/lapack "${dir}"
  fi
  ( cd "${dir}"
    git fetch --all --tags
    git checkout "${LAPACK_REF}"
    cp -f make.inc.example make.inc
    # Ensure PIC (LAPACK can be linked into shared objects, depending on MAD build)
    sed -i \
      -e 's/^\(CFLAGS[[:space:]]*=[[:space:]]*.*\)$/\1 -fPIC/' \
      -e 's/^\(FFLAGS[[:space:]]*=[[:space:]]*.*\)$/\1 -fPIC/' \
      -e 's/^\(FFLAGS_NOOPT[[:space:]]*=[[:space:]]*.*\)$/\1 -fPIC/' \
      make.inc || true
    make clean
    make -j"${JOBS}" lib
    cp -f liblapack.a "${BIN_DIR}/liblapack.a"
    cp -f librefblas.a "${BIN_DIR}/librefblas.a"
  )
}

build_fftw3() {
  echo "== FFTW3 (${FFTW_VERSION}) =="
  need_cmd make

  local tar="fftw-${FFTW_VERSION}.tar.gz"
  local url="https://fftw.org/${tar}"
  local tar_path="${LIB_DIR}/${tar}"
  local src_dir="${LIB_DIR}/fftw-${FFTW_VERSION}"
  local dir="${LIB_DIR}/fftw3"

  if [[ ! -d "${src_dir}" ]]; then
    fetch_tarball "${url}" "${tar_path}"
    ( cd "${LIB_DIR}" && tar xzf "${tar}" )
  fi
  if [[ ! -e "${dir}" ]]; then
    ln -s "fftw-${FFTW_VERSION}" "${dir}"
  fi

  ( cd "${dir}"
    ./configure --disable-shared CC="${CC}"
    make clean || true
    make -j"${JOBS}"
    cp -f .libs/libfftw3.a "${BIN_DIR}/libfftw3.a"
  )
}

build_nfft3() {
  echo "== NFFT3 (${NFFT_VERSION}) =="
  need_cmd make

  local tar="nfft-${NFFT_VERSION}.tar.gz"
  local url="http://www.nfft.org/download/${tar}"
  local tar_path="${LIB_DIR}/${tar}"
  local src_dir="${LIB_DIR}/nfft-${NFFT_VERSION}"
  local dir="${LIB_DIR}/nfft3"

  if [[ ! -d "${src_dir}" ]]; then
    fetch_tarball "${url}" "${tar_path}"
    ( cd "${LIB_DIR}" && tar xzf "${tar}" )
  fi
  if [[ ! -e "${dir}" ]]; then
    ln -s "nfft-${NFFT_VERSION}" "${dir}"
  fi

  ( cd "${dir}"
    ./configure --enable-all --disable-shared \
      --with-fftw3="$(pwd)/../fftw3" \
      --with-fftw3-libdir="$(pwd)/../fftw3/.libs" \
      --with-fftw3-includedir="$(pwd)/../fftw3/api" \
      CC="${CC}"
    make clean || true
    make -j"${JOBS}"
    cp -f .libs/libnfft3.a "${BIN_DIR}/libnfft3.a"
  )
}

build_nlopt() {
  echo "== NLOpt (${NLOPT_REF}) =="
  need_cmd git
  need_cmd cmake
  need_cmd make

  local dir="${LIB_DIR}/nlopt"
  if [[ ! -d "${dir}/.git" ]]; then
    git clone https://github.com/stevengj/nlopt "${dir}"
  fi

  ( cd "${dir}"
    git fetch --all --tags
    git checkout "${NLOPT_REF}"
    rm -rf build
    mkdir -p build
    cd build
    cmake -DBUILD_SHARED_LIBS=OFF -DNLOPT_CXX=OFF -DCMAKE_C_COMPILER="${CC}" ..
    make -j"${JOBS}"
    cp -f libnlopt.a "${BIN_DIR}/libnlopt.a"
  )
}

main() {
  ensure_dirs

  prompt_default JOBS "Parallel jobs (make -j)" "$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"
  prompt_default CC "C compiler (CC)" "gcc"
  prompt_default CXX "C++ compiler (CXX)" "g++"
  prompt_default FC "Fortran compiler (FC)" "gfortran"
  prompt_default AR "Archiver (AR)" "ar"
  prompt_default RANLIB "RANLIB" "ranlib"

  need_cmd "${CC}"
  need_cmd "${FC}"
  need_cmd "${AR}"
  need_cmd "${RANLIB}"
  need_cmd tar

  if ! command -v rg >/dev/null 2>&1; then
    echo "Tip: install ripgrep ('rg') for better diagnostics; continuing without it."
  fi

  echo "Root: ${ROOT}"
  echo "Lib sources: ${LIB_DIR}"
  echo "Output: ${BIN_DIR}"
  echo

  build_luajit
  build_lfs
  build_lpeg
  build_lapack
  build_fftw3
  build_nfft3
  build_nlopt

  echo
  echo "Done. Built libraries in: ${BIN_DIR}"
  ls -1 "${BIN_DIR}"
}

main "$@"
