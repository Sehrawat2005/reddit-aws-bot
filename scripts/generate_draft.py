"""Generate a new Reddit draft post via the Groq API and send it for approval."""
import json
import os
import random
import uuid
from datetime import datetime, timezone

import requests

import common

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You write Reddit posts for r/{subreddit}, an AWS/cloud \
startup community. You must output ONLY a single JSON object, no other text, \
no markdown code fences, with exactly two keys: "title" and "body".

Style rules you must follow:
{style_rules}

The post should center on this specific angle/topic: "{topic}"

Avoid reusing these exact angles already covered recently: {recent}
"""


def pick_topic(config, history):
    recent_posted = [h.get("topic") for h in history.get("posted", [])]
    recent_rejected = [h.get("topic") for h in history.get("rejected", [])]
    n = config.get("history_context_size", 8)
    recent = (recent_posted + recent_rejected)[-n:]

    available = [t for t in config["topics"] if t not in recent]
    if not available:
        available = config["topics"]
    return random.choice(available), recent


def call_groq(config, topic, recent):
    api_key = os.environ["GROQ_API_KEY"]
    style_rules = "\n".join(f"- {r}" for r in config["style_rules"])
    system_prompt = SYSTEM_PROMPT.format(
        subreddit=config["subreddit"],
        style_rules=style_rules,
        topic=topic,
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

    topic, recent = pick_topic(config, history)
    title, body = call_groq(config, topic, recent)

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
