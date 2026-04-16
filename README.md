# Maintainer

**Maintainer** is a GitHub Actions-powered automation that uses OpenAI to classify every open issue in a repository daily, then posts a formatted summary report as a comment on a designated GitHub Discussion.

---

## What It Does

Every day at 08:00 UTC (or on manual trigger), the `Daily Issue Classifier` workflow:

1. **Fetches all open issues** from the configured repository via the GitHub API, skipping pull requests.
2. 2. **Classifies each issue** using OpenAI (default: `gpt-4o-mini`). Each issue title and body is sent to the model, which assigns it exactly one label: `bug`, `feature`, `question`, or `duplicate`, along with a one-sentence justification.
   3. 3. **Saves results** to a `classified_issues.csv` artifact (retained for 7 days) containing the issue number, title, assigned label, and the model's reasoning.
      4. 4. **Posts a Markdown summary** as a new comment on a pre-configured GitHub Discussion. The comment includes a summary table showing the count and percentage share for each category, followed by per-category tables listing every issue with a link and the model's reason.
        
         5. ---
        
         6. ## Repository Structure
        
         7. | File | Purpose |
         8. |------|---------|
         9. | `.github/workflows/daily-issue-classifier.yml` | GitHub Actions workflow — schedules the daily run, wires secrets/vars, uploads the CSV artifact |
         10. | `classify_github_issues.py` | Fetches open issues via PyGithub, classifies each with OpenAI, prints results, writes `classified_issues.csv` |
         11. | `post_discussion_comment.py` | Reads the CSV, builds a Markdown report, and posts it as a comment on the target Discussion via the GitHub GraphQL API |
         12. | `requirements.txt` | Pinned Python dependencies: `PyGithub`, `openai`, `requests` |
         13. | `Discussion 1` | The GitHub Discussion used as the posting target for daily reports |
        
         14. ---
        
         15. ## Configuration
        
         16. The workflow reads the following **secrets** and **repository variables**:
        
         17. | Name | Type | Description |
         18. |------|------|-------------|
         19. | `GH_PAT` | Secret | GitHub personal access token with `repo` and `discussions` scopes |
         20. | `OPENAI_API_KEY` | Secret | OpenAI API key |
         21. | `OPENAI_MODEL` | Variable | Model to use (default: `gpt-4o-mini`) |
         22. | `MAX_ISSUES` | Variable | Max issues to classify per run (`0` = all) |
         23. | `DISCUSSION_NUMBER` | Variable | Number of the Discussion to post the report to |
        
         24. ---
        
         25. ## Workflow Triggers
        
         26. - **Scheduled:** daily at `0 8 * * *` (08:00 UTC)
             - - **Manual (`workflow_dispatch`):** supports `max_issues` and `dry_run` inputs. In dry-run mode the report is printed to the log but not posted to the Discussion.
