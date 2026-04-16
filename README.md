# Maintainer

> Daily, AI-powered triage for your GitHub issue backlog — posted as a Discussion comment every morning.

**Maintainer** is a GitHub Actions automation that uses OpenAI to classify every open issue in a repository as `bug`, `feature`, `question`, or `duplicate`, then posts a formatted summary report as a comment on a designated GitHub Discussion. It's a drop-in, zero-infra way for maintainers of busy open-source projects to wake up to a sorted inbox.

---

## Who This Is For

If any of these sound like you, Maintainer is built for you:

- You maintain an open-source project with a growing issue backlog you never quite catch up on.
- You run a team repo where tickets pile up faster than anyone can triage them.
- You want a daily "state of the issues" briefing without setting up a webhook server, a database, or a dashboard.
- You'd like a consistent first-pass label on every new issue so you can decide what to work on at a glance.

---

## What It Does

Every day at 08:00 UTC (or on manual trigger), the `Daily Issue Classifier` workflow runs through these steps:

- **Fetch open issues:** All open issues are retrieved from the repository via the GitHub REST API. Pull requests are skipped.
- **AI classification:** Each issue's title and body is sent to OpenAI (default model: `gpt-4o-mini`). The model returns exactly one label — `bug`, `feature`, `question`, or `duplicate` — plus a one-sentence justification. Rate limits and transient API errors are retried with exponential backoff.
- **Save results:** A `classified_issues.csv` file is written and uploaded as a workflow artifact (kept for 7 days) containing the issue number, title, assigned label, and the model's reasoning.
- **Post Discussion comment:** The CSV is read, a Markdown report is built, and it is posted as a new comment on a pre-configured GitHub Discussion via the GitHub GraphQL API. The report contains a summary table (count and percentage share per category) and per-category tables linking to each issue with the model's reason.

---

## Quick Start

1. **Fork or copy this repository** into your own account/org.
2. **Create a GitHub Discussion** in the target repo — this is where the daily report will be posted. Note its number (visible in the URL, e.g. `/discussions/5`).
3. **Add repository secrets** (Settings → Secrets and variables → Actions → Secrets):
   - `GH_PAT` — a fine-grained or classic personal access token with `repo` and `discussions` scopes.
   - `OPENAI_API_KEY` — your OpenAI API key.
4. **Add repository variables** (Settings → Secrets and variables → Actions → Variables):
   - `DISCUSSION_NUMBER` — the number of the Discussion you created.
   - `OPENAI_MODEL` — optional; defaults to `gpt-4o-mini`.
   - `MAX_ISSUES` — optional; `0` means classify all open issues.
5. **Trigger a dry run** from the Actions tab: open *Daily Issue Classifier*, click *Run workflow*, tick *dry_run*, and run. The workflow will print the report to the logs without posting.
6. **Let it run on schedule.** Once the dry run looks right, the daily cron (08:00 UTC) will post real reports.

---

## Repository Structure

| File | Purpose |
|------|---------|
| `.github/workflows/daily-issue-classifier.yml` | GitHub Actions workflow — schedules the daily run, wires secrets/vars, uploads the CSV artifact |
| `classify_github_issues.py` | Fetches open issues via PyGithub, classifies each with OpenAI (with retry/backoff), writes `classified_issues.csv` |
| `post_discussion_comment.py` | Reads the CSV, builds a Markdown report, and posts it as a comment on the target Discussion via the GitHub GraphQL API |
| `requirements.txt` | Pinned Python dependencies: PyGithub, openai, requests |
| `Discussion 1` | The GitHub Discussion used as the posting target for daily reports |

---

## Configuration

| Name | Kind | Description |
|------|------|-------------|
| `GH_PAT` | Secret | GitHub personal access token with `repo` and `discussions` scopes |
| `OPENAI_API_KEY` | Secret | OpenAI API key |
| `OPENAI_MODEL` | Variable | Model to use (default: `gpt-4o-mini`) |
| `MAX_ISSUES` | Variable | Max issues to classify per run (`0` = all) |
| `DISCUSSION_NUMBER` | Variable | Number of the Discussion to post the report to |
| `REQUEST_DELAY` | Env (optional) | Seconds to sleep between OpenAI calls (default: `0.5`) |
| `MAX_RETRIES` | Env (optional) | Retry attempts for transient API errors (default: `3`) |

---

## Workflow Triggers

- **Scheduled:** daily at `0 8 * * *` (08:00 UTC).
- **Manual (`workflow_dispatch`):** supports `max_issues` and `dry_run` inputs. In dry-run mode the report is printed to the log but not posted to the Discussion.
- **Concurrency:** a single run at a time; a new scheduled run won't start while another is in progress.

---

## Contributing

Contributions are very welcome — this project is deliberately small and hackable, and there's lots of room to improve it. If you're reading this, **you** are the kind of person this project needs.

**Good first issues / ideas to pick up:**

- Support additional labels beyond the four built-in categories (e.g. `docs`, `security`, `performance`) via a config file.
- Add a local-mode runner that prints a report without touching Discussions (useful for trying it on any repo).
- Swap the OpenAI client for a provider-agnostic interface so Anthropic, Gemini, or a local Ollama model can be dropped in.
- Add unit tests around `build_comment` and the classifier's label-normalization logic.
- De-duplicate detection: compare new issues to recently-closed ones and flag likely duplicates with links.
- Post a weekly *trend* summary (new bugs opened vs. closed) in addition to the daily snapshot.

**How to contribute:**

1. Open an [issue](../../issues) to discuss the idea, or jump into the [Discussions](../../discussions) tab.
2. Fork the repo and create a feature branch.
3. Keep PRs small and focused; include a brief description of what changed and why.
4. Run the workflow in `dry_run` mode against your fork before opening the PR to confirm it still produces a valid report.

**Found a bug?** Open an issue with the workflow run URL (if applicable) and a copy of the failing log line — the classifier logs every step, so errors are usually easy to trace.

**Want to use this on your own repo but hit a snag?** Open a Discussion. Setup help is absolutely in scope, and your question will probably help someone else.

---

## License

No license has been added yet. If you'd like to use Maintainer in your own project, please open an issue and we'll sort out a proper open-source license (MIT is the likely choice).
