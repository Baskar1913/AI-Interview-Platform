from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from ..core.config import settings
import uuid

class QdrantVectorStore:
    collection="interview_context"
    def __init__(self):
        self.client=QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    def ensure(self, size=1536):
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.create_collection(self.collection, vectors_config=VectorParams(size=size,distance=Distance.COSINE))
    def upsert(self, vector, payload):
        self.client.upsert(self.collection,[PointStruct(id=str(uuid.uuid4()),vector=vector,payload=payload)])
    def search(self, vector, limit=5):
        return self.client.query_points(collection_name=self.collection,query=vector,limit=limit).points
