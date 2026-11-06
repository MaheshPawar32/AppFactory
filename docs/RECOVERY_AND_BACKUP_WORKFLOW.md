# Recovery and Backup Workflow

- Use Git commits as the preferred recovery points; keep credentials and private signing material out of Git.
- Before broad changes, create a dated external backup or commit after reviewing the working tree.
- Keep generated build output out of backups unless required for diagnosis.
- Verify a backup by listing its contents and, when appropriate, opening/extracting a test copy.
- Recover only the intended files. Compare before overwriting current work.
- Database-backed apps need database exports and a tested restore procedure; source backup alone is insufficient.
- Never report a backup as verified until its archive/file was actually checked.
