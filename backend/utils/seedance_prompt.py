"""Build Seedance-friendly video prompts with explicit spoken dialogue."""

from __future__ import annotations

import re
from typing import List, Tuple


def _parse_audio_desc(audio_desc: str) -> Tuple[List[str], List[str]]:
    dialogues: List[str] = []
    ambients: List[str] = []
    if not audio_desc or not audio_desc.strip():
        return dialogues, ambients

    for raw_line in audio_desc.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"\[Sound Effect\]", line, re.IGNORECASE):
            ambients.append(re.sub(r"^\[Sound Effect\]\s*", "", line, flags=re.IGNORECASE))
        elif re.match(r"\[(Dialogue|Speaker|Narration)\]", line, re.IGNORECASE):
            dialogues.append(re.sub(r"^\[(Dialogue|Speaker|Narration)\]\s*", "", line, flags=re.IGNORECASE))
        else:
            dialogues.append(line)
    return dialogues, ambients


def _format_dialogue_line(line: str) -> str:
    line = line.strip()
    if not line:
        return line
    if re.search(r"\bsays\s*:", line, re.IGNORECASE):
        return line

    match = re.match(r'^(.+?):\s*(".*?"|\'.+?\')$', line, flags=re.DOTALL)
    if match:
        speaker, quote = match.group(1).strip(), match.group(2).strip()
        speaker = speaker.replace("O.S.", "off-screen").replace("(O.S.)", "(off-screen)")
        return f'{speaker} says: {quote}'

    match = re.match(r"^(.+?):\s*(.+)$", line, flags=re.DOTALL)
    if match:
        speaker, text = match.group(1).strip(), match.group(2).strip().strip('"')
        speaker = speaker.replace("O.S.", "off-screen").replace("(O.S.)", "(off-screen)")
        return f'{speaker} says: "{text}"'

    return line


def build_seedance_video_prompt(
    motion_desc: str,
    audio_desc: str,
    duration_seconds: int = 5,
) -> str:
    """Merge motion + audio into a prompt Seedance can turn into spoken dialogue."""
    dialogues, ambients = _parse_audio_desc(audio_desc)
    parts = [motion_desc.strip()]

    if dialogues:
        parts.append(
            "\nSpoken dialogue (clear character voice, lip sync when face is visible):"
        )
        if len(dialogues) == 1:
            parts.append(f"- {_format_dialogue_line(dialogues[0])}")
        else:
            segment = max(1, duration_seconds // len(dialogues))
            cursor = 0
            for index, dialogue in enumerate(dialogues):
                start = cursor
                end = duration_seconds if index == len(dialogues) - 1 else min(duration_seconds, cursor + segment)
                parts.append(
                    f"- {start}-{end}s: {_format_dialogue_line(dialogue)}"
                )
                cursor = end

    if ambients:
        parts.append(
            "\nBackground ambience (keep low under dialogue): "
            + "; ".join(ambients)
        )

    if dialogues:
        parts.append(
            "\nAudio requirements: generate audible character speech for every quoted line; "
            "do not output ambience-only or music-only audio."
        )
    elif ambients:
        parts.append("\nAudio requirements: ambient sound only, no music.")

    parts.append(
        "\nMotion requirements: smooth continuous movement, natural ending velocity at the "
        "final frame, avoid abrupt freeze or stutter at the clip end."
    )

    return "\n".join(part for part in parts if part)
