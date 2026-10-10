#!/usr/bin/env bash
# Build Debian/Ubuntu .deb package for DNA-Linux
set -euo pipefail

PACKAGE_NAME="dna-linux"
VERSION="0.1.0"
ARCH="all"
BUILD_DIR="$(mktemp -d -t dna-deb-XXXXXX)"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Building Debian Package: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb ==="

DEB_ROOT="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}"
mkdir -p "${DEB_ROOT}/DEBIAN"
mkdir -p "${DEB_ROOT}/usr/bin"
mkdir -p "${DEB_ROOT}/usr/lib/dna-linux"
mkdir -p "${DEB_ROOT}/usr/share/applications"
mkdir -p "${DEB_ROOT}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${DEB_ROOT}/usr/share/man/man1"
mkdir -p "${DEB_ROOT}/usr/share/bash-completion/completions"
mkdir -p "${DEB_ROOT}/usr/share/zsh/site-functions"
mkdir -p "${DEB_ROOT}/usr/share/fish/vendor_completions.d"

# 1. Build & Copy Application Files
cp -r "${REPO_DIR}/dna_core" "${DEB_ROOT}/usr/lib/dna-linux/"
cp -r "${REPO_DIR}/dna_cli" "${DEB_ROOT}/usr/lib/dna-linux/"
cp -r "${REPO_DIR}/dna_tui" "${DEB_ROOT}/usr/lib/dna-linux/"
cp -r "${REPO_DIR}/dna_gui" "${DEB_ROOT}/usr/lib/dna-linux/"
cp -r "${REPO_DIR}/data" "${DEB_ROOT}/usr/lib/dna-linux/"

# 2. Wrapper Scripts
cat << 'EOF' > "${DEB_ROOT}/usr/bin/dna"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/dna-linux")
from dna_cli.main import cli
if __name__ == "__main__":
    cli()
EOF
chmod 755 "${DEB_ROOT}/usr/bin/dna"

cat << 'EOF' > "${DEB_ROOT}/usr/bin/dna-gui"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/dna-linux")
from dna_gui.app import start_gui
if __name__ == "__main__":
    sys.exit(start_gui())
EOF
chmod 755 "${DEB_ROOT}/usr/bin/dna-gui"

# 3. Desktop Entry & Icon
cp "${REPO_DIR}/data/dna.desktop" "${DEB_ROOT}/usr/share/applications/"
cp "${REPO_DIR}/data/icons/dna.svg" "${DEB_ROOT}/usr/share/icons/hicolor/scalable/apps/"
mkdir -p "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps"
cp "${REPO_DIR}/data/icons/dna.png" "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/"


# 4. Man Page
if [ -f "${REPO_DIR}/man/dna.1" ]; then
    gzip -9 -c "${REPO_DIR}/man/dna.1" > "${DEB_ROOT}/usr/share/man/man1/dna.1.gz"
fi

# 5. Shell Completions
if [ -f "${REPO_DIR}/completions/dna.bash" ]; then
    cp "${REPO_DIR}/completions/dna.bash" "${DEB_ROOT}/usr/share/bash-completion/completions/dna"
fi
if [ -f "${REPO_DIR}/completions/_dna" ]; then
    cp "${REPO_DIR}/completions/_dna" "${DEB_ROOT}/usr/share/zsh/site-functions/_dna"
fi
if [ -f "${REPO_DIR}/completions/dna.fish" ]; then
    cp "${REPO_DIR}/completions/dna.fish" "${DEB_ROOT}/usr/share/fish/vendor_completions.d/dna.fish"
fi

# 6. Control File
cat << EOF > "${DEB_ROOT}/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: iprjkt <muhammadaufan0101@gmail.com>
Depends: python3 (>= 3.11), python3-click, python3-rich, e2fsprogs, erofs-utils, brotli, zstd
Recommends: python3-pyqt6, android-sdk-platform-tools | android-tools
Suggests: apktool, avbtool
Description: Native Linux (x86_64) Android ROM unpack, repack, and patch toolkit
 DNA-Linux is a high-performance native Linux port of DNA-Android.
 It provides command-line, curses TUI, and modern PyQt6 desktop GUI
 interfaces for unpacking, repacking, converting, debloating, and
 patching Android images (ext4, erofs, super.img, services.jar).
EOF

# 7. Postinst & Postrm
cat << 'EOF' > "${DEB_ROOT}/DEBIAN/postinst"
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q || true
fi
EOF
chmod 755 "${DEB_ROOT}/DEBIAN/postinst"

cat << 'EOF' > "${DEB_ROOT}/DEBIAN/postrm"
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q || true
fi
EOF
chmod 755 "${DEB_ROOT}/DEBIAN/postrm"

# 8. Build package using dpkg-deb if installed, or report directory
OUT_DIR="${REPO_DIR}/dist"
mkdir -p "${OUT_DIR}"

if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --build --root-owner-group "${DEB_ROOT}" "${OUT_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
    echo "✓ Built package: ${OUT_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
else
    echo "dpkg-deb not found. Root prepared at: ${DEB_ROOT}"
fi

rm -rf "${BUILD_DIR}"
echo "Debian packaging script completed."
