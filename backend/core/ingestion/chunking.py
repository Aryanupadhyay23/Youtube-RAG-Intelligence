from langchain_core.documents import Document
from backend.utils.constants import CHUNK_SIZE, CHUNK_OVERLAP


def create_timestamp_aware_chunks(video_id: str, transcript_segments: list) -> list[Document]:
    """
    Groups transcript segments into coherent chunks preserving start and end timestamps.
    Respects CHUNK_SIZE and CHUNK_OVERLAP while avoiding trailing single-segment duplicate chunks.
    Returns a list of LangChain Document objects.
    """
    if not transcript_segments:
        return []

    documents = []
    current_segments = []
    current_chars = 0
    target_limit = CHUNK_SIZE * 4  # Target chunk size in characters (~1000 tokens)
    overlap_limit = CHUNK_OVERLAP * 4

    for seg in transcript_segments:
        seg_text = seg.get("text", "").strip()
        if not seg_text:
            continue

        current_segments.append(seg)
        current_chars += len(seg_text) + 1

        if current_chars >= target_limit:
            # Emit completed chunk
            chunk_text = " ".join(s["text"].strip() for s in current_segments)
            documents.append(
                Document(
                    page_content=chunk_text,
                    metadata={
                        "video_id": video_id,
                        "start_time": current_segments[0]["start"],
                        "end_time": current_segments[-1]["start"] + current_segments[-1]["duration"],
                    },
                )
            )

            # Preserve recent segments for overlap
            overlap_segments = []
            overlap_chars = 0
            for prev_seg in reversed(current_segments):
                prev_len = len(prev_seg.get("text", "")) + 1
                if overlap_chars + prev_len > overlap_limit and overlap_segments:
                    break
                overlap_segments.insert(0, prev_seg)
                overlap_chars += prev_len

            current_segments = overlap_segments
            current_chars = overlap_chars

    # Flush remainder if it contains new content beyond the overlap
    if current_segments:
        if not documents or len(current_segments) > 1:
            chunk_text = " ".join(s["text"].strip() for s in current_segments)
            documents.append(
                Document(
                    page_content=chunk_text,
                    metadata={
                        "video_id": video_id,
                        "start_time": current_segments[0]["start"],
                        "end_time": current_segments[-1]["start"] + current_segments[-1]["duration"],
                    },
                )
            )

    return documents
