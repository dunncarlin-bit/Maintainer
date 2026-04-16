import os
import time
import logging
import csv
import json
from dataclasses import dataclass
from collections import Counter

from github import Github, GithubException
from openai import OpenAI, OpenAIError, RateLimitError, APIError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_NAME = os.getenv("GITHUB_REPO", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_ISSUES = int(os.getenv("MAX_ISSUES", "0"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "classified_issues.csv")

VALID_LABELS = {"bug", "feature", "question", "duplicate"}


@dataclass
class ClassifiedIssue:
    number: int
    title: str
    label: str
    reason: str


def fetch_open_issues(token: str, repo_name: str) -> list[dict]:
    """Fetch all open issues (excluding PRs) from the given repo."""
    if not token:
        raise ValueError("GITHUB_TOKEN is not set.")
    if not repo_name:
        raise ValueError("GITHUB_REPO is not set.")

    gh = Github(token)
    try:
        repo = gh.get_repo(repo_name)
        logger.info("Connected to: %s", repo.full_name)
    except GithubException as exc:
        raise RuntimeError(f"Could not access '{repo_name}': {exc}") from exc

    issues: list[dict] = []
    for issue in repo.get_issues(state="open"):
        if issue.pull_request:
            continue
        issues.append({
            "number": issue.number,
            "title": (issue.title or "(untitled)").strip(),
            "body": (issue.body or "").strip(),
        })
        if MAX_ISSUES and len(issues) >= MAX_ISSUES:
            break

    logger.info("Fetched %d open issues.", len(issues))
    return issues


SYSTEM_PROMPT = (
    "You are an expert software-project assistant. "
    "Classify GitHub issues into exactly ONE of: bug, feature, question, duplicate. "
    'Reply ONLY with JSON: {"label": "<category>", "reason": "<one-sentence justification>"}'
)


def classify_issue(client: OpenAI, number: int, title: str, body: str) -> ClassifiedIssue:
    """Classify a single issue, retrying on transient errors."""
    user_content = f"Issue #{number}\nTitle: {title}\n\nBody:\n{body[:2000]}"

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            break
        except RateLimitError as exc:
            last_error = f"rate limit: {exc}"
            wait = min(2 ** attempt, 30)
            logger.warning("Rate limited on #%d (attempt %d/%d); sleeping %ds",
                           number, attempt, MAX_RETRIES, wait)
            time.sleep(wait)
        except APIError as exc:
            last_error = f"api error: {exc}"
            logger.warning("API error on #%d (attempt %d/%d): %s",
                           number, attempt, MAX_RETRIES, exc)
            time.sleep(min(2 ** attempt, 10))
        except OpenAIError as exc:
            logger.error("OpenAI error for #%d: %s", number, exc)
            return ClassifiedIssue(number, title, "question", f"(API error: {exc})")
    else:
        return ClassifiedIssue(number, title, "question", f"(retries exhausted: {last_error})")

    content = resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(content)
        label = str(parsed.get("label", "")).lower().strip()
        reason = str(parsed.get("reason", "")).strip()
    except json.JSONDecodeError:
        label, reason = "question", "(parse error)"

    if label not in VALID_LABELS:
        logger.info("Unexpected label %r for #%d; defaulting to 'question'", label, number)
        label = "question"

    return ClassifiedIssue(number, title, label, reason)


def write_csv(path: str, results: list[ClassifiedIssue]) -> None:
    """Write classification results to CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["number", "title", "label", "reason"])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "number": r.number,
                "title": r.title,
                "label": r.label,
                "reason": r.reason,
            })
    logger.info("Saved %s", path)


def main() -> None:
    missing = [n for n, v in [
        ("GITHUB_TOKEN", GITHUB_TOKEN),
        ("GITHUB_REPO", REPO_NAME),
        ("OPENAI_API_KEY", OPENAI_API_KEY),
    ] if not v]
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

    issues = fetch_open_issues(GITHUB_TOKEN, REPO_NAME)
    if not issues:
        logger.info("No open issues to classify; writing empty CSV.")
        write_csv(OUTPUT_CSV, [])
        return

    client = OpenAI(api_key=OPENAI_API_KEY)
    results: list[ClassifiedIssue] = []
    for idx, issue in enumerate(issues, 1):
        logger.info("Classifying %d/%d #%d", idx, len(issues), issue["number"])
        results.append(classify_issue(client, issue["number"], issue["title"], issue["body"]))
        if idx < len(issues):
            time.sleep(REQUEST_DELAY)

    for r in results:
        print(f"#{r.number:<5} {r.label:<12} {r.title[:50]}")

    counts = Counter(r.label for r in results)
    print()
    print("Summary:")
    for lbl in sorted(VALID_LABELS):
        print(f"  {lbl:<12} {counts.get(lbl, 0)}")

    write_csv(OUTPUT_CSV, results)


if __name__ == "__main__":
    main()
