# Example Tweak Plugin for DNA-Linux

This directory contains a reference plugin demonstration for the **DNA-Linux** plugin system.

## Plugin Structure

```
my_plugin/
├── plugin.toml     # Plugin metadata and entrypoint declaration
├── run.sh          # Executable entrypoint (can also be a Python script `run.py`)
└── README.md
```

## Manifest (`plugin.toml`)

```toml
[plugin]
id = "example-tweak"
name = "Example Tweak Plugin"
version = "1.0.0"
author = "DNA Community"
description = "A demonstration plugin showing workspace environment integration."
entrypoint = "run.sh"
min_dna_version = "1.0.0"
```

## Sandboxed Workspace Environment Variables

When executed via `dna plugin run <id>`, DNA-Linux automatically injects:
- `DNA_PROJECT`: Active project root path (`~/DNA/DNA_<project>/`)
- `DNA_PROJECT_NAME`: Project name
- `DNA_UNPACKED`: Unpacked partition directory (`~/DNA/DNA_<project>/unpacked/`)
- `DNA_IMAGES`: Raw partition images directory (`~/DNA/DNA_<project>/images/`)
- `DNA_OUT`: Output directory for repacked files (`~/DNA/DNA_<project>/out/`)
- `DNA_CONFIG`: Configuration and SELinux contexts directory (`~/DNA/DNA_<project>/config/`)
- `DNA_ROM`: Source ROM archive directory (`~/DNA/DNA_<project>/rom/`)
- `DNA_LOGS`: Log directory (`~/DNA/DNA_<project>/logs/`)
- `DNA_PLUGIN_DIR`: Directory where the plugin is installed
- `DNA_PLUGIN_ID`: Identifier of the plugin
