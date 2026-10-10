"""Project Menu view containing all Android ROM unpack, repack, convert, jar, patch, and debloat operations."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dna_gui.widgets.card_button import CardItemWidget


class ProjectView(QWidget):
    """Scrollable operation menu matching DNA-Android's comprehensive Project Menu."""

    # Navigation
    navigate_plugins = pyqtSignal()

    # Unpack operations
    action_unpack_bin = pyqtSignal()
    action_unpack_br = pyqtSignal()
    action_unpack_dat = pyqtSignal()
    action_unpack_img = pyqtSignal()
    action_unpack_zstd = pyqtSignal()
    action_unpack_super = pyqtSignal()

    # Repack operations
    action_resize_img = pyqtSignal()
    action_repack_img = pyqtSignal()
    action_repack_zstd = pyqtSignal()
    action_repack_super = pyqtSignal()

    # Conversion operations
    action_convert_simg = pyqtSignal()
    action_convert_dat_br = pyqtSignal()
    action_convert_merge_super = pyqtSignal()
    action_convert_split_super = pyqtSignal()

    # Jar operations
    action_jar_dsv = pyqtSignal()
    action_jar_apk_protection = pyqtSignal()
    action_jar_dss = pyqtSignal()

    # Patch operations
    action_patch_vbmeta = pyqtSignal()
    action_patch_integrity = pyqtSignal()
    action_patch_safetycore = pyqtSignal()
    action_patch_privapp = pyqtSignal()
    action_patch_ota = pyqtSignal()
    action_patch_xiaomi = pyqtSignal()

    # ROM operations
    action_rom_debloat = pyqtSignal()
    action_rom_remove_oat = pyqtSignal()
    action_rom_make_rw = pyqtSignal()
    action_rom_decrypt = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 14, 20, 24)
        content_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Plugin Functions
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Plugin Functions"))
        plugin_card = self._make_card()
        item_plugins = CardItemWidget(
            title="Plugin Functions",
            subtitle="Local plugins can be imported using zip archives",
            icon_type="arrow",
        )
        item_plugins.clicked.connect(self.navigate_plugins.emit)
        plugin_card.layout().addWidget(item_plugins)
        content_layout.addWidget(plugin_card)

        # -------------------------------------------------------------
        # 2. Unpacking Menu
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Unpacking Menu"))
        unpack_card = self._make_card()
        u_layout = unpack_card.layout()

        item_u_bin = CardItemWidget("Unpack bin", "Extract partitions from OTA payload.bin")
        item_u_bin.clicked.connect(self.action_unpack_bin.emit)
        u_layout.addWidget(item_u_bin)

        item_u_br = CardItemWidget("Unpack br", "Decompress brotli archive (.br) into sparse dat")
        item_u_br.clicked.connect(self.action_unpack_br.emit)
        u_layout.addWidget(item_u_br)

        item_u_dat = CardItemWidget("Unpack dat", "Convert transfer list (.transfer.list + .new.dat) to raw img")
        item_u_dat.clicked.connect(self.action_unpack_dat.emit)
        u_layout.addWidget(item_u_dat)

        item_u_img = CardItemWidget("Unpack img", "Extract ext4 or erofs partition image to directory")
        item_u_img.clicked.connect(self.action_unpack_img.emit)
        u_layout.addWidget(item_u_img)

        item_u_zstd = CardItemWidget("Unpack zstd", "Decompress zstd compressed partition image (.zst)")
        item_u_zstd.clicked.connect(self.action_unpack_zstd.emit)
        u_layout.addWidget(item_u_zstd)

        item_u_super = CardItemWidget("Unpack super", "Unpack dynamic super.img partitions using native lpunpack")
        item_u_super.clicked.connect(self.action_unpack_super.emit)
        u_layout.addWidget(item_u_super)

        content_layout.addWidget(unpack_card)

        # -------------------------------------------------------------
        # 3. Repacking Menu
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Repacking Menu"))
        repack_card = self._make_card()
        r_layout = repack_card.layout()

        item_r_resize = CardItemWidget("Resize img partition", "Resize ext4 partition image using resize2fs")
        item_r_resize.clicked.connect(self.action_resize_img.emit)
        r_layout.addWidget(item_r_resize)

        item_r_img = CardItemWidget("Repack single img partition", "Repack unpacked folder into ext4/erofs image with canned metadata")
        item_r_img.clicked.connect(self.action_repack_img.emit)
        r_layout.addWidget(item_r_img)

        item_r_zstd = CardItemWidget("Repack zstd", "Compress partition image with zstd")
        item_r_zstd.clicked.connect(self.action_repack_zstd.emit)
        r_layout.addWidget(item_r_zstd)

        item_r_super = CardItemWidget("Repack super.img", "Assemble dynamic super.img partition table using native lpmake")
        item_r_super.clicked.connect(self.action_repack_super.emit)
        r_layout.addWidget(item_r_super)

        content_layout.addWidget(repack_card)

        # -------------------------------------------------------------
        # 4. Format Conversion
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Format Conversion"))
        conv_card = self._make_card()
        c_layout = conv_card.layout()

        item_c_simg = CardItemWidget("img-simg Conversion", "Convert raw image to sparse image or sparse to raw")
        item_c_simg.clicked.connect(self.action_convert_simg.emit)
        c_layout.addWidget(item_c_simg)

        item_c_dat_br = CardItemWidget("img-dat-br Conversion", "Convert raw partition image into sparse dat & brotli archive")
        item_c_dat_br.clicked.connect(self.action_convert_dat_br.emit)
        c_layout.addWidget(item_c_dat_br)

        item_c_merge = CardItemWidget("Merge splited img into super.img", "Restore the original super.img from sparse chunks")
        item_c_merge.clicked.connect(self.action_convert_merge_super.emit)
        c_layout.addWidget(item_c_merge)

        item_c_split = CardItemWidget("Split super.img into parts", "Sparse super.img into evenly sized chunk files")
        item_c_split.clicked.connect(self.action_convert_split_super.emit)
        c_layout.addWidget(item_c_split)

        content_layout.addWidget(conv_card)

        # -------------------------------------------------------------
        # 5. Jar Menu
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Jar Menu"))
        jar_card = self._make_card()
        j_layout = jar_card.layout()

        item_j_dsv = CardItemWidget(
            "Core patch - DSV",
            "Enables direct installation of system applications by bypassing complete signature verification",
        )
        item_j_dsv.clicked.connect(self.action_jar_dsv.emit)
        j_layout.addWidget(item_j_dsv)

        item_j_prot = CardItemWidget(
            "Remove Apk Protection",
            "Disables built-in APK protection in stock ROMs, allowing seamless replacement of modified system applications",
        )
        item_j_prot.clicked.connect(self.action_jar_apk_protection.emit)
        j_layout.addWidget(item_j_prot)

        item_j_dss = CardItemWidget(
            "Disable secure screenshot",
            "This removes the screenshots and screenrecords limits for all applications (Includes Android 17 CompletableFuture crash fix)",
        )
        item_j_dss.clicked.connect(self.action_jar_dss.emit)
        j_layout.addWidget(item_j_dss)

        content_layout.addWidget(jar_card)

        # -------------------------------------------------------------
        # 6. Patch Menu
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Patch Menu"))
        patch_card = self._make_card()
        p_layout = patch_card.layout()

        item_p_vbmeta = CardItemWidget("Patch vbmeta", "Patch AVB 2.0 vbmeta.img flags to disable verity & verification")
        item_p_vbmeta.clicked.connect(self.action_patch_vbmeta.emit)
        p_layout.addWidget(item_p_vbmeta)

        item_p_integ = CardItemWidget("Integrity fix", "Changing device fingerprint to Pixel 7 Pro")
        item_p_integ.clicked.connect(self.action_patch_integrity.emit)
        p_layout.addWidget(item_p_integ)

        item_p_safety = CardItemWidget("Patch SafetyCore", "Patch Google spyware by adding a SafetyCore placeholder.")
        item_p_safety.clicked.connect(self.action_patch_safetycore.emit)
        p_layout.addWidget(item_p_safety)

        item_p_priv = CardItemWidget(
            "Patch Priv-App Permissions",
            "Removing ro.control_privapp_permissions skips priv-app permissions enforcement, ignoring privapp-permissions.xml rules",
        )
        item_p_priv.clicked.connect(self.action_patch_privapp.emit)
        p_layout.addWidget(item_p_priv)

        item_p_ota = CardItemWidget(
            "Disable OTA Update",
            "This will disable automatic OTA updates on your ROM, stop the system from downloading and updates by default",
        )
        item_p_ota.clicked.connect(self.action_patch_ota.emit)
        p_layout.addWidget(item_p_ota)

        item_p_xiaomi = CardItemWidget(
            "Disable xiaomi services",
            "Freeing background processes for better performance and system optimization",
        )
        item_p_xiaomi.clicked.connect(self.action_patch_xiaomi.emit)
        p_layout.addWidget(item_p_xiaomi)

        content_layout.addWidget(patch_card)

        # -------------------------------------------------------------
        # 7. Rom Menu
        # -------------------------------------------------------------
        content_layout.addWidget(self._make_section_header("Rom Menu"))
        rom_card = self._make_card()
        rom_layout = rom_card.layout()

        item_r_debloat = CardItemWidget(
            "Debloat Miui/HyperOS",
            "Debloat Works on all MIUI versions 13/14 and HyperOS releases 1.0/2.0/2.0.2 safely removing bloatware to boost performance and free resources",
        )
        item_r_debloat.clicked.connect(self.action_rom_debloat.emit)
        rom_layout.addWidget(item_r_debloat)

        item_r_oat = CardItemWidget(
            "Remove oat",
            "Delete the `oat` folder to free up space and prevent optimized ART files from being used",
        )
        item_r_oat.clicked.connect(self.action_rom_remove_oat.emit)
        rom_layout.addWidget(item_r_oat)

        item_r_rw = CardItemWidget(
            "Make full Rom-RW",
            "Enables full read-write access to ROM, allowing modifications and customization",
        )
        item_r_rw.clicked.connect(self.action_rom_make_rw.emit)
        rom_layout.addWidget(item_r_rw)

        item_r_decrypt = CardItemWidget(
            "Rom decryption",
            "By modifying fstab, allowing dirty flash",
        )
        item_r_decrypt.clicked.connect(self.action_rom_decrypt.emit)
        rom_layout.addWidget(item_r_decrypt)

        content_layout.addWidget(rom_card)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _make_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section_header")
        return lbl

    def _make_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card_container")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        return card
