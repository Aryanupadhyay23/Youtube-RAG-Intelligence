from langchain_core.documents import Document
from utils.constants import CHUNK_SIZE

def create_timestamp_aware_chunks(video_id: str, transcript_segments: list) -> list[Document]:
    """
    Groups transcript segments into chunks, preserving start and end timestamps.
    Returns a list of LangChain Document objects.
    """
    if not transcript_segments:
        return []

    documents = []
    current_text, current_start = [], None
    char_count = 0
    approx_limit = CHUNK_SIZE * 4 # rough estimate for characters per chunk
    
    for seg in transcript_segments:
        if current_start is None:
            current_start = seg["start"]
            
        current_text.append(seg["text"])
        char_count += len(seg["text"]) + 1
        
        if char_count > approx_limit:
            documents.append(Document(
                page_content=" ".join(current_text),
                metadata={
                    "video_id": video_id, 
                    "start_time": current_start, 
                    "end_time": seg["start"] + seg["duration"]
                }
            ))
            # Start next chunk with overlap
            current_text = [seg["text"]]
            current_start = seg["start"]
            char_count = len(seg["text"]) + 1
            
    if current_text:
        documents.append(Document(
            page_content=" ".join(current_text),
            metadata={
                "video_id": video_id, 
                "start_time": current_start, 
                "end_time": transcript_segments[-1]["start"] + transcript_segments[-1]["duration"]
            }
        ))
        
    return documents
