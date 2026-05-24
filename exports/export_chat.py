from utils.formatting import (
    format_chat_export,
)


def export_chat_as_text(
    chat_history,
):

    return format_chat_export(
        chat_history
    )


def export_chat_as_markdown(
    chat_history,
):

    markdown_lines = []

    for index, turn in enumerate(
        chat_history,
        1,
    ):

        markdown_lines.append(
            f"# Turn {index}\n\n"
            f"## User\n"
            f"{turn['user']}\n\n"
            f"## Assistant\n"
            f"{turn['ai']}\n"
        )

    return "\n\n".join(
        markdown_lines
    )