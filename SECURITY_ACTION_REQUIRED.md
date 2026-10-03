# Security Action Required

The historical `backups.zip` committed before this source import contains real-looking environment secrets and a Cloudflare tunnel service token. The archive has been removed from the current working tree, but deleting a file in a new commit does **not** remove it from earlier Git history.

Assume every credential inside that archive is exposed, even though the repository is private.

## Rotate now

1. Revoke and recreate the Cloudflare tunnel/service token.
2. Replace PostgreSQL and Neo4j passwords.
3. Replace `JWT_SECRET_KEY` and force users to sign in again.
4. Replace `PJP_SIMULATOR_SECRET`.
5. Replace `PAYER_PSEUDONYM_KEY`; understand that old and new payer pseudonyms will not match.
6. Replace `ML_ARTIFACT_SIGNING_KEY` and regenerate trusted artifact signatures.
7. Check GitHub security/audit logs and any server logs for unexpected use.

Store new values only in ignored `.env` files or a secret manager. Never paste them into shell scripts, documentation, issues, or chat.

## History cleanup

After rotation and team coordination, use `git filter-repo` or GitHub's sensitive-data removal procedure to purge `backups.zip` from every historical commit, then force-push and have every collaborator re-clone. History rewriting is intentionally not performed automatically because it invalidates existing clones and commit references.
