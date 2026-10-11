# Severity Rubric

The category → tier map is **data**, in the run's `audit-config/global.json` →
`severityPolicy`. This file explains what each tier *means* and how the guardrail
is allowed to move a finding within it. It never overrides the JSON; if the two
disagree, the JSON wins and the rubric is stale.

## Tiers

| Tier | Meaning | Effect on verdict |
| --- | --- | --- |
| **Critical** | A finding that makes the repo unsafe to publish as a professional artifact. | Forces `BLOCK`. Non-overridable by the persona. Cleared only by fixing it or by a recorded human waiver. |
| **High** | Embarrassing or misleading, but not dangerous. Must be fixed before publish. | Does not force BLOCK on its own, but a repo with open High findings is not "ready." |
| **Medium** | Soft quality signal a reviewer notices. Should fix. | Advisory. |
| **Low / Info** | Worth noting, harmless. | Note only. |

## Category → tier (mirror of `severityPolicy`, keep in sync)

- **Critical:** `live-secret`, `company-identity-in-history`,
  `copyleft-dependency-in-apache-repo`, `colleague-directed-venting`.
- **High:** `dead-secret-in-history`, `profanity-in-commit-message`,
  `broken-readme-claim`.
- **Medium:** `dead-code`, `commented-out-code-block`, `dead-link`, `typo`,
  `known-vulnerability`.
- **Low:** `todo-fixme-census`, `undocumented-harmless-branch`,
  `weak-copyleft-dependency`.

## Allowed movement (with evidence only)

- **Downgrade to noise:** the finding matches a `secretAllowlist` entry
  (fixture, path + fingerprint) or `documentedExperimentBranches` (branch is a
  documented asset → becomes "missing README pointer", Low). Cite the config
  entry.
- **Upgrade:** a secret confirmed live (trufflehog verified) upgrades from
  `dead-secret-in-history` (High) to `live-secret` (Critical). Cite the
  verification.
- **No movement without a `raw/` citation.** Intuition is not evidence.

## Waivers

A waiver is the only way a Critical finding stops blocking. It is written by the
human into the per-repo config `waivers.entries` as `{findingId, reason, date}`.
The guardrail reads waivers and reflects them in the verdict, but never authors
one.
