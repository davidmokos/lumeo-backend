from datetime import datetime, UTC
from typing import TypeVar, Optional, List, Generic, Dict, Any
from pydantic import BaseModel

from src.database.client import SupabaseClient


T = TypeVar('T', bound=BaseModel)


class Repository(Generic[T]):
    """Base repository with common database operations"""
    
    def __init__(self, table_name: str, model: type[T]):
        self.client = SupabaseClient.get_client()
        self.table_name = table_name
        self.model = model

    def _serialize_datetime(self, obj: Any) -> Any:
        """Convert datetime objects to ISO format strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for database operations by serializing special types"""
        return {k: self._serialize_datetime(v) for k, v in data.items()}

    def get(self, id: str) -> Optional[T]:
        """Get a single record by ID"""
        response = self.client.table(self.table_name).select("*").eq("id", id).execute()
        return self.model.model_validate(response.data[0]) if response.data else None

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List records with optional filters"""
        query = self.client.table(self.table_name).select("*")
        if filters:
            filters = self._prepare_data(filters)
            for field, value in filters.items():
                query = query.eq(field, value)
        response = query.execute()
        return [self.model.model_validate(item) for item in response.data]

    def create(self, data: T) -> T:
        """Create a new record"""
        create_data = data.model_dump(exclude={'id'}, exclude_none=True)
        create_data['created_at'] = datetime.now(UTC)
        create_data = self._prepare_data(create_data)
        
        response = self.client.table(self.table_name).insert(create_data).execute()
        return self.model.model_validate(response.data[0])

    def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update a record"""
        data['updated_at'] = datetime.now(UTC)
        data = self._prepare_data(data)
        response = self.client.table(self.table_name).update(data).eq("id", id).execute()
        return self.model.model_validate(response.data[0]) if response.data else None

    def delete(self, id: str) -> bool:
        """Delete a record"""
        response = self.client.table(self.table_name).delete().eq("id", id).execute()
        return bool(response.data) 