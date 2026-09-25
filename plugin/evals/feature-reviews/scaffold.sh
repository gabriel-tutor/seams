#!/usr/bin/env bash
# This case's workspace: the shared scaffold beside the cases, told where this case is.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$HERE/../_scaffold.sh" "$HERE"
