"""Entry point for the poll-approvals.yml workflow.

Polls Telegram for a button press on the currently pending draft:
- Approve -> sends back a clean copy-paste-ready version of the post and
  logs it as approved (you post it to Reddit yourself, manually).
- Reject -> discards the draft and immediately generates + sends a new one.
"""
from datetime import datetime, timezone

import common
from generate_draft import generate_and_send


def handle_approve(draft):
    text = (
        f"Approved! Copy these into Reddit (r/{draft['subreddit']}) yourself:\n\n"
        f"TITLE (paste into Reddit's title field):\n{draft['title']}\n\n"
        f"BODY (paste into the post text box):\n{draft['body']}"
    )
    common.telegram_send_text(text)

    history = common.load_history()
    history["posted"].append(
        {
            "draft_id": draft["draft_id"],
            "topic": draft["topic"],
            "title": draft["title"],
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    common.save_history(history)
    common.clear_pending_draft()


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
            common.telegram_answer_callback(callback["id"], "Approved!")
            handle_approve(pending)
        elif action == "reject":
            common.telegram_answer_callback(callback["id"], "Rejected.")
            handle_reject(pending)

    common.save_telegram_offset(new_offset)


if __name__ == "__main__":
    main()
