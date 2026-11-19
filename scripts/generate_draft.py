"""Research a trending angle and generate a new Reddit draft via Groq, then
send it for Telegram approval."""
import json
import os
import uuid
from datetime import datetime, timezone

import requests

import common
from research import pick_angle

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You write Reddit posts for r/{subreddit}, an AWS/cloud \
startup community. You must output ONLY a single JSON object, no other text, \
no markdown code fences, with exactly two keys: "title" and "body".

Style rules you must follow:
{style_rules}

The post should center on this angle: "{topic}"
{context_block}
Avoid reusing these exact angles already covered recently: {recent}
"""


def call_groq(config, topic, context, recent):
    api_key = os.environ["GROQ_API_KEY"]
    style_rules = "\n".join(f"- {r}" for r in config["style_rules"])
    context_block = (
        f"\nFor background, here's a recent real AWS announcement related to "
        f"this angle - use it only as inspiration for a first-person story, "
        f"never summarize it like a press release or link to it:\n{context}\n"
        if context
        else ""
    )
    system_prompt = SYSTEM_PROMPT.format(
        subreddit=config["subreddit"],
        style_rules=style_rules,
        topic=topic,
        context_block=context_block,
        recent=", ".join(recent) if recent else "(none yet)",
    )

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": config["groq_model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Write the post now."},
            ],
            "temperature": 0.9,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return parsed["title"].strip(), parsed["body"].strip()


def generate_and_send():
    config = common.load_config()
    history = common.load_history()

    n = config.get("history_context_size", 8)
    recent = ([h.get("topic") for h in history.get("posted", [])] +
              [h.get("topic") for h in history.get("rejected", [])])[-n:]

    topic, context = pick_angle(config, recent)
    title, body = call_groq(config, topic, context, recent)

    draft = {
        "draft_id": uuid.uuid4().hex[:12],
        "subreddit": config["subreddit"],
        "topic": topic,
        "title": title,
        "body": body,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    common.save_pending_draft(draft)
    common.telegram_send_draft(draft)
    return draft


if __name__ == "__main__":
    generate_and_send()
