from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.constants import CHUNK_SIZE, CHUNK_OVERLAP

def create_timestamp_aware_chunks(video_id: str, transcript_segments: list) -> list[Document]:
    """
    Groups transcript segments into chunks, preserving start and end timestamps.
    Returns a list of LangChain Document objects.
    """
    if not transcript_segments:
        return []

    # Let's use a simpler heuristic for now. Group segments until they exceed CHUNK_SIZE.
    # Alternatively, use LangChain's splitter but carefully map back timestamps.
    # Given the requirements: "Use timestamp-aware transcript chunking... Do not blindly split the raw transcript by characters."
    
    documents = []
    current_text = ""
    current_start = None
    current_end = None
    chunk_idx = 0
    
    # We will simply accumulate segments until we hit a word count limit or character limit.
    # Since tokens/characters roughly correlate, we'll use character approximation.
    approx_char_limit = CHUNK_SIZE * 4 # rough estimate for 600 tokens
    
    for seg in transcript_segments:
        text = seg["text"]
        start = seg["start"]
        duration = seg["duration"]
        end = start + duration
        
        if current_start is None:
            current_start = start
            
        if len(current_text) + len(text) > approx_char_limit and current_text:
            # Save chunk
            doc = Document(
                page_content=current_text.strip(),
                metadata={
                    "video_id": video_id,
                    "chunk_id": chunk_idx,
                    "start_time": current_start,
                    "end_time": current_end,
                }
            )
            documents.append(doc)
            chunk_idx += 1
            # Simple overlap: start next chunk with the current segment
            current_text = text + " "
            current_start = start
            current_end = end
        else:
            current_text += text + " "
            current_end = end
            
    # Add final chunk
    if current_text.strip():
        doc = Document(
            page_content=current_text.strip(),
            metadata={
                "video_id": video_id,
                "chunk_id": chunk_idx,
                "start_time": current_start,
                "end_time": current_end,
            }
        )
        documents.append(doc)
        
    return documents
