# Maintainer

**Maintainer** is a GitHub Actions-powered automation that uses OpenAI to classify every open issue in a repository daily, then posts a formatted summary report as a comment on a designated GitHub Discussion.

---

## What It Does

Every day at 08:00 UTC (or on manual trigger), the `Daily Issue Classifier` workflow runs through these steps:

- **Fetch open issues:** All open issues are retrieved from the repository via the GitHub REST API. Pull requests are skipped.
- **AI classification:** Each issue's title and body is sent to OpenAI (default model: `gpt-4o-mini`). The model returns exactly one label — `bug`, `feature`, `question`, or `duplicate` — plus a one-sentence justification.
- **Save results:** A `classified_issues.csv` file is written (and uploaded as a workflow artifact, kept for 7 days) containing the issue number, title, assigned label, and the model's reasoning.
- **Post Discussion comment:** The CSV is read, a Markdown report is built, and it is posted as a new comment on a pre-configured GitHub Discussion via the GitHub GraphQL API. The report contains a summary table (count and percentage share per category) and per-category tables linking to each issue with the model's reason.

---

## Repository Structure

| File | Purpose |
|------|---------|
| `.github/workflows/daily-issue-classifier.yml` | GitHub Actions workflow — schedules the daily run, wires secrets/vars, uploads the CSV artifact |
| `classify_github_issues.py` | Fetches open issues via PyGithub, classifies each with OpenAI, prints results, writes `classified_issues.csv` |
| `post_discussion_comment.py` | Reads the CSV, builds a Markdown report, and posts it as a comment on the target Discussion via the GitHub GraphQL API |
| `requirements.txt` | Pinned Python dependencies: PyGithub, openai, requests |
| `Discussion 1` | The GitHub Discussion used as the posting target for daily reports |

---

## Configuration

The workflow reads the following **secrets** and **repository variables**:

| Name | Type | Description |
|------|------|-------------|
| `GH_PAT` | Secret | GitHub personal access token with `repo` and `discussions` scopes |
| `OPENAI_API_KEY` | Secret | OpenAI API key |
| `OPENAI_MODEL` | Variable | Model to use (default: `gpt-4o-mini`) |
| `MAX_ISSUES` | Variable | Max issues to classify per run (0 = all) |
| `DISCUSSION_NUMBER` | Variable | Number of the Discussion to post the report to |

---

## Workflow Triggers

- **Scheduled:** daily at `0 8 * * *` (08:00 UTC)
- **Manual (`workflow_dispatch`):** supports `max_issues` and `dry_run` inputs; in dry-run mode the report is printed to the log but not posted to the Discussion.
