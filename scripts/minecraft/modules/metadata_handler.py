import json
from typing import List, Dict, Any, Set, Optional
from .constants import METADATA_FILE
from .logger import logger
from .db import db_connection

class MetadataHandler:
    def __init__(self, use_mongodb: bool = False, collection_name: Optional[str] = None, overwrite: bool = False):
        self.items: List[Dict[str, Any]] = []
        self.existing_ids: Set[str] = set()
        self.use_mongodb = use_mongodb
        self.collection_name = collection_name
        self.overwrite = overwrite
        self.db_collection = None

        if self.use_mongodb and self.collection_name:
            self.setup_mongodb()

        self.load_metadata()

    def setup_mongodb(self):
        try:
            db_connection.connect()
            db = db_connection.get_database()
            if db is not None and self.collection_name:
                self.db_collection = db[self.collection_name]
                # Load existing IDs from MongoDB to prevent duplicates
                mongo_ids = self.db_collection.distinct("id")
                self.existing_ids.update(mongo_ids)
                logger.info(f"Loaded {len(mongo_ids)} existing items from MongoDB collection '{self.collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to setup MongoDB: {e}")
            # Fallback to not using MongoDB if connection fails?
            # Or should we fail hard? The user asked to fail if item exists.
            # Let's assume we should fail hard if MongoDB was requested but failed.
            raise

    def load_metadata(self):
        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    file_items = json.load(f)
                    self.items = file_items
                    self.existing_ids.update({item['id'] for item in file_items})
                logger.info(f"Loaded {len(file_items)} existing items from metadata file.")
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from {METADATA_FILE}. Starting with empty list.")
                self.items = []
        else:
            logger.info("No existing metadata file found. Starting fresh.")

    def item_exists(self, item_id: str) -> bool:
        return item_id in self.existing_ids

    def add_item(self, item_id: str, asset_name: str, name: str, source_jar: str, asset_b64: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None, block_type: Optional[str] = None, rendered_3d: Optional[bool] = None, mod_info: Optional[Dict[str, str]] = None, parent: Optional[str] = None, model: Optional[Dict[str, Any]] = None) -> bool:
        if self.item_exists(item_id) and not self.overwrite:
            logger.warning(f"Duplicate item data found for ID: {item_id}. Source: {source_jar}. Skipping.")
            return False

        new_item: Dict[str, Any] = {
            "id": item_id,
            "asset": asset_name,
            "name": name,
            "source": source_jar,
        }

        # Preserve 'asset' as the image filename string. If a model is provided, add it
        # as a separate 'model' object with path and JSON content.
        if mod_info:
            new_item["mod"] = mod_info

        # Always include the model field; it may be None when no model was found
        if model is None:
            new_item["model"] = None
        else:
            # Ensure the model includes the 'path' key—if not, assume the path is unknown
            if "path" not in model:
                model = {"path": None, **model}
            new_item["model"] = model

        if asset_b64:
            new_item["asset_b64"] = asset_b64
        if width is not None and height is not None:
            new_item["width"] = int(width)
            new_item["height"] = int(height)
        if block_type:
            new_item["block_type"] = block_type
        if parent:
            new_item["parent"] = parent

        if rendered_3d:
            new_item["rendered_3d"] = True

        # Update in-memory list
        if self.item_exists(item_id):
            # Find and replace
            for i, item in enumerate(self.items):
                if item['id'] == item_id:
                    self.items[i] = new_item
                    break
        else:
            self.items.append(new_item)
            self.existing_ids.add(item_id)

        if self.use_mongodb and self.db_collection is not None:
            try:
                if self.overwrite:
                    self.db_collection.update_one(
                        {"id": item_id},
                        {"$set": new_item},
                        upsert=True
                    )
                    logger.info(f"Upserted item {item_id} (source: {source_jar}) to MongoDB.")
                else:
                    self.db_collection.insert_one(new_item.copy())
                    logger.info(f"Added item {item_id} (source: {source_jar}) to MongoDB.")
            except Exception as e:
                logger.error(f"Failed to insert/update item {item_id} into MongoDB: {e}")
                # If DB write fails, do we continue?
                # Probably yes, but log error.

        return True

    def save_metadata(self):
        try:
            # Sort by ID for consistency
            sorted_items = sorted(self.items, key=lambda x: x['id'])
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(sorted_items, f, indent=2)
            logger.info(f"Saved metadata to {METADATA_FILE}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    def close(self):
        """
        Close any external resources (e.g., DB connection) and ensure metadata is saved.
        """
        try:
            # Always attempt to save metadata when closing
            self.save_metadata()
        except Exception:
            # save_metadata logs its own errors
            pass

        if self.use_mongodb:
            try:
                db_connection.close()
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
