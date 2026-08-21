# Deployment Runbook

This runbook covers the current public-site deployment arrangement for the trapping dashboard.

## Current Deployment Shape

- Development repository: `wimericvandijk/mv_trapping_graphs`
- Development repository visibility may be public, but it should not deploy its own GitHub Pages site
- Public site repository: `MarsdenValleyTrappers/trapping_graphs`
- Public site URL: `https://marsdenvalleytrappers.github.io/trapping_graphs/`
- Publish workflow: `.github/workflows/publish-public-site.yml`
- In-repo GitHub Pages workflow: removed
- Publish workflow triggers: push to `main`, successful completion of `Nightly Data Refresh`, or manual `workflow_dispatch`
- Workflow secret used for cross-repository publish: `PUBLIC_SITE_DEPLOY_TOKEN`
- Current token owner: `MarsdenValley` GitHub user

## Current Repository Variables And Secrets

In the development repository, the publish workflow expects:

- repository secret `PUBLIC_SITE_DEPLOY_TOKEN`
- repository variable `PUBLIC_SITE_REPO=MarsdenValleyTrappers/trapping_graphs`
- repository variable `PUBLIC_SITE_BRANCH=main`

Keep GitHub Pages disabled in `wimericvandijk/mv_trapping_graphs` so the repository does not publish to `https://wimericvandijk.github.io/mv_trapping_graphs/`.

## Replacing The Deployment Token

Use these steps when the current `PUBLIC_SITE_DEPLOY_TOKEN` is nearing expiry.

1. Sign in to GitHub as the `MarsdenValley` user.
2. Open `Settings`.
3. Open `Developer settings`.
4. Open `Personal access tokens`.
5. Open `Tokens (classic)`.
6. Create a new classic token.
7. Give the token a clear name such as `mv_trapping public site publish`.
8. Set an expiry that satisfies the organisation policy.
9. Grant the `repo` scope.
10. Generate the token and copy it immediately.
11. Open the development repository `wimericvandijk/mv_trapping_graphs`.
12. Open `Settings`.
13. Open `Secrets and variables`.
14. Open `Actions`.
15. Replace the repository secret `PUBLIC_SITE_DEPLOY_TOKEN` with the new token value.
16. Open the `Actions` tab in the development repository.
17. Run the workflow `Publish Static Site To Public Repo` manually once.
18. Confirm the workflow succeeds.
19. Confirm that `MarsdenValleyTrappers/trapping_graphs` receives the updated published files.
20. Confirm that the public site at `https://marsdenvalleytrappers.github.io/trapping_graphs/` still loads.
21. Revoke the old token from the `MarsdenValley` user account after the replacement is confirmed.

## When The Token Expires

- The public site stays live with the last successfully published files.
- New publish workflow runs will fail until `PUBLIC_SITE_DEPLOY_TOKEN` is replaced.
- Replacing the secret and rerunning the publish workflow restores normal operation.

## Quick Validation Checklist

After replacing the token, verify all of these:

- the workflow `Publish Static Site To Public Repo` succeeds
- the public repository receives a new commit when there are site changes
- the public Pages URL still loads correctly
- the old token is revoked only after the new token is proven

## Ongoing Validation Checklist

Use this checklist for routine checks on the development repository.

1. Open the development repository `wimericvandijk/mv_trapping_graphs`.
2. Open `Actions`.
3. Check the latest `Nightly Data Refresh` workflow run.
4. Confirm the nightly workflow completed successfully.
5. If the nightly workflow published changed site output, confirm the latest `Publish Static Site To Public Repo` workflow also completed successfully.
6. Open the public repository `MarsdenValleyTrappers/trapping_graphs`.
7. Confirm a fresh automated commit appeared there when the latest run produced changed site output.
8. Open `https://marsdenvalleytrappers.github.io/trapping_graphs/`.
9. Confirm the public site still loads correctly.
10. If you run `Publish Static Site To Public Repo` manually from the development repository, confirm it succeeds.
11. Treat `No public site changes to publish` as an expected success result when the generated site files are unchanged.
12. If any validation step fails, investigate before relying on the next scheduled publish.

## Troubleshooting

If the publish workflow fails after a token replacement:

1. Check that the new token was created from the `MarsdenValley` user.
2. Check that the token has the `repo` scope.
3. Check that `PUBLIC_SITE_DEPLOY_TOKEN` was updated in the development repository rather than the public repository.
4. Check that `PUBLIC_SITE_REPO` is still `MarsdenValleyTrappers/trapping_graphs`.
5. Check that `PUBLIC_SITE_BRANCH` is still `main`.
6. Re-run the workflow manually and read the exact failed step.

If the publish workflow succeeds but shows `No public site changes to publish`:

1. Treat that as a valid confirmation that cross-repository publish still has access.
2. Confirm the public Pages URL still loads.
3. Wait for the next run that produces changed site output to confirm an automated commit lands in the public repository.

## Calendar Reminder Suggestion

Set reminders for token rotation before expiry:

- 30 days before expiry
- 7 days before expiry

That gives enough time to replace the secret and test the workflow without urgency.
