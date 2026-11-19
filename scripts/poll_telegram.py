"""Entry point for the poll-approvals.yml workflow.

Polls Telegram for a text reply and acts on it:
- "done"   -> marks the pending draft as posted, sends back a clean
              copy-paste-ready version (you post it to Reddit yourself).
- "reject" -> discards the pending draft and immediately generates + sends
              a new one.
- anything else -> treated as a specific topic request. Takes priority over
              whatever is pending: any current draft is discarded and a new
              one is generated for exactly that topic.
"""
import os
from datetime import datetime, timezone

import common
from generate_draft import generate_and_send, generate_for_topic


def handle_done(draft):
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


def handle_custom_topic(topic):
    if common.load_pending_draft() is not None:
        common.clear_pending_draft()
        common.telegram_send_text(
            f"Got it - dropping the pending draft and writing about: {topic}"
        )

    history = common.load_history()
    already_posted = [
        h for h in history.get("posted", [])
        if h.get("topic", "").strip().lower() == topic.strip().lower()
    ]
    if already_posted:
        common.telegram_send_text(
            f"Heads up: you already posted about '{topic}' before "
            f"({already_posted[-1].get('approved_at', 'date unknown')}). "
            f"Generating anyway since you asked for it directly."
        )

    generate_for_topic(topic)


def main():
    offset = common.load_telegram_offset()
    updates = common.telegram_get_updates(offset)

    if not updates:
        print("No new Telegram updates.")
        return

    expected_chat_id = os.environ["TELEGRAM_CHAT_ID"]
    new_offset = offset
    for update in updates:
        new_offset = max(new_offset, update["update_id"] + 1)

        message = update.get("message")
        if not message or "text" not in message:
            continue
        if str(message.get("chat", {}).get("id")) != str(expected_chat_id):
            continue

        text = message["text"].strip()
        if not text:
            continue
        lowered = text.lower()

        pending = common.load_pending_draft()

        if lowered == "done":
            if pending is None:
                common.telegram_send_text("No draft is currently pending.")
            else:
                handle_done(pending)
        elif lowered == "reject":
            if pending is None:
                common.telegram_send_text("No draft is currently pending to reject.")
            else:
                handle_reject(pending)
        else:
            handle_custom_topic(text)

    common.save_telegram_offset(new_offset)


if __name__ == "__main__":
    main()
