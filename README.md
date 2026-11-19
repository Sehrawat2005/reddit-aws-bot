# reddit-aws-bot

Semi-automated Reddit poster for r/AWSForStartuppz. Every day it drafts an
AWS/cloud informational post (via Groq), sends it to you on Telegram for
Approve/Reject, and only posts to Reddit once you approve. Runs entirely on
GitHub Actions, triggered by cron-job.org pings, so it works even when your
laptop is off.

## How it works

- **Daily** (cron-job.org -> GitHub `repository_dispatch` -> `daily-draft.yml`):
  if a draft is already waiting on a decision, you get a reminder; otherwise
  a new draft is generated and sent to Telegram.
- **Every few minutes** (cron-job.org -> `poll-approvals.yml`): checks if you
  tapped Approve or Reject on Telegram.
  - Approve -> posts to r/AWSForStartuppz, confirms back on Telegram.
  - Reject -> discards the draft and immediately generates + sends a new one.

State (`state/*.json`) is committed back to the repo by the workflow itself,
so there's no external database.

## One-time setup

### 1. Reddit app

1. Go to https://www.reddit.com/prefs/apps while logged into the account
   that will post.
2. Create app -> type **script**. Any name/redirect URI works (e.g.
   `http://localhost:8080`).
3. Note the client id (under the app name) and client secret.

### 2. Telegram bot

1. Message **@BotFather** on Telegram -> `/newbot` -> follow prompts -> copy
   the bot token.
2. Send your new bot any message (e.g. "hi").
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and
   copy the `chat.id` field from the response - that's your
   `TELEGRAM_CHAT_ID`.

### 3. Groq API key

Create one at https://console.groq.com/keys.

### 4. GitHub repo secrets

In the repo -> Settings -> Secrets and variables -> Actions, add:

| Secret | Value |
|---|---|
| `GROQ_API_KEY` | from step 3 |
| `TELEGRAM_BOT_TOKEN` | from step 2 |
| `TELEGRAM_CHAT_ID` | from step 2 |
| `REDDIT_CLIENT_ID` | from step 1 |
| `REDDIT_CLIENT_SECRET` | from step 1 |
| `REDDIT_USERNAME` | the Reddit account's username |
| `REDDIT_PASSWORD` | the Reddit account's password |
| `REDDIT_USER_AGENT` | any descriptive string, e.g. `reddit-aws-bot/1.0 by u/<your-username>` |

### 5. GitHub personal access token for cron-job.org

Create a classic PAT with the `repo` scope at
https://github.com/settings/tokens. This token is used **only** inside
cron-job.org's request headers - never paste it into this repo.

### 6. cron-job.org jobs

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

- Posts are self-text only, first-person anecdotes, no links/company
  names/CTAs - see `config.yaml` for the exact style rules and topic pool.
- A defensive check (`min_hours_between_posts` in `config.yaml`) refuses to
  double-post to the subreddit within a configurable window.
- Re-check r/AWSForStartuppz's current rules occasionally (self-promo
  policy, posting frequency limits) - subreddit rules can change.
