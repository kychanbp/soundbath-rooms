#!/bin/zsh
# Usage: bake_all.sh size samples room...
S=$1; N=$2; shift 2
for r in "$@"; do /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/bake.py -- $r $S $N bake > data/bake_$r.log 2>&1; grep -E "DONE|Traceback|Error:" data/bake_$r.log | tail -2; done
