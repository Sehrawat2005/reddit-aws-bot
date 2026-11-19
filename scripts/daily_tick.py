"""Entry point for the daily-draft.yml workflow.

If a draft is already pending a decision, just re-send it as a reminder.
Otherwise generate a brand new draft and send it for approval.
"""
import common
from generate_draft import generate_and_send


def main():
    pending = common.load_pending_draft()
    if pending is not None:
        common.telegram_send_draft(pending)
        print(f"Pending draft {pending['draft_id']} still awaiting a decision; sent reminder.")
        return

    draft = generate_and_send()
    print(f"Generated new draft {draft['draft_id']} and sent for approval.")


if __name__ == "__main__":
    main()
