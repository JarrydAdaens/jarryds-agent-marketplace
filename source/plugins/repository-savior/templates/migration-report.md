# Migration Report — {{repository_name}}

**Final status:** {{final_status}}
**Date:** {{date}}

## Source

- Type: {{source_type}}
- Location: {{source_path}}
- Fingerprint (aggregate SHA-256): `{{source_fingerprint}}`
- Source intact after migration: {{source_verified_unchanged}}

## Conversion

- Converter: {{converter_tool}} ({{converter_version}})
- Source revisions: {{source_revision_count}}
- Git commits: {{git_commit_count}}
- Count deviation explanation: {{count_deviation_explanation}}

### Author mapping

{{author_mapping_table}}

### Branch and tag mapping

{{branch_tag_mapping_table}}

- Default branch: {{default_branch}}

## Publishability

- Large-file findings: {{large_file_findings}}
- Accepted deviations: {{accepted_deviations}}

## Audit

- Result: {{audit_result}}
- Report: {{audit_report_path}}

## GitHub destination

- Repository: {{github_owner}}/{{github_name}}
- Privacy verification: {{privacy_verification_result}}

## Verification

- Local conversion verification: {{local_verification_result}}
- Fresh-clone verification: {{fresh_clone_verification_result}}

## Warnings

{{warnings}}
