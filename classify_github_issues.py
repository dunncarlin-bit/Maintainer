import os, time, logging, csv
from dataclasses import dataclass
from collections import Counter
from github import Github, GithubException
from openai import OpenAI, OpenAIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_NAME    = os.getenv("GITHUB_REPO", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_ISSUES   = int(os.getenv("MAX_ISSUES", "0"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))
VALID_LABELS = {"bug", "feature", "question", "duplicate"}

@dataclass
class ClassifiedIssue:
    number: int
    title: str
    label: str
    confidence: str

def fetch_open_issues(token, repo_name):
    if not token: raise ValueError("GITHUB_TOKEN is not set.")
    if not repo_name: raise ValueError("GITHUB_REPO is not set.")
    gh = Github(token)
    try:
        repo = gh.get_repo(repo_name)
        logger.info("Connected to: %s", repo.full_name)
    except GithubException as exc:
        raise RuntimeError(f"Could not access '{repo_name}': {exc}") from exc
    issues = []
    for issue in repo.get_issues(state="open"):
        if issue.pull_request: continue
        issues.append({"number": issue.number, "title": issue.title, "body": issue.body or ""})
        if MAX_ISSUES and len(issues) >= MAX_ISSUES: break
    logger.info("Fetched %d open issues.", len(issues))
    return issues

SYSTEM_PROMPT = (
    "You are an expert software-project assistant. "
    "Classify GitHub issues into exactly ONE of: bug, feature, question, duplicate. "
    'Reply ONLY with JSON: {"label": "<category>", "reason": "<one-sentence justification>"}'
)

def classify_issue(client, number, title, body):
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": f"Issue #{number}\nTitle: {title}\n\nBody:\n{body[:2000]}"}],
            temperature=0, max_tokens=120,
            response_format={"type": "json_object"},
        )
    except OpenAIError as exc:
        logger.error("OpenAI error for #%d: %s", number, exc)
        return ClassifiedIssue(number, title, "question", "(API error)")
    import json
    try:
        parsed = json.loads(resp.choices[0].message.content or "{}")
        label = str(parsed.get("label", "")).lower().strip()
        reason = str(parsed.get("reason", ""))
    except json.JSONDecodeError:
        label, reason = "question", "(parse error)"
    if label not in VALID_LABELS: label = "question"
    return ClassifiedIssue(number, title, label, reason)

def main():
    missing = [n for n, v in [("GITHUB_TOKEN", GITHUB_TOKEN), ("GITHUB_REPO", REPO_NAME), ("OPENAI_API_KEY", OPENAI_API_KEY)] if not v]
    if missing: raise EnvironmentError(f"Missing: {', '.join(missing)}")
    issues = fetch_open_issues(GITHUB_TOKEN, REPO_NAME)
    if not issues: return
    client = OpenAI(api_key=OPENAI_API_KEY)
    results = []
    for idx, issue in enumerate(issues, 1):
        logger.info("Classifying %d/%d #%d", idx, len(issues), issue["number"])
        results.append(classify_issue(client, issue["number"], issue["title"], issue["body"]))
        if idx < len(issues): time.sleep(REQUEST_DELAY)
    for r in results:
        print(f"#{r.number:<5} {r.label:<12} {r.title[:50]}")
    counts = Counter(r.label for r in results)
    for lbl in sorted(VALID_LABELS): print(f"  {lbl:<12} {counts.get(lbl,0)}")
    with open("classified_issues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["number","title","label","reason"])
        w.writeheader()
        for r in results: w.writerow({"number":r.number,"title":r.title,"label":r.label,"reason":r.confidence})
    logger.info("Saved classified_issues.csv")

if __name__ == "__main__":
    main()
