#!/usr/bin/env bash
set -euo pipefail

# Stage headers into the layout expected by MAD-NG's unmodified `src/Makefile`.
# The fetch/stage layout follows the documented MAD dependency build flow.
#
# Expected include paths (from `src/Makefile`):
#   -I../lib/luajit/src            -> lua.h, luajit.h, luaconf.h, lualib.h, lauxlib.h, lua.hpp
#   -I../lib/nlopt/src/api         -> nlopt.h
#   -I../lib/fftw3/api             -> fftw3.h
#   -I../lib/nfft3/include         -> nfft3.h (and friends)
#
# This script does NOT build archives; it only ensures headers exist (by
# downloading sources, or by symlinking/copying from user-provided locations).

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB_DIR="${ROOT}/lib"
BIN_DIR="${ROOT}/bin/linux"

LUAJIT_REF="${LUAJIT_REF:-mad-patch}"
LUAJIT_REPO="${LUAJIT_REPO:-https://github.com/MethodicalAcceleratorDesign/LuaJIT.git}"
LFS_REF="${LFS_REF:-v1.8.0}"
LFS_REPO="${LFS_REPO:-https://github.com/MethodicalAcceleratorDesign/luafilesystem.git}"
LPEG_VERSION="${LPEG_VERSION:-1.1.0}"

NLOPT_REF="${NLOPT_REF:-v2.7.1}"
NLOPT_REPO="${NLOPT_REPO:-https://github.com/stevengj/nlopt.git}"

FFTW_VERSION="${FFTW_VERSION:-3.3.10}"
NFFT_VERSION="${NFFT_VERSION:-3.5.3}"

# Optional: point these at already-installed headers (will be copied/symlinked)
LUAJIT_SRC_DIR="${LUAJIT_SRC_DIR:-}"   # directory containing lua.h, luajit.h, etc
NLOPT_INC_DIR="${NLOPT_INC_DIR:-}"     # directory containing nlopt.h
FFTW_INC_DIR="${FFTW_INC_DIR:-}"       # directory containing fftw3.h
NFFT_INC_DIR="${NFFT_INC_DIR:-}"       # directory containing nfft3.h

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }
}

pick_make() {
  if command -v gmake >/dev/null 2>&1; then
    echo "gmake"
  else
    echo "make"
  fi
}

fetch_tarball() {
  local url="$1"
  local out="$2"
  if [[ -f "${out}" ]]; then return 0; fi
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail "${url}" -o "${out}"
  else
    need_cmd wget
    wget -O "${out}" "${url}"
  fi
}

stage_dir_copy_or_link() {
  local src="$1"
  local dest="$2"
  local mode="${3:-symlink}" # symlink|copy
  rm -rf "${dest}"
  mkdir -p "$(dirname "${dest}")"
  case "${mode}" in
    symlink) ln -s "${src}" "${dest}" ;;
    copy) cp -a "${src}" "${dest}" ;;
    *) echo "Unknown mode: ${mode}" >&2; exit 1 ;;
  esac
}

stage_file_copy_or_link() {
  local src="$1"
  local dest="$2"
  local mode="${3:-symlink}" # symlink|copy
  rm -f "${dest}"
  mkdir -p "$(dirname "${dest}")"
  case "${mode}" in
    symlink) ln -s "${src}" "${dest}" ;;
    copy) cp -a "${src}" "${dest}" ;;
    *) echo "Unknown mode: ${mode}" >&2; exit 1 ;;
  esac
}

rebuild_lfs() {
  echo "Rebuilding LuaFileSystem against rebuilt LuaJIT"
  need_cmd git
  local dir="${LIB_DIR}/lfs"
  if [[ ! -d "${dir}/.git" ]]; then
    git clone "${LFS_REPO}" "${dir}"
  fi
  (
    cd "${dir}"
    git fetch --all --tags
    git checkout "${LFS_REF}" || git checkout -B "${LFS_REF}" "origin/${LFS_REF}"
    git pull --ff-only || true
    make clean || true
    make lfs.a
    mkdir -p "${BIN_DIR}"
    cp -f liblfs.a "${BIN_DIR}/liblfs.a"
  )
}

