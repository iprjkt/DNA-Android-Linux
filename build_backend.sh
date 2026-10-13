#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo " Building DNA-Android-Linux Native C++ Engine (libdna)    "
echo "=========================================================="

BUILD_DIR="build"

mkdir -p "${BUILD_DIR}"
cmake -B "${BUILD_DIR}" -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build "${BUILD_DIR}" --parallel

echo ""
echo "[✓] Native C++ backend engine compiled successfully!"
echo "    - Shared Python module: dna_core/dna_core_cpp.*.so"
echo "    - Native CLI executable: build/dna_native_cli"
echo "=========================================================="
