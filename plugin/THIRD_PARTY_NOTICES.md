# Third-party notices

## Matt Pocock's skills

Three skills in this plugin are adaptations, not copies, of files from Matt Pocock's skills (https://github.com/mattpocock/skills), taken at commit `3cca18b368ae95cdbdebbff572ccafa662551015` (2026-09-04). Each keeps his process and templates and adds this plugin's gates, additions and attribution line, so nothing reads his user-only files at runtime (ADR-0002, `docs/adr/0002-seams-owned-flow-skills.md`).

| This plugin | Adapted from (path in the upstream repo at that commit) |
| --- | --- |
| `skills/to-spec/SKILL.md` | `skills/engineering/to-spec/SKILL.md` |
| `skills/to-tickets/SKILL.md` | `skills/engineering/to-tickets/SKILL.md` |
| `skills/implement/SKILL.md` | `skills/engineering/implement/SKILL.md` |

The upstream files' SHA-256 at that commit. His future edits do not flow into the adaptations; to see whether the installed files have moved on, run `shasum -a 256 -c` from `~/.claude/skills` (or `$CLAUDE_CONFIG_DIR/skills`) with the paths below shortened to `<name>/SKILL.md`. `scripts/tests/test_plugin.sh` does that comparison and prints a warning on drift; porting a change is a manual review.

```text
43ad9cf318e5e7d3d1fa360253a37021796dc87a0c2e595ad262661a10f85088  skills/engineering/to-spec/SKILL.md
5c9fba69845c2519b9b35b9af42ae5142c21f8ca15ac2123dc2722002c8058ae  skills/engineering/to-tickets/SKILL.md
6d3fd9e83b8f36e5213854779db49b256a457a7ebb4a503e53fa7dcff696adc3  skills/engineering/implement/SKILL.md
```

Matt Pocock's skills are released under the MIT License:

```text
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Superpowers

Four skills in this plugin come from Superpowers 6.3.0 (https://github.com/obra/superpowers). They were copied from the Claude Code plugin cache at `claude-plugins-official/superpowers/6.3.0/skills/`.

Three of them are unmodified copies, and this plugin never edits them. To check that they are still identical, run `shasum -a 256 -c` from `plugin/`, using the checksums below.

- `skills/using-git-worktrees/SKILL.md`
- `skills/verification-before-completion/SKILL.md`
- `skills/receiving-code-review/SKILL.md`

```text
8cfb86f121269e8f7f12361e6795c4f6738828340e28964c9229d365666c9edd  skills/using-git-worktrees/SKILL.md
2befe7fc55bcadaa3d97dd9e8efeb633d2561c0ebe74c5a8b17c4d9e7e4520b3  skills/verification-before-completion/SKILL.md
091df1629510af1b92fc4abd6f96732ebedb4cb2c0f3457e8f2740b0504a2438  skills/receiving-code-review/SKILL.md
```

The fourth, `skills/finishing-a-development-branch/SKILL.md`, is an adaptation, not a copy. It keeps the original's process and adds one step: after a local merge, it records integration in the feature's progress file (ADR 0003, `docs/adr/0003-committed-progress-file.md`). Its last line attributes the original. The original's SHA-256 at 6.3.0 is below; `scripts/tests/test_plugin.sh` compares it with the plugin cache when the cache is present.

```text
8db5a922b242dd4e1bf824cb91c13b3e8d8e8a86d6ceaf7f0774eb9cce909d65  original: skills/finishing-a-development-branch/SKILL.md
```

Superpowers is released under the MIT License:

```text
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
