# Bash completion for DNA-Linux (dna)
_dna_completion() {
    local cur prev words cword
    _init_completion || return

    local commands="convert doctor gui jar patch plugin project repack resize rom super tui unpack unzip-rom"
    local options="-V --version -p --project -n --dry-run -v --verbose -y --yes --log-file -h --help"

    if [[ $cword -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$commands $options" -- "$cur") )
        return 0
    fi

    case "${words[1]}" in
        project)
            COMPREPLY=( $(compgen -W "create select delete list" -- "$cur") )
            ;;
        rom)
            COMPREPLY=( $(compgen -W "unzip debloat remove-oat make-rw decrypt" -- "$cur") )
            ;;
        unpack)
            COMPREPLY=( $(compgen -W "bin br dat img zstd super" -- "$cur") )
            ;;
        repack)
            COMPREPLY=( $(compgen -W "img zstd super" -- "$cur") )
            ;;
        convert)
            COMPREPLY=( $(compgen -W "img-simg img-dat-br" -- "$cur") )
            ;;
        super)
            COMPREPLY=( $(compgen -W "split merge" -- "$cur") )
            ;;
        jar)
            COMPREPLY=( $(compgen -W "core-patch-dsv remove-apk-protection disable-secure-screenshot patch-all" -- "$cur") )
            ;;
        patch)
            COMPREPLY=( $(compgen -W "vbmeta integrity-fix safetycore privapp-permissions disable-ota disable-xiaomi-services" -- "$cur") )
            ;;
        plugin)
            COMPREPLY=( $(compgen -W "list info import run delete" -- "$cur") )
            ;;
        *)
            _filedir
            ;;
    esac
}

complete -F _dna_completion dna
