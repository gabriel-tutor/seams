#!/usr/bin/env bash
# A ladder scenario: no scenario-specific state. The baseline fixture already has formatLine (src/format.ts) and
# subtotalCents (src/cart.ts), and the standard library groups thousands, so a receipt needs little new code.
set -euo pipefail
