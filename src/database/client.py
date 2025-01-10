from typing import Optional
from supabase import create_client, Client
import os


class SupabaseClient:
    """Singleton client for Supabase database connection"""
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client instance (Singleton pattern)"""
        if cls._instance is None:

            cls._instance = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
        return cls._instance
