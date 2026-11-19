"""Generate a new Reddit draft via Groq - either from a researched trending
angle, or from a topic the user typed on Telegram - and send it for review."""
import json
import os
import uuid
from datetime import datetime, timezone

import requests

import common
from research import pick_angle

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You write short case-study Reddit posts for r/{subreddit}, \
an AWS/cloud startup community, on behalf of an AWS cloud consulting \
partner sharing a brief story about a client engagement. You must output \
ONLY a single JSON object, no other text, no markdown code fences, with \
exactly two keys: "title" and "body".

Style rules you must follow:
{style_rules}

The case study should center on this angle: "{topic}"
{context_block}
Avoid reusing these exact angles already covered recently: {recent}
"""


def recent_topics(config, history):
    n = config.get("history_context_size", 8)
    return ([h.get("topic") for h in history.get("posted", [])] +
            [h.get("topic") for h in history.get("rejected", [])])[-n:]


def call_groq(config, topic, context, recent):
    api_key = os.environ["GROQ_API_KEY"]
    style_rules = "\n".join(f"- {r}" for r in config["style_rules"])
    context_block = (
        f"\nFor background, here's a recent real AWS development related to "
        f"this angle - use it only as plausible inspiration for the kind of "
        f"problem a client might have hit, never summarize it like a press "
        f"release or link to it:\n{context}\n"
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


def _build_send_and_save(config, topic, context, recent):
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


def generate_and_send():
    """Research a trending (or evergreen fallback) angle and send a draft."""
    config = common.load_config()
    history = common.load_history()
    recent = recent_topics(config, history)

    topic, context = pick_angle(config, recent)
    return _build_send_and_save(config, topic, context, recent)


def generate_for_topic(topic):
    """Generate a draft for a topic the user typed on Telegram directly."""
    config = common.load_config()
    history = common.load_history()
    recent = recent_topics(config, history)

    return _build_send_and_save(config, topic, None, recent)


if __name__ == "__main__":
    generate_and_send()
