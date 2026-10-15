#!/usr/bin/env bash
# ==============================================================================
# DNA-Android-Linux Master Release Packaging Script
# Generates:
#   1. Native C++ backend engine (libdna & dna_native_cli)
#   2. Python Wheel & Source Distribution (.whl, .tar.gz)
#   3. Arch Linux Package (.pkg.tar.zst)
#   4. Debian/Ubuntu Package (.deb)
#   5. Standalone Portable Distribution Bundle (.tar.gz, .tar.zst)
#   6. Cryptographic SHA-256 Checksums (SHA256SUMS)
# ==============================================================================
set -euo pipefail

VERSION="0.1.0"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${REPO_DIR}/dist"
PORTABLE_DIR="$(mktemp -d -t dna-portable-XXXXXX)"

echo "=========================================================="
echo " Starting DNA-Linux v${VERSION} Release Packaging Pipeline"
echo "=========================================================="
mkdir -p "${DIST_DIR}"

# ------------------------------------------------------------------------------
# 1. Native C++ Backend Engine
# ------------------------------------------------------------------------------
echo ""
echo "[Step 1/5] Compiling native C++ backend engine..."
"${REPO_DIR}/build_backend.sh"

# ------------------------------------------------------------------------------
# 2. Python Wheel & Source Distribution
# ------------------------------------------------------------------------------
echo ""
echo "[Step 2/5] Building Python Wheel and Source Distribution..."
python3 -m build --no-isolation "${REPO_DIR}"

# ------------------------------------------------------------------------------
# 3. Debian / Ubuntu Package (.deb)
# ------------------------------------------------------------------------------
echo ""
echo "[Step 3/5] Building Debian / Ubuntu .deb package..."
"${REPO_DIR}/packaging/debian/build_deb.sh"

# ------------------------------------------------------------------------------
# 4. Arch Linux Package (.pkg.tar.zst)
# ------------------------------------------------------------------------------
echo ""
echo "[Step 4/5] Building Arch Linux .pkg.tar.zst package..."
if command -v makepkg >/dev/null 2>&1; then
    "${REPO_DIR}/packaging/arch/build_pkg.sh"
else
    echo ">> makepkg not installed, skipping Arch package creation."
fi

# ------------------------------------------------------------------------------
# 5. Standalone Portable Bundle (.tar.gz and .tar.zst)
# ------------------------------------------------------------------------------
echo ""
echo "[Step 5/5] Assembling Standalone Portable Release Bundles..."
BUNDLE_NAME="dna-linux-v${VERSION}-linux-x86_64"
BUNDLE_ROOT="${PORTABLE_DIR}/${BUNDLE_NAME}"
mkdir -p "${BUNDLE_ROOT}/bin"