rebuild_lpeg() {
  echo "Rebuilding LPeg against rebuilt LuaJIT"
  need_cmd tar
  local tar_name="lpeg-${LPEG_VERSION}.tar.gz"
  local tar_path="${LIB_DIR}/${tar_name}"
  local src_dir="${LIB_DIR}/lpeg-${LPEG_VERSION}"
  local dir="${LIB_DIR}/lpeg"
  local luajit_inc="${LIB_DIR}/luajit/include/luajit-2.1"
  local luajit_lib="${LIB_DIR}/luajit/lib/libluajit-5.1.a"

  if [[ ! -d "${src_dir}" ]]; then
    fetch_tarball "http://www.inf.puc-rio.br/~roberto/lpeg/${tar_name}" "${tar_path}"
    ( cd "${LIB_DIR}" && tar xzf "${tar_name}" )
  fi
  if [[ ! -e "${dir}" ]]; then
    ln -s "lpeg-${LPEG_VERSION}" "${dir}"
  fi

  (
    cd "${dir}"
    cp -f makefile makefile.mad.bak
    sed -i \
      -e "s|^#\\?LUADIR\\s*=.*|LUADIR = ${luajit_inc}|" \
      -e "s|^#\\?LUALIB\\s*=.*|LUALIB = ${luajit_lib}|" \
      -e "s|^COPT\\s*=.*|COPT = -O3|" \
      makefile
    if ! grep -qE '^[[:space:]]*lpeg\.a:' makefile; then
      awk '
        BEGIN{done=0}
        {print}
        (!done && $0 ~ /^lpeg\.so:/){
          print ""
          print "lpeg.a: $(FILES)"
          print "\tenv $(AR) -r lib$@ $(FILES)"
          print ""
          done=1
        }
      ' makefile > makefile.mad.tmp && mv makefile.mad.tmp makefile
    fi
    sed -i \
      -e 's/^\(linux:\).*/\1 lpeg.a/' \
      -e 's/^\(macosx:\).*/\1 lpeg.a/' \
      -e 's/^clean:.*/& liblpeg.a/' \
      makefile || true
    make clean || true
    make linux
    mkdir -p "${BIN_DIR}"
    cp -f liblpeg.a "${BIN_DIR}/liblpeg.a"
  )
}

