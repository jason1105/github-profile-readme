# Setup Guide — GitHub Profile README

## Critical: Repo naming

GitHub activates a special profile README **only** when the repository is named
identically to your username.

```
github.com/jason1105/jason1105   ✅  shown on your profile page
github.com/jason1105/profile     ✗   just a normal repo
```

Create (or rename) the repo so that **owner == repo name**, then push this
directory to the `main` branch.

---

## Quick start

```bash
# Clone or init the repo with the correct name
git clone git@github.com:jason1105/jason1105.git
# Copy these files in, then:
git add .
git commit -m "feat: add auto-updating profile README"
git push origin main
```

The workflow triggers on every push to `main` **and** on a 6-hour schedule.
The first run generates a fully populated README.md automatically.

---

## Permissions the workflow needs

The built-in `GITHUB_TOKEN` is sufficient — no extra secrets required.
The workflow requests `contents: write` via its `permissions` block, which
GitHub grants automatically.

If your repo has **Actions → General → Workflow permissions** set to
"Read repository contents and packages", change it to
"Read and write permissions" under:

```
Settings → Actions → General → Workflow permissions
```

---

## Personalising the content

Edit `data/profile.yml` and push:

| Field | Effect |
|---|---|
| `name` / `title` / `tagline` | Shown in the About Me section |
| `currently_learning` | Bullet list of tech you are exploring |
| `fun_fact` | Displayed in the ⚡ row |
| `social.github` | Fallback username when `GITHUB_USER` env var is absent |
| `projects[].name` | Repo names used for the pinned-card URLs |
| `digest_url` | Override the JSON endpoint for the weekly digest |

---

## How the auto-update works

```
Schedule / push
     │
     ▼
.github/workflows/update-readme.yml
     │
     ├─ GitHub API  ──▶  total stars, recent commits, top languages
     ├─ Digest API  ──▶  latest.json headline + summary
     └─ data/profile.yml ──▶ personal config
     │
     ▼
scripts/update_readme.py
     │  reads  README.template.md
     │  writes README.md  (with placeholders replaced)
     │
     ▼
git commit + push  (only when README.md actually changed)
```

**Placeholders in README.template.md:**

| Placeholder | Replaced with |
|---|---|
| `GITHUB_USER` | Actual GitHub username |
| `{TOTAL_STARS}` | Sum of stars across all owned repos |
| `{RECENT_ACTIVITY}` | Last 5 push-event commit messages |
| `{WEEKLY_DIGEST}` | Latest digest title + summary |
| `{LAST_UPDATED}` | UTC timestamp of the current run |

---

## Services used (all free)

| Service | Purpose | URL |
|---|---|---|
| capsule-render | Wave header / footer image | capsule-render.vercel.app |
| readme-typing-svg | Animated tagline | readme-typing-svg.demolab.com |
| github-readme-stats | Stats card + language card + pin cards | github-readme-stats.vercel.app |
| streak-stats | Contribution streak | streak-stats.demolab.com |
| activity-graph | Contribution graph | github-readme-activity-graph.vercel.app |
| github-profile-trophy | Trophy display | github-profile-trophy.vercel.app |
| shields.io | All flat/for-the-badge badges | shields.io |
| komarev.com | Profile view counter | komarev.com/ghpvc |

All image services are called by GitHub's Camo proxy when the page is viewed —
no credentials needed, and the stat images update on their own schedule.

---

## Running the script locally

```bash
cd github-profile-readme
pip install requests pyyaml
GITHUB_TOKEN=$(gh auth token) GITHUB_USER=jason1105 python scripts/update_readme.py
```

The script only writes `README.md`; the template is never modified.
