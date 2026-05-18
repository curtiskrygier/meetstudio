EMOJI_TRIGGERS = {
    "impressive": "👏",
    "impress":    "👏",
    "love":       "🫶",
    "idea":       "💡",
    "ideas":      "💡",
    "brilliant":  "💡",
    "amazing":    "🔥",
    "incredible": "🔥",
    "congrats":   "🎉",
    "congratulations": "🎉",
}

def detect_emojis(text: str) -> list[str]:
    seen, result = set(), []
    for word in text.lower().split():
        emoji = EMOJI_TRIGGERS.get(word.strip(".,!?;:'\""))
        if emoji and emoji not in seen:
            seen.add(emoji)
            result.append(emoji)
    return result