main() {
  mkdir -p "${LIB_DIR}"
  local rebuilt_luajit=0

  # LuaJIT headers -> lib/luajit/src/*
  if [[ -n "${LUAJIT_SRC_DIR}" ]]; then
    echo "Staging LuaJIT headers from LUAJIT_SRC_DIR=${LUAJIT_SRC_DIR}"
    [[ -e "${LUAJIT_SRC_DIR}/lua.h" ]] || { echo "Missing ${LUAJIT_SRC_DIR}/lua.h" >&2; exit 1; }
    [[ -e "${LUAJIT_SRC_DIR}/luajit.h" ]] || { echo "Missing ${LUAJIT_SRC_DIR}/luajit.h" >&2; exit 1; }
    mkdir -p "${LIB_DIR}/luajit"
    stage_dir_copy_or_link "${LUAJIT_SRC_DIR}" "${LIB_DIR}/luajit/src" "symlink"
  else
    echo "Fetching LuaJIT repo for headers (${LUAJIT_REF})"
    need_cmd git
    local_dir="${LIB_DIR}/luajit"
    if [[ ! -d "${local_dir}/.git" ]]; then
      git clone "${LUAJIT_REPO}" "${local_dir}"
    fi
    ( cd "${local_dir}"
      git fetch --all --tags
      git checkout "${LUAJIT_REF}"
      git pull --ff-only || true
    )

    # Follow `README.luajit` literally enough to materialize `src/luajit.h`:
    #   make clean
    #   make amalg PREFIX=`pwd`
    #   make install PREFIX=`pwd`
    if [[ ! -e "${local_dir}/src/luajit.h" ]]; then
      echo "luajit.h not in repo — building LuaJIT as documented by MAD..."
      mk="$(pick_make)"
      (
        cd "${local_dir}"
        "${mk}" clean
        "${mk}" amalg PREFIX="$(pwd)"
        "${mk}" install PREFIX="$(pwd)"
      )
      rebuilt_luajit=1
    fi
  fi

  if [[ "${rebuilt_luajit}" -eq 1 ]]; then
    rebuild_lfs
    rebuild_lpeg
  fi

  # NLOpt headers -> lib/nlopt/src/api/nlopt.h
  if [[ -n "${NLOPT_INC_DIR}" ]]; then
    echo "Staging NLOpt header from NLOPT_INC_DIR=${NLOPT_INC_DIR}"
    stage_file_copy_or_link "${NLOPT_INC_DIR}/nlopt.h" "${LIB_DIR}/nlopt/src/api/nlopt.h" "symlink"
  else
    echo "Fetching NLOpt repo for headers (${NLOPT_REF})"
    need_cmd git
    local_dir="${LIB_DIR}/nlopt"
    if [[ ! -d "${local_dir}/.git" ]]; then
      git clone "${NLOPT_REPO}" "${local_dir}"
    fi
    ( cd "${local_dir}"
      git fetch --all --tags
      git checkout "${NLOPT_REF}"
      git pull --ff-only 2>/dev/null || true
    )
  fi

  # FFTW headers -> lib/fftw3/api/fftw3.h
  if [[ -n "${FFTW_INC_DIR}" ]]; then
    echo "Staging FFTW header from FFTW_INC_DIR=${FFTW_INC_DIR}"
    stage_file_copy_or_link "${FFTW_INC_DIR}/fftw3.h" "${LIB_DIR}/fftw3/api/fftw3.h" "symlink"
  else
    echo "Fetching FFTW tarball for headers (${FFTW_VERSION})"
    need_cmd tar
    tar_name="fftw-${FFTW_VERSION}.tar.gz"
    tar_path="${LIB_DIR}/${tar_name}"
    url="https://fftw.org/${tar_name}"
    fetch_tarball "${url}" "${tar_path}"
    ( cd "${LIB_DIR}" && tar xzf "${tar_name}" )
    rm -f "${LIB_DIR}/fftw3"
    ln -s "fftw-${FFTW_VERSION}" "${LIB_DIR}/fftw3"
  fi

  # NFFT headers -> lib/nfft3/include/nfft3.h
  if [[ -n "${NFFT_INC_DIR}" ]]; then
    echo "Staging NFFT header from NFFT_INC_DIR=${NFFT_INC_DIR}"
    mkdir -p "${LIB_DIR}/nfft3"
    stage_dir_copy_or_link "${NFFT_INC_DIR}" "${LIB_DIR}/nfft3/include" "symlink"
  else
    echo "Fetching NFFT tarball for headers (${NFFT_VERSION})"
    need_cmd tar
    tar_name="nfft-${NFFT_VERSION}.tar.gz"
    tar_path="${LIB_DIR}/${tar_name}"
    url="https://www-user.tu-chemnitz.de/~potts/nfft/download/${tar_name}"
    fetch_tarball "${url}" "${tar_path}"
    ( cd "${LIB_DIR}" && tar xzf "${tar_name}" )
    rm -f "${LIB_DIR}/nfft3"
    ln -s "nfft-${NFFT_VERSION}" "${LIB_DIR}/nfft3"
  fi

  echo
  echo "Header checks (expected by src/Makefile):"
  local rc=0
  for f in \
    "${LIB_DIR}/luajit/src/lua.h" \
    "${LIB_DIR}/luajit/src/luajit.h" \
    "${LIB_DIR}/nlopt/src/api/nlopt.h" \
    "${LIB_DIR}/fftw3/api/fftw3.h" \
    "${LIB_DIR}/nfft3/include/nfft3.h"
  do
    if [[ -e "${f}" ]]; then
      echo "  OK  ${f}"
    else
      echo "  MISS ${f}" >&2
      rc=1
    fi
  done
  return "${rc}"
}

main "$@"
