#!/usr/bin/env bash
# Scenario: the fixture as it is. The request names a GitHub pull request by number, which since 3.3.1 routes to
# pr-review; a local branch or uncommitted work would be code-review's (review-scope).
set -euo pipefail
