#!/usr/bin/env bash
# Build Arch Linux package (.pkg.tar.zst) for DNA-Linux
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCH_DIR="${REPO_DIR}/packaging/arch"
OUT_DIR="${REPO_DIR}/dist"
mkdir -p "${OUT_DIR}"

echo "=== Building Arch Linux Package ==="

VERSION="$(grep '^pkgver=' "${ARCH_DIR}/PKGBUILD" | cut -d= -f2)"

# Build source distribution tarball if not already present
if [ ! -f "${OUT_DIR}/dna_linux-${VERSION}.tar.gz" ]; then
    echo ">> Generating sdist tarball..."
    python3 -m build --sdist --no-isolation "${REPO_DIR}"
fi

# Supply source archive for makepkg
cp "${OUT_DIR}/dna_linux-${VERSION}.tar.gz" "${ARCH_DIR}/dna-linux-${VERSION}.tar.gz"

cd "${ARCH_DIR}"
makepkg -f -d -C

# Move generated package to dist/
mv "${ARCH_DIR}"/dna-linux-${VERSION}-*.pkg.tar.zst "${OUT_DIR}/"
rm -f "${ARCH_DIR}/dna-linux-${VERSION}.tar.gz"
rm -rf "${ARCH_DIR}/pkg" "${ARCH_DIR}/src"

echo "✓ Arch Linux package created in ${OUT_DIR}"
