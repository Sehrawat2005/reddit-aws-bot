"""Entry point for the poll-approvals.yml workflow.

Polls Telegram for a button press on the currently pending draft and acts on
it: approve -> submit to Reddit, reject -> discard and generate a new draft.
"""
from datetime import datetime, timezone

import praw

import common
from generate_draft import generate_and_send


def build_reddit():
    import os

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )


def recently_posted(reddit, subreddit, min_hours):
    """Defensive duplicate guard: skip if we already posted to this
    subreddit more recently than min_hours ago."""
    me = reddit.user.me()
    now = datetime.now(timezone.utc).timestamp()
    for submission in me.submissions.new(limit=10):
        if submission.subreddit.display_name.lower() == subreddit.lower():
            age_hours = (now - submission.created_utc) / 3600
            if age_hours < min_hours:
                return True, age_hours
    return False, None


def handle_approve(draft, config):
    reddit = build_reddit()

    blocked, age_hours = recently_posted(
        reddit, draft["subreddit"], config["min_hours_between_posts"]
    )
    if blocked:
        common.telegram_send_text(
            f"Not posting yet: already posted to r/{draft['subreddit']} "
            f"{age_hours:.1f}h ago (minimum gap is "
            f"{config['min_hours_between_posts']}h). Draft is still pending; "
            f"try Approve again later."
        )
        return

    try:
        subreddit = reddit.subreddit(draft["subreddit"])
        submission = subreddit.submit(title=draft["title"], selftext=draft["body"])
    except Exception as exc:  # noqa: BLE001 - surface any Reddit error to the user
        common.telegram_send_text(
            f"Failed to post draft {draft['draft_id']} to Reddit: {exc}\n"
            f"Draft is still pending - fix the issue and tap Approve again."
        )
        return

    history = common.load_history()
    history["posted"].append(
        {
            "draft_id": draft["draft_id"],
            "topic": draft["topic"],
            "title": draft["title"],
            "url": f"https://reddit.com{submission.permalink}",
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    common.save_history(history)
    common.clear_pending_draft()
    common.telegram_send_text(f"Posted! https://reddit.com{submission.permalink}")


def handle_reject(draft):
    history = common.load_history()
    history["rejected"].append(
        {
            "draft_id": draft["draft_id"],
            "topic": draft["topic"],
            "title": draft["title"],
            "rejected_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    common.save_history(history)
    common.clear_pending_draft()
    common.telegram_send_text("Rejected. Generating a new draft...")
    generate_and_send()


def main():
    config = common.load_config()
    offset = common.load_telegram_offset()
    updates = common.telegram_get_updates(offset)

    if not updates:
        print("No new Telegram updates.")
        return

    new_offset = offset
    for update in updates:
        new_offset = max(new_offset, update["update_id"] + 1)

        callback = update.get("callback_query")
        if not callback:
            continue

        data = callback.get("data", "")
        if ":" not in data:
            continue
        action, draft_id = data.split(":", 1)

        pending = common.load_pending_draft()
        if pending is None or pending["draft_id"] != draft_id:
            common.telegram_answer_callback(callback["id"], "This draft is no longer pending.")
            continue

        if action == "approve":
            common.telegram_answer_callback(callback["id"], "Approved, posting...")
            handle_approve(pending, config)
        elif action == "reject":
            common.telegram_answer_callback(callback["id"], "Rejected.")
            handle_reject(pending)

    common.save_telegram_offset(new_offset)


if __name__ == "__main__":
    main()
