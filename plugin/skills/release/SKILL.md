---
name: release
description: Use when the user says ship, deploy, release, publish or go live, or when an integrated candidate is to reach a host, a store, a registry or a marketplace
---

# Release

Take an integrated candidate to its target and prove that exact candidate is what runs. Readiness first; a deploy only after a yes that names what is being deployed where; then verification, then the operations handover. Nothing here deploys, publishes or uploads before the Deploy step's yes.

**Shared rules:** `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/rules.md`, read when a step names one of its sections. **Effort** `${CLAUDE_EFFORT}`: nothing to skip at `low` (shared rules: Effort).

**Repository facts.** The Seams hook adds them as this skill starts (shared rules: Repository facts).

## Gate

Establish three facts, from the repo where the repo can answer (facts are not questions):

1. **Candidate.** The exact commit: the SHA the user names, or `git rev-parse HEAD` on the base branch with a clean tree. A dirty tree has no candidate. A candidate still on its own branch is *built*, not integrated: integrate it first (`seams:finishing-a-development-branch`) and release from the base branch.
2. **Target.** Where the work runs: the user's words, the spec's Release section, or the repo's deploy configuration (a platform config file, a deploy workflow or script, a publish script, a store or marketplace manifest). See the target table below.
3. **Environment.** The environments the target has (staging, preview, a test track, production) and which one this release is for.

Then ask with AskUserQuestion, recommended answer first: "Release candidate `<sha>` to `<target>`, environment `<environment>`: check readiness now?" Skip this only when the user's last message asked for the release, or a yes earlier in this request covered it ("then take it to staging"); reaching this skill on your own initiative always asks, and the Deploy step's question is never skipped. What the repo cannot answer is an unmet row in the readiness table, asked there; do not ask for what a file already says.

## Readiness

Check every row and report one table: row, ready / unmet / not applicable, and the evidence (the file, the command and its output). **Anything unmet blocks:** no deploy until every row is ready or explicitly not applicable with the reason.

| Row | What counts as ready |
| --- | --- |
| Target and environment | named (the gate's facts) and reachable: the platform's CLI or skill is installed and signed in. With no deploy target, this row is unmet: report "no deploy target" and ask for one |
| Integrated candidate | the SHA is on the base branch and `git status --short` is empty; it is the candidate `implement`'s definition of done covered, after its review and fixes, or that candidate as `finishing-a-development-branch` integrated and recorded it, whose suite then runs here |
| Suite green on that SHA | the full suite ran on the candidate with its output shown (shared rules: Evidence) |
| Artifact built and identified | built with the repo's own build command and named by version and SHA (image tag, package version, bundle, installer) |
| Config and variables per environment | every variable the code reads is named per environment (`.env.example`, the platform's config), secrets live in the platform's store, none in the artifact or the repo |
| Migration and restore | when data changes shape: an expand–contract plan, the migration rehearsed on a copy, and the restore rehearsed; otherwise not applicable |
| Abort conditions and rollback path | what would make you abort, and the exact command or action that puts the previous version back |
| Applicable checks | a dependency audit; a secret scan; accessibility for a UI; a load check when the design lens flagged scale; each ready, or not applicable with the reason |
| Smoke plan | the two or three journeys to run against the deployed candidate, and the version endpoint or marker that identifies what runs |

Then ask with AskUserQuestion, recommended answer first: which unmet rows to close now (each through the skill or command that owns it: `seams:foundations` for a missing pipeline, environment config or monitoring; the platform's skill for its setup), or the missing facts (the target, the environment). A yes to closing a row is not a yes to deploying.

## Deploy

1. **The question.** Ask with AskUserQuestion, **every time**: "Deploy candidate `<sha>` to `<target>`, environment `<environment>`?" A yes given earlier, to `implement`, to the readiness question, or as "ship it" or "go all the way", never covers a deploy; the question names the target, the environment and the candidate, and the deploy waits for that yes.
2. **Staged environment first.** When the target has a staged environment (staging, a preview deployment, an internal or test track, a beta channel, a prerelease tag), deploy there first and run the Verify step against it. Production, or the public listing, gets its own question and its own yes after the staged verification passed.
3. **Through the platform's own tooling.** Use the platform's skill when one is installed (for example `vercel:deploy`, `expo:eas-app-stores`, `wrangler`), otherwise its CLI, as its docs say (shared rules: Official docs). Never a hand-rolled upload when the platform has a CLI.
4. **Person-only steps** (a store console upload, a review submission, a 2FA or OTP prompt, a signing credential) are handed to the user as exact steps in order, and the release waits for them. Steps that only a person can take are never worked around.

## Verify

Against the environment just deployed, with the output shown:

1. **Running version equals the candidate.** Read the version endpoint, build marker or the platform's deployment SHA and compare the running version with the candidate's SHA or version. "Deployed" means the exact candidate is what runs, not that a deploy command returned 0.
2. **Smoke journeys.** Run the smoke plan's journeys against the running candidate.
3. **A short watch.** Watch errors and logs for a few minutes through the platform's logs or dashboard command; note what was seen.
4. **On any failure, abort.** Execute the rollback path from the readiness table, confirm the previous version is what runs, and report the failure with what was seen. A release is reverted, never "deployed with issues".

## Operations handover

First record the release in the feature's progress file, when the work has one (`.scratch/<feature>/progress.md`, in the format `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md` describes): `Stage` the stage reached below and `Updated` today; `Status: done` once the candidate is verified in the last environment the spec's Release section names, and until then `Next` says what is left (an unmet row, the production deploy). Commit it by name.

The closing message, in this order:

1. **Monitoring and alert owner.** Where errors and health are watched, and the person an alert reaches.
2. **Runbook.** Where the runbook is. When there is none, say so and offer `seams:foundations`, whose offer writes the skeleton.
3. **Follow-ups.** Tickets for anything deferred: an unmet row closed provisionally, a check marked not applicable that should exist, the production deploy still to come.
4. **Stage reached** (shared rules: Stages). A release that stopped at readiness leaves the candidate at the stage it arrived with, and says why it stopped.

## Targets

The steps scale to the target. Person-only steps are handed to the user; nothing else changes.

| Target | Staged environment | Artifact | Version check | Rollback | Person-only steps |
| --- | --- | --- | --- | --- | --- |
| Web host (Vercel, Netlify, Cloudflare Pages, a PaaS) | preview or staging deployment | the platform's build | the deployment's SHA, or a version endpoint | promote or redeploy the previous deployment | usually none |
| Container or VPS | a staging host or a canary | an image tagged with version and SHA | `/version` or the image digest on the host | redeploy the previous tag | usually none |
| Mobile store (App Store, Play) | TestFlight, an internal or closed track | a signed build (EAS, fastlane) | the build number in the store console | halt a phased rollout, or promote the previous build | console upload, review submission, phased-rollout controls |
| CLI or library registry (npm, PyPI, crates) | a prerelease tag (`next`, an rc) | the packed tarball, wheel or crate | `npm view <pkg> version` or the registry's equivalent | publish a patch; registries do not unpublish | the 2FA or OTP prompt on publish |
| Browser extension store | an unlisted or test listing | the zipped bundle with its manifest version | the version on the listing and in the browser's extensions page | upload the previous package, or halt the rollout | dashboard upload, review submission |
| Desktop (Electron, Tauri, native) | a beta channel | signed installers per OS | the app's about or version screen | pull the release and re-point the update feed | notarization and signing credentials, store submissions |
