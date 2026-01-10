
import logging
import os
import time
from datetime import datetime
from threading import Thread, Event
from typing import Dict, Any, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass

_LOG = logging.getLogger("mongo_sink")

class MongoSink:
    """
    Handles buffering and async insertion of sensor data into MongoDB.
    Implements the 'Dual-Archiving' strategy mentioned in the paper.
    """
    
    def __init__(self, uri: str = "mongodb://localhost:27017/", db_name: str = "stgen_data"):
        self.uri = uri
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
        self.enabled = False
        
        if not HAS_MONGO:
            _LOG.warning("pymongo not installed. MongoDB storage disabled.")
            return
            
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            # Check connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.collection = self.db["sensor_readings"]
            self.enabled = True
            
            # Safe logging (hide credentials)
            safe_uri = uri.split('@')[-1] if '@' in uri else uri
            _LOG.info(f"Connected to MongoDB: ...{safe_uri} [{db_name}]")
        except Exception as e:
            _LOG.warning(f"Failed to connect to MongoDB: {e}. Storage disabled.")
            self.enabled = False
            
    def insert(self, data: Dict[str, Any]):
        """
        Insert a single record into MongoDB.
        In a production env, this should be buffered/batched.
        """
        if not self.enabled:
            return
            
        try:
            # Add metadata if missing
            if "received_at" not in data:
                data["received_at"] = datetime.utcnow()
                
            self.collection.insert_one(data)
        except Exception as e:
            _LOG.error(f"MongoDB write error: {e}")

    def close(self):
        if self.client:
            self.client.close()

# Global singleton instance
_sink = None

def get_sink():
    global _sink
    if _sink is None:
        # Check environment variable for MongoDB connection string
        # Default to local if not set
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        _sink = MongoSink(uri=uri)
    return _sink
