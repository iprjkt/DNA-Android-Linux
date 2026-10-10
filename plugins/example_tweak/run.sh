#!/bin/bash
set -e

echo "=== DNA-Linux Example Plugin Running ==="
echo "Project Name:     $DNA_PROJECT_NAME"
echo "Project Root:     $DNA_PROJECT"
echo "Unpacked Tree:    $DNA_UNPACKED"
echo "Output Directory: $DNA_OUT"
echo "Arguments:        $@"

# Example action: ensure unpacked directory exists and log activity
if [ -d "$DNA_UNPACKED" ]; then
    echo "Found active unpacked tree with $(find "$DNA_UNPACKED" -maxdepth 2 | wc -l) items."
fi

echo "=== Example Plugin Completed Successfully ==="
exit 0
