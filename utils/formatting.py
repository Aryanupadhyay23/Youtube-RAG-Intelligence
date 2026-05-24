def format_time(seconds: float):

    minutes, seconds = divmod(
        int(seconds),
        60,
    )

    hours, minutes = divmod(
        minutes,
        60,
    )

    if hours:

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes}:"
        f"{seconds:02d}"
    )


def format_word_count(count: int):

    return f"{count:,}"


def format_segment_count(count: int):

    return f"{count:,}"


def format_chat_export(chat_history):

    export_lines = []

    for index, turn in enumerate(
        chat_history,
        1,
    ):

        export_lines.append(
            f"Turn {index}\n\n"
            f"You: {turn['user']}\n\n"
            f"AI: {turn['ai']}\n\n"
        )

    return "\n".join(export_lines)