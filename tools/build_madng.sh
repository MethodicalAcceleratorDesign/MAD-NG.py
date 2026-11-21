#!/usr/bin/env bash
# Build MAD-NG (Linux x86_64 or macOS arm64) in a MAD-NG checkout: tools/build_madng.sh <MAD-NG checkout>
# Needs git, curl, make, cmake and gcc/g++/gfortran (Linux: static libgfortran, libquadmath, libstdc++).
set -euo pipefail

TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAD="$(cd "${1:?usage: build_madng.sh <MAD-NG checkout>}" && pwd)"
DEPS="${DEPS:-${MAD}/lib}" # dependency sources and (macOS) built archives
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN)}"
OS="$(uname -s)"

LUAJIT_REPO=https://github.com/MethodicalAcceleratorDesign/LuaJIT.git
LFS_REPO=https://github.com/MethodicalAcceleratorDesign/luafilesystem.git
LPEG=lpeg-1.1.0
FFTW=fftw-3.3.10
NFFT=nfft-3.5.3
NLOPT_REF=v2.7.1
LAPACK_REF=v3.12.1

if [[ "${OS}" == Darwin ]]; then
  gcc_bin="$(ls /opt/homebrew/bin/gcc-[0-9]* | sort -V | tail -n1)"
  export CC="${CC:-${gcc_bin}}" CXX="${CXX:-g++-${gcc_bin##*-}}" FC="${FC:-gfortran-${gcc_bin##*-}}"
  export MACOSX_DEPLOYMENT_TARGET=14
fi

mkdir -p "${DEPS}"
cd "${DEPS}"

clone() { [[ -d "$2" ]] || git clone --depth 1 ${3:+--branch "$3"} "$1" "$2"; }
untar() { [[ -d "$2" ]] || curl -fsSL "$1" | tar xz; }

# LuaJIT supplies the bytecode compiler used by the MAD-NG build
clone "${LUAJIT_REPO}" luajit mad-patch
[[ -x luajit/bin/luajit ]] || (cd luajit && make -j"${JOBS}" amalg PREFIX="$PWD" ${CC:+CC="${CC}"} && make install PREFIX="$PWD")

# Headers only (Linux) or sources (macOS)
untar "https://fftw.org/${FFTW}.tar.gz" "${FFTW}"
untar "https://www-user.tu-chemnitz.de/~potts/nfft/download/${NFFT}.tar.gz" "${NFFT}"
clone https://github.com/stevengj/nlopt nlopt "${NLOPT_REF}"
ln -sfn "${FFTW}" fftw3
ln -sfn "${NFFT}" nfft3

build_linux() {
  # The archives in the MAD-NG `bin` submodule are used as they are
  cp "${MAD}/src/Makefile.lxplus" "${MAD}/src/Makefile"
  sed -i 's/-fdiagnostics-all-candidates//g' "${MAD}/src/Makefile" # clang-only flag
  make -C "${MAD}/src" -j"${JOBS}" SHELL=/bin/bash CC=gcc CXX=g++ LDOPTIONS=-no-pie
}

build_macos() {
  local arm="${DEPS}/arm64"
  mkdir -p "${arm}"

  # Each archive is built once, so `DEPS` can be cached between runs
  have() { [[ -f "${arm}/$1" ]]; }

  have libluajit.a || cp luajit/src/libluajit.a "${arm}/"

  have liblfs.a || (
    clone "${LFS_REPO}" lfs
    cd lfs && make lfs.a CC="${CC}" AR=ar CFLAGS="-O3 -fPIC -I${DEPS}/luajit/src" && cp liblfs.a "${arm}/"
  )

  # MAD embeds a static archive: build the object set instead of the upstream shared module
  have liblpeg.a || (
    untar "http://www.inf.puc-rio.br/~roberto/lpeg/${LPEG}.tar.gz" "${LPEG}"
    cd "${LPEG}"
    make lpvm.o lpcap.o lptree.o lpcode.o lpprint.o lpcset.o CC="${CC}" \
      LUADIR="${DEPS}/luajit/src" COPT='-O3 -DNDEBUG'
    ar -rcs liblpeg.a lpvm.o lpcap.o lptree.o lpcode.o lpprint.o lpcset.o
    cp liblpeg.a "${arm}/"
  )

  have libfftw3.a || (
    cd "${FFTW}"
    CC="${CC}" CFLAGS='-O3 -fPIC' ./configure --disable-shared --enable-static
    make -j"${JOBS}" && cp .libs/libfftw3.a "${arm}/"
  )

  have libnfft3.a || (
    cd "${NFFT}"
    CC="${CC}" CFLAGS='-O3 -fPIC' ./configure --enable-all --disable-shared \
      --with-fftw3="${DEPS}/${FFTW}" --with-fftw3-libdir="${DEPS}/${FFTW}/.libs" \
      --with-fftw3-includedir="${DEPS}/${FFTW}/api"
    make -j"${JOBS}" && cp .libs/libnfft3.a "${arm}/"
  )

  have libnlopt.a || (
    cd nlopt
    cmake -S . -B build -DBUILD_SHARED_LIBS=OFF -DNLOPT_CXX=OFF -DNLOPT_FORTRAN=OFF \
      -DCMAKE_C_COMPILER="${CC}" -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cmake --build build -j"${JOBS}" && cp build/libnlopt.a "${arm}/"
  )

  have liblapack.a || (
    clone https://github.com/Reference-LAPACK/lapack lapack "${LAPACK_REF}"
    cd lapack
    cmake -S . -B build -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DCMAKE_C_COMPILER="${CC}" \
      -DCMAKE_Fortran_COMPILER="${FC}" -DCMAKE_OSX_ARCHITECTURES=arm64
    cmake --build build -j"${JOBS}" --target blas lapack
    cp build/lib/libblas.a "${arm}/librefblas.a" && cp build/lib/liblapack.a "${arm}/"
  )

  # The submodule archives are Intel: replace them with the arm64 ones
  lipo -info "${arm}"/*.a
  cp "${arm}"/*.a "${MAD}/bin/macosx/"

  # arm64 Makefile.macosx; skipped if a previous run already applied it
  if git -C "${MAD}" apply --check "${TOOLS}/macos_arm64.patch" 2>/dev/null; then
    git -C "${MAD}" apply "${TOOLS}/macos_arm64.patch"
  else
    git -C "${MAD}" apply -R --check "${TOOLS}/macos_arm64.patch"
  fi
  make -C "${MAD}/src" -f Makefile.macosx -j"${JOBS}" CC="${CC}" CXX="${CXX}" FC="${FC}" \
    LIB="${DEPS}" CPUFLAGS=-mcpu=apple-m1
}

case "${OS}" in
  Linux) build_linux ;;
  Darwin) build_macos ;;
  *) echo "Unsupported OS: ${OS}" >&2 && exit 1 ;;
esac

chmod 755 "${MAD}/src/mad"
"${MAD}/src/mad" -e "print(MAD.env.version)"
