from langchain.tools import tool
from moth.tools.utils import get_youtube_service

@tool
def search_videos(query: str, max_results: int = 5) -> str:
    """Searches for videos on YouTube matching the query."""
    service = get_youtube_service()
    
    request = service.search().list(
        part="snippet",
        maxResults=max_results,
        q=query,
        type="video"
    )
    response = request.execute()
    
    output = []
    for item in response.get('items', []):
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        output.append(f"Title: {title}\nChannel: {channel}\nLink: https://www.youtube.com/watch?v={video_id}\n---")
        
    return "\n".join(output)
