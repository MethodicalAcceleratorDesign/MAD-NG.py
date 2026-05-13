#!/usr/bin/env bash
set -euo pipefail

# Stage headers into the layout expected by MAD-NG's unmodified `src/Makefile`.
#
# Expected include paths (from `src/Makefile`):
#   -I../lib/luajit/src            -> lua.h etc
#   -I../lib/nlopt/src/api         -> nlopt.h
#   -I../lib/fftw3/api             -> fftw3.h
#   -I../lib/nfft3/include         -> nfft3.h
#
# This script does NOT build archives; it only ensures headers exist (by
# downloading sources, or by symlinking/copying from user-provided locations).

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB_DIR="${ROOT}/lib"

LUAJIT_REF="${LUAJIT_REF:-mad-patch}"
LUAJIT_REPO="${LUAJIT_REPO:-https://github.com/MethodicalAcceleratorDesign/LuaJIT.git}"

NLOPT_REF="${NLOPT_REF:-v2.7.1}"
NLOPT_REPO="${NLOPT_REPO:-https://github.com/stevengj/nlopt.git}"

FFTW_VERSION="${FFTW_VERSION:-3.3.10}"
NFFT_VERSION="${NFFT_VERSION:-3.5.3}"

# Optional: point these at already-installed headers (will be copied/symlinked)
LUAJIT_SRC_DIR="${LUAJIT_SRC_DIR:-}"   # directory containing lua.h etc
NLOPT_INC_DIR="${NLOPT_INC_DIR:-}"     # directory containing nlopt.h
FFTW_INC_DIR="${FFTW_INC_DIR:-}"       # directory containing fftw3.h
NFFT_INC_DIR="${NFFT_INC_DIR:-}"       # directory containing nfft3.h

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }
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

main() {
  mkdir -p "${LIB_DIR}"

  # LuaJIT headers -> lib/luajit/src/*
  if [[ -n "${LUAJIT_SRC_DIR}" ]]; then
    echo "Staging LuaJIT headers from LUAJIT_SRC_DIR=${LUAJIT_SRC_DIR}"
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
      git pull --ff-only || true
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
    echo "Staging NFFT header(s) from NFFT_INC_DIR=${NFFT_INC_DIR}"
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
  for f in \
    "${LIB_DIR}/luajit/src/lua.h" \
    "${LIB_DIR}/nlopt/src/api/nlopt.h" \
    "${LIB_DIR}/fftw3/api/fftw3.h" \
    "${LIB_DIR}/nfft3/include/nfft3.h"
  do
    if [[ -e "${f}" ]]; then
      echo "  OK  ${f}"
    else
      echo "  MISS ${f}"
    fi
  done
}

main "$@"
