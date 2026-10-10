# Fish completion for DNA-Linux (dna)

# Top-level commands
set -l commands doctor gui tui project rom unpack repack resize convert super jar patch plugin unzip-rom

complete -c dna -f
complete -c dna -n "not __fish_seen_subcommand_from $commands" -s V -l version -d "Show version"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -s p -l project -d "Target project"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -s n -l dry-run -d "Simulate execution"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -s v -l verbose -d "Verbose output"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -s y -l yes -d "Auto-confirm prompts"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -s h -l help -d "Show help"

complete -c dna -n "not __fish_seen_subcommand_from $commands" -a doctor -d "Check dependencies and tool health"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a gui -d "Launch Desktop Graphical User Interface"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a tui -d "Launch Terminal User Interface"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a project -d "Manage workspaces"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a rom -d "ROM operations"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a unpack -d "Unpack images and archives"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a repack -d "Repack partitions and super.img"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a resize -d "Resize ext4 images"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a convert -d "Format conversions"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a super -d "Split and merge super.img"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a jar -d "Patch services.jar"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a patch -d "System and AVB patches"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a plugin -d "Manage and execute plugins"
complete -c dna -n "not __fish_seen_subcommand_from $commands" -a unzip-rom -d "Extract ROM archive"

# Subcommands
complete -c dna -n "__fish_seen_subcommand_from project" -a "create select delete list"
complete -c dna -n "__fish_seen_subcommand_from rom" -a "unzip debloat remove-oat make-rw decrypt"
complete -c dna -n "__fish_seen_subcommand_from unpack" -a "bin br dat img zstd super"
complete -c dna -n "__fish_seen_subcommand_from repack" -a "img zstd super"
complete -c dna -n "__fish_seen_subcommand_from convert" -a "img-simg img-dat-br"
complete -c dna -n "__fish_seen_subcommand_from super" -a "split merge"
complete -c dna -n "__fish_seen_subcommand_from jar" -a "core-patch-dsv remove-apk-protection disable-secure-screenshot patch-all"
complete -c dna -n "__fish_seen_subcommand_from patch" -a "vbmeta integrity-fix safetycore privapp-permissions disable-ota disable-xiaomi-services"
complete -c dna -n "__fish_seen_subcommand_from plugin" -a "list info import run delete"
