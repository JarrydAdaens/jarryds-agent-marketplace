---
name: inspect-organization-access
description: >-
  Use when reporting who can effectively access a private repository under
  the configured GitHub owner: the organization's base repository
  permission and relevant team or user grants. Reporting and gating only —
  it never modifies organization permissions, and it never assumes members
  can or cannot access private repositories. Writes only into the
  user-specified migration root and refuses to run without one. Triggers:
  "who can see this private repo", "inspect org access", "check base
  permissions before publishing".
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Inspect Organization Access

A private repository in an organization is not "visible to nobody" — access
depends on the organization's base permission plus explicit user, team, and
repository grants. This skill reports that reality so the human publishes
with open eyes. It is Gate 5's observability half; the hardening itself is
human work in GitHub settings.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; owner from config
`github.target_owner`.

## Contract

- **Read-only against GitHub.** Query via `gh api` / `gh` commands only;
  never modify organization or repository permissions.
- Never assume: a personal owner has no base-permission concept; an
  organization's base permission may be anything from `none` to `write`.
  Report what the API actually returns, including "insufficient scope to
  query" as an explicit finding rather than a silent gap.

## What to report

- Owner type (user vs. organization);
- for organizations: base repository permission
  (`gh api orgs/<owner> --jq .default_repository_permission`), whether
  members can create repositories, and private-fork policy where readable;
- teams or users that would receive access to a new private repository
  under current settings, where readable.

## Recommended hardening (report, do not perform)

Base repository permission at the minimum required; repository creation
restricted to trusted roles; private-repository forking disabled unless
required.

## Outputs

`WS/manifests/org-access.json` with the findings, plus the human-facing
summary in the migration report.

## State

Append an informational transition; this skill does not advance the main
state, but an inability to confirm the owner exists and is usable is a
`BLOCKED` condition before creation.
