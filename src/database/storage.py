from typing import BinaryIO
from pathlib import Path
from enum import Enum
import httpx
import tempfile

from src.database.client import SupabaseClient


class StorageBucket(str, Enum):
    """Enum for Supabase storage buckets"""
    LECTURES = "lectures"
    SCENES = "scenes"

class StorageClient:
    """Client for managing file storage in Supabase"""
    
    def __init__(self):
        self.client = SupabaseClient.get_client().storage
        
    async def upload_file(
        self,
        bucket: StorageBucket,
        file_path: Path,
        destination_path: str
    ) -> str:
        """Upload a file to storage and return its URL"""
        with open(file_path, 'rb') as f:
            response = self.client.from_(bucket.value).upload(
                path=destination_path,
                file=f,
                file_options={"content-type": "auto"}
            )
            
        return self.client.from_(bucket.value).get_public_url(destination_path)
        
    async def upload_from_url(
        self,
        bucket: StorageBucket,
        source_url: str,
        destination_path: str
    ) -> str:
        """Download a file from URL and upload it to storage"""
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url)
            response.raise_for_status()
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(response.content)
                temp_file.flush()
                
                # Upload from temporary file
                return await self.upload_file(
                    bucket=bucket,
                    file_path=Path(temp_file.name),
                    destination_path=destination_path
                )
    
    async def delete_file(self, bucket: StorageBucket, file_path: str) -> bool:
        """Delete a file from storage
        
        Args:
            bucket: Storage bucket to use
            file_path: Path to the file in the bucket
            
        Returns:
            True if deletion was successful
        """
        try:
            self.client.from_(bucket.value).remove([file_path])
            return True
        except Exception:
            return False

# Example usage in main:
if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    
    async def main():
        # Get storage client instance 
        storage = StorageClient()
        
        # Upload an AI-generated song
        song_url = await storage.upload_file(
            bucket=StorageBucket.AI_SONGS,
            file_path=Path("tests/blank-space.mp3"),
            destination_path="blank-space.mp3"
        )
        
        print(f"Uploaded song URL: {song_url}")

    asyncio.run(main())