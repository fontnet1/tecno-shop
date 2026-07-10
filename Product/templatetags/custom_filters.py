from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter
def break_after_words(value, words_per_line=30):
    """
    Breaks text into new lines after a specified number of words.

    Features:
      - Handles None / empty input gracefully
      - Preserves HTML tags (does not split them across lines)
      - Retains existing newlines from the original text
      - Leaves overly long words intact (no partial splits)
      - Supports two output modes: ``br`` (default) and ``css``

    Template usage:
      {{ text|break_after_words:25 }}
      {{ text|break_after_words:"25" }}
      {{ text|break_after_words:"25,css" }}
    """
    if value is None:
        return ""

    # Coerce non-string input and strip whitespace
    text = str(value).strip()
    if not text:
        return ""

    # --- Parse arguments ---------------------------------------------------
    parts = str(words_per_line).split(",")
    target = max(1, int(parts[0].strip()))
    mode = parts[1].strip().lower() if len(parts) > 1 else "br"

    # --- Extract and temporarily replace HTML tags -------------------------
    # This prevents HTML tags from being counted or split as "words".
    placeholder_map = {}
    html_pattern = re.compile(r"<[^>]+>")

    def _placeholder(match):
        key = f"\x00HTML{len(placeholder_map)}\x00"
        placeholder_map[key] = match.group(0)
        return key

    sanitized = html_pattern.sub(_placeholder, text)

    # --- Split on existing newlines first (preserve paragraph breaks) ------
    raw_lines = sanitized.split("\n")
    processed = []

    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            processed.append("")
            continue

        words = line.split()
        chunk = []
        word_count = 0

        for word in words:
            # Restore any HTML placeholders back to their original tags
            restored = word
            for key, html in placeholder_map.items():
                restored = restored.replace(key, html)

            chunk.append(restored)
            word_count += 1
            if word_count >= target:
                processed.append(" ".join(chunk))
                chunk = []
                word_count = 0

        if chunk:
            processed.append(" ".join(chunk))

    # --- Render output based on the chosen mode ----------------------------
    if mode == "css":
        inner = "<br>\n".join(processed)
        return mark_safe(
            f'<div style="word-wrap:break-word;overflow-wrap:break-word;'
            f'line-height:1.8;text-align:justify;">{inner}</div>'
        )

    # Default mode: plain <br> line breaks
    return mark_safe("<br>\n".join(processed))