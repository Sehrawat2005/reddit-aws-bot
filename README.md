# reddit-aws-bot

Semi-automated drafting assistant for r/AWSForStartuppz posts, written as
short, anonymized client case studies (industry + problem + what was done +
outcome - never the client's name) from the voice of an AWS cloud
consulting partner. Every day it researches a trending AWS angle, drafts a
post (via Groq), and sends it to you on Telegram for review. Reply
**"done"** and it sends back a clean copy-paste-ready version — **you post
it to Reddit yourself, manually**. (Reddit closed self-service API app
creation in late 2025; see "Why no auto-posting" below.) Runs entirely on
GitHub Actions, triggered by cron-job.org pings, so it works even when your
laptop is off.

Note: case-study-style posts read more like service marketing than a
personal story would, even without naming the company, so it's worth
checking r/AWSForStartuppz's self-promotion rules before these start going
out regularly.

## How it works

- **Daily** (cron-job.org -> GitHub `repository_dispatch` -> `daily-draft.yml`):
  if a draft is already waiting on a decision, you get a reminder; otherwise
  it researches a fresh angle and sends a new draft to Telegram.
  - Research first checks AWS's official "What's New" RSS feed for a recent,
    not-yet-used announcement to riff on; if that fails or everything recent
    has already been used, it falls back to the evergreen topic pool in
    `config.yaml`.
- **Every few minutes** (cron-job.org -> `poll-approvals.yml`): checks for a
  text reply on Telegram to the pending draft:
  - **`done`** -> sends back the title/body in a copy-paste-ready message.
    Paste the title into Reddit's title field and the body into the text
    box, yourself, on reddit.com. Logged to `state/history.json` so it's
    never regenerated.
  - **`reject`** -> discards the draft and immediately researches + sends a
    new one.
  - **anything else** -> treated as a specific topic you want written about.
    This takes priority over whatever is pending - the current draft (if
    any) is dropped and a new one is generated for exactly that topic, no
    matter where things stood.

State (pending draft, Telegram update offset, draft history) lives as JSON
files in `state/`, committed back to the repo by the Actions bot itself - no
external database. Topics already in `history.json` (posted or rejected)
are never picked again for the researched/evergreen flow, and a custom
topic you type gets a heads-up if you've already posted that exact angle
before (it still generates it - that's an explicit request, not a dedupe
decision).

## Why no auto-posting

Reddit closed self-service API app creation in November 2025 (the
"Responsible Builder Policy") - creating a new app at reddit.com/prefs/apps
now requires manual approval from Reddit, which isn't guaranteed or fast.
Rather than block on that, this bot does everything *except* the final
submit: you stay the one actually clicking "Post" on reddit.com, which also
means there's no bot-automation risk to the account at all. If a Reddit API
app ever gets approved later, `poll_telegram.py`'s `handle_done` is the only
place that would need to change to re-add auto-posting.

## One-time setup

### 1. Telegram bot

1. Message **@BotFather** on Telegram -> `/newbot` -> follow prompts -> copy
   the bot token.
2. Send your new bot any message (e.g. "hi").
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and
   copy the `chat.id` field from the response - that's your
   `TELEGRAM_CHAT_ID`.

### 2. Groq API key

Create one at https://console.groq.com/keys.

### 3. GitHub repo secrets

In the repo -> Settings -> Secrets and variables -> Actions, add:

| Secret | Value |
|---|---|
| `GROQ_API_KEY` | from step 2 |
| `TELEGRAM_BOT_TOKEN` | from step 1 |
| `TELEGRAM_CHAT_ID` | from step 1 |

### 4. GitHub personal access token for cron-job.org

Create a classic PAT with the `repo` scope at
https://github.com/settings/tokens. This token is used **only** inside
cron-job.org's request headers - never paste it into this repo.

### 5. cron-job.org jobs

Create two jobs at https://cron-job.org, both:

- URL: `https://api.github.com/repos/Sehrawat2005/reddit-aws-bot/dispatches`
- Method: `POST`
- Headers:
  - `Authorization: Bearer <your PAT>`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`

| Job | Schedule | Body |
|---|---|---|
| Daily draft | once/day, your chosen fixed time | `{"event_type":"daily-draft"}` |
| Poll approvals | every 5 minutes | `{"event_type":"poll-approvals"}` |

## Testing before relying on cron-job.org

You can trigger either workflow manually from the repo's Actions tab
("Run workflow"), or via `gh workflow run daily-draft.yml` /
`gh workflow run poll-approvals.yml`, to verify everything end-to-end before
wiring up cron-job.org.

## Notes

- Posts are first-person anecdotes, no links/company names/CTAs - see
  `config.yaml` for the exact style rules and fallback topic pool.
- Re-check r/AWSForStartuppz's current rules occasionally (self-promo
  policy, posting frequency limits) before posting - subreddit rules can
  change.
- You can message the bot a topic at any time (e.g. "write about S3
  Intelligent-Tiering surprises") - it doesn't wait for the daily cron or
  an existing pending draft; it just generates and sends that one next.
- Only messages from the chat matching `TELEGRAM_CHAT_ID` are acted on.
