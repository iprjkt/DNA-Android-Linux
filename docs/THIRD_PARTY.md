# Third-Party Tools & Licenses

DNA-Linux orchestrates native Linux tools to unpack, patch, and repack Android ROM images. Below are the third-party native tools and their respective upstream licenses:

| Tool | Purpose | Upstream License | Project URL |
|---|---|---|---|
| **android-tools** (`lpmake`, `lpunpack`, `simg2img`, `img2simg`) | Dynamic partition (super) and sparse image tools | Apache 2.0 | [AOSP / android-tools](https://android.googlesource.com/) |
| **e2fsprogs** (`mke2fs`, `e2fsdroid`, `resize2fs`, `e2fsck`, `debugfs`) | ext4 creation, manipulation, and SELinux file injection | GPL-2.0 / LGPL-2.0 / Apache 2.0 | [e2fsprogs](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git) |
| **erofs-utils** (`mkfs.erofs`, `fsck.erofs`) | EROFS compression and unpacking | GPL-2.0 / Apache 2.0 | [erofs-utils](https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git) |
| **f2fs-tools** (`extract.f2fs`, `mkfs.f2fs`, `sload_f2fs`) | F2FS extraction and filesystem creation | GPL-2.0 / LGPL-2.1 | [f2fs-tools](https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git) |
| **brotli** | Brotli decompression / compression for `.br` images | MIT | [google/brotli](https://github.com/google/brotli) |
| **zstd** | Zstandard decompression / compression | BSD-3-Clause / GPL-2.0 | [facebook/zstd](https://github.com/facebook/zstd) |
| **avbtool** | Android Verified Boot header / vbmeta inspection & patching | Apache 2.0 | [AOSP / avb](https://android.googlesource.com/platform/external/avb/) |
| **apktool** / **smali** / **baksmali** | Smali bytecode decompilation & assembly | Apache 2.0 / BSD-style | [iBotPeaches/Apktool](https://github.com/iBotPeaches/Apktool), [JesusFreke/smali](https://github.com/JesusFreke/smali) |
| **payload-dumper-go** | OTA `payload.bin` partition extraction | Apache 2.0 | [ssut/payload-dumper-go](https://github.com/ssut/payload-dumper-go) |
| **sdat2img** / **img2sdat** | Sparse data convert to/from raw ext4 | Apache 2.0 | [xpirt/sdat2img](https://github.com/xpirt/sdat2img) |
