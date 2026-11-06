# Security and privacy audit

This is a review checklist, not a guarantee of security or legal compliance.

## Configuration and secrets
- [ ] Search source, logs and repository history for accidental credentials.
- [ ] Keep signing keys, service account credentials and production secrets outside Git.
- [ ] Verify `.gitignore`; remember ignore rules do not remove files already tracked.
- [ ] Use least-privilege API keys and backend authorization.
- [ ] Do not place server secrets in a Flutter client or client-readable environment file.

## Permissions and data
- [ ] Request only permissions needed for an explained feature.
- [ ] Explain permission requests in context and handle denial gracefully.
- [ ] Document what personal data is collected, why, where it is stored and how long it is retained.
- [ ] Avoid logging personal or authentication data.
- [ ] Provide account/data deletion and export where required by the product.
- [ ] Check backups, analytics, crash reports and third-party SDK data behavior.

## Network and backend
- [ ] Use TLS for remote APIs.
- [ ] Enforce authorization and validation on the server, not only in the UI.
- [ ] Review database rules, file access rules, rate limits and abuse protections.
- [ ] Handle expired sessions, network failures and malformed responses.
- [ ] Do not treat obfuscation as a substitute for secret management.

## Release and policy
- [ ] Verify the actual target audience, content rating, ads and data safety declarations.
- [ ] Publish a privacy policy that matches actual app behavior.
- [ ] Review consent requirements for the regions and SDKs used.
- [ ] Check third-party SDK terms and permissions.
- [ ] Record unresolved risks; do not claim compliance without evidence and appropriate review.