# Copy python packages & native extension
cp -r "${REPO_DIR}/dna_core" "${BUNDLE_ROOT}/"
cp -r "${REPO_DIR}/dna_cli" "${BUNDLE_ROOT}/"
cp -r "${REPO_DIR}/dna_tui" "${BUNDLE_ROOT}/"
cp -r "${REPO_DIR}/dna_gui" "${BUNDLE_ROOT}/"
cp -r "${REPO_DIR}/data" "${BUNDLE_ROOT}/"
if [ -d "${BUNDLE_ROOT}/data/bin" ]; then
    chmod 755 "${BUNDLE_ROOT}/data/bin"/*
    cp -p "${BUNDLE_ROOT}/data/bin"/* "${BUNDLE_ROOT}/bin/"
fi
cp -r "${REPO_DIR}/completions" "${BUNDLE_ROOT}/"
cp -r "${REPO_DIR}/man" "${BUNDLE_ROOT}/"
cp "${REPO_DIR}/README.md" "${BUNDLE_ROOT}/"
cp "${REPO_DIR}/LICENSE" "${BUNDLE_ROOT}/"
cp "${REPO_DIR}/CREDITS.md" "${BUNDLE_ROOT}/"

# Copy native C++ standalone CLI
if [ -f "${REPO_DIR}/build/dna_native_cli" ]; then
    cp "${REPO_DIR}/build/dna_native_cli" "${BUNDLE_ROOT}/bin/dna-native"
    cp "${REPO_DIR}/build/dna_native_cli" "${BUNDLE_ROOT}/dna-native"
    chmod 755 "${BUNDLE_ROOT}/bin/dna-native" "${BUNDLE_ROOT}/dna-native"
fi

# Portable direct runners
cat << 'EOF' > "${BUNDLE_ROOT}/dna"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}" exec python3 -m dna_cli.main "$@"
EOF
chmod 755 "${BUNDLE_ROOT}/dna"
cp "${BUNDLE_ROOT}/dna" "${BUNDLE_ROOT}/bin/dna"

cat << 'EOF' > "${BUNDLE_ROOT}/dna-gui"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}" exec python3 -m dna_gui.app "$@"
EOF
chmod 755 "${BUNDLE_ROOT}/dna-gui"
cp "${BUNDLE_ROOT}/dna-gui" "${BUNDLE_ROOT}/bin/dna-gui"

# Install script inside portable bundle
cat << 'EOF' > "${BUNDLE_ROOT}/install.sh"
#!/usr/bin/env bash
# DNA-Linux Portable Bundle Installer
set -euo pipefail

PREFIX="/usr/local"
if [[ "${1:-}" == "--user" ]]; then
    PREFIX="${HOME}/.local"
fi

echo "=== Installing DNA-Linux to ${PREFIX} ==="

BIN_DIR="${PREFIX}/bin"
LIB_DIR="${PREFIX}/lib/dna-linux"
SHARE_DIR="${PREFIX}/share"
APP_DIR="${SHARE_DIR}/applications"
ICON_SCALABLE="${SHARE_DIR}/icons/hicolor/scalable/apps"
ICON_256="${SHARE_DIR}/icons/hicolor/256x256/apps"
MAN_DIR="${SHARE_DIR}/man/man1"
BASH_COMP="${SHARE_DIR}/bash-completion/completions"
ZSH_COMP="${SHARE_DIR}/zsh/site-functions"
FISH_COMP="${SHARE_DIR}/fish/vendor_completions.d"

mkdir -p "${BIN_DIR}" "${LIB_DIR}" "${APP_DIR}" "${ICON_SCALABLE}" "${ICON_256}" "${MAN_DIR}" "${BASH_COMP}" "${ZSH_COMP}" "${FISH_COMP}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Application files
cp -r "${SCRIPT_DIR}/dna_core" "${LIB_DIR}/"
cp -r "${SCRIPT_DIR}/dna_cli" "${LIB_DIR}/"
cp -r "${SCRIPT_DIR}/dna_tui" "${LIB_DIR}/"
cp -r "${SCRIPT_DIR}/dna_gui" "${LIB_DIR}/"
cp -r "${SCRIPT_DIR}/data" "${LIB_DIR}/"
mkdir -p "${SHARE_DIR}/dna-linux"
cp -r "${SCRIPT_DIR}/data" "${SHARE_DIR}/dna-linux/"
if [ -d "${LIB_DIR}/data/bin" ]; then
    chmod 755 "${LIB_DIR}/data/bin"/*
    chmod 755 "${SHARE_DIR}/dna-linux/data/bin"/*
fi

# System launch wrappers
cat << WRAPPER > "${BIN_DIR}/dna"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "${LIB_DIR}")
from dna_cli.main import cli
if __name__ == "__main__":
    cli()
WRAPPER
chmod 755 "${BIN_DIR}/dna"

cat << WRAPPER > "${BIN_DIR}/dna-gui"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "${LIB_DIR}")
from dna_gui.app import start_gui
if __name__ == "__main__":
    sys.exit(start_gui())
WRAPPER
chmod 755 "${BIN_DIR}/dna-gui"

if [ -f "${SCRIPT_DIR}/bin/dna-native" ]; then
    cp "${SCRIPT_DIR}/bin/dna-native" "${BIN_DIR}/dna-native"
    chmod 755 "${BIN_DIR}/dna-native"
fi

# Desktop & Icons
cp "${SCRIPT_DIR}/data/dna.desktop" "${APP_DIR}/"
cp "${SCRIPT_DIR}/data/icons/dna.svg" "${ICON_SCALABLE}/"
cp "${SCRIPT_DIR}/data/icons/dna.png" "${ICON_256}/"

# Man page & completions
if [ -f "${SCRIPT_DIR}/man/dna.1" ]; then
    gzip -9 -c "${SCRIPT_DIR}/man/dna.1" > "${MAN_DIR}/dna.1.gz"
fi
if [ -f "${SCRIPT_DIR}/completions/dna.bash" ]; then
    cp "${SCRIPT_DIR}/completions/dna.bash" "${BASH_COMP}/dna"
fi
if [ -f "${SCRIPT_DIR}/completions/_dna" ]; then
    cp "${SCRIPT_DIR}/completions/_dna" "${ZSH_COMP}/_dna"
fi
if [ -f "${SCRIPT_DIR}/completions/dna.fish" ]; then
    cp "${SCRIPT_DIR}/completions/dna.fish" "${FISH_COMP}/dna.fish"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q "${APP_DIR}" || true
fi

echo "✓ DNA-Linux installed successfully to ${PREFIX}!"
echo "  Run 'dna' for CLI, 'dna-gui' for GUI, or 'dna-native' for native C++ runner."
EOF
chmod 755 "${BUNDLE_ROOT}/install.sh"

# Uninstall script inside portable bundle
cat << 'EOF' > "${BUNDLE_ROOT}/uninstall.sh"
#!/usr/bin/env bash
set -euo pipefail

PREFIX="/usr/local"
if [[ "${1:-}" == "--user" ]]; then
    PREFIX="${HOME}/.local"
fi

echo "=== Uninstalling DNA-Linux from ${PREFIX} ==="
rm -f "${PREFIX}/bin/dna" "${PREFIX}/bin/dna-gui" "${PREFIX}/bin/dna-native"
rm -rf "${PREFIX}/lib/dna-linux"
rm -rf "${PREFIX}/share/dna-linux"
rm -f "${PREFIX}/share/applications/dna.desktop"
rm -f "${PREFIX}/share/icons/hicolor/scalable/apps/dna.svg"
rm -f "${PREFIX}/share/icons/hicolor/256x256/apps/dna.png"
rm -f "${PREFIX}/share/man/man1/dna.1.gz"
rm -f "${PREFIX}/share/bash-completion/completions/dna"
rm -f "${PREFIX}/share/zsh/site-functions/_dna"
rm -f "${PREFIX}/share/fish/vendor_completions.d/dna.fish"
echo "✓ DNA-Linux uninstalled from ${PREFIX}."
EOF
chmod 755 "${BUNDLE_ROOT}/uninstall.sh"

# Pack tar.gz and tar.zst
tar -czf "${DIST_DIR}/${BUNDLE_NAME}.tar.gz" -C "${PORTABLE_DIR}" "${BUNDLE_NAME}"
echo "✓ Portable tar.gz created: ${DIST_DIR}/${BUNDLE_NAME}.tar.gz"

if command -v zstd >/dev/null 2>&1; then
    tar --zstd -cf "${DIST_DIR}/${BUNDLE_NAME}.tar.zst" -C "${PORTABLE_DIR}" "${BUNDLE_NAME}"
    echo "✓ Portable tar.zst created: ${DIST_DIR}/${BUNDLE_NAME}.tar.zst"
fi

rm -rf "${PORTABLE_DIR}"

# ------------------------------------------------------------------------------
# 6. Checksums (SHA-256)
# ------------------------------------------------------------------------------
echo ""
echo ">> Generating SHA-256 checksums..."
cd "${DIST_DIR}"
rm -f SHA256SUMS
sha256sum * > SHA256SUMS

echo ""
echo "=========================================================="
echo " DNA-Linux Release Packaging Completed Successfully!"
echo " Output files in ${DIST_DIR}:"
echo "=========================================================="
ls -lh "${DIST_DIR}"
echo ""
cat "${DIST_DIR}/SHA256SUMS"
echo "=========================================================="
