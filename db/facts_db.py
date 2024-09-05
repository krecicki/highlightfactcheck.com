import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
import json
from datetime import date, datetime
from typing import List, Optional
import os

from tools.logger import logger
from config.api_config import APIConfig


class FactsDB:

    facts_table_name = "facts_checked"
    transformer_model_name = "BAAI/bge-small-en-v1.5"

    def __init__(self, db_uri: str):
        logger.debug(f"Connecting to database at '{db_uri}'")
        self.db = lancedb.connect(db_uri)
        self.model = self._initialize_model()
        self.FactChecked = self._create_fact_checked_model()
        self.table = self.create_or_migrate_table()

    def _initialize_model(self):
        return get_registry().get("sentence-transformers").create(name=self.transformer_model_name, device="cpu")

    def _create_fact_checked_model(self):
        class FactChecked(LanceModel):
            sentence: str = self.model.SourceField()
            explanation: str
            rating: str
            severity: str
            key_points: List[str]
            source: Optional[str] = None
            check_date: Optional[date] = None
            vector: Vector(self.model.ndims()) = self.model.VectorField()
        return FactChecked

    def create_or_migrate_table(self):
        if self.facts_table_name in self.db.table_names():
            old_table = self.db.open_table(self.facts_table_name)
            if set(old_table.schema.names) != set(self.FactChecked.model_fields.keys()):
                logger.debug("Migrating existing table to new schema...")
                self.db.drop_table(self.facts_table_name)
                return self.create_new_table()
            else:
                logger.debug("Using existing table.")
                return old_table
        else:
            logger.debug("Creating new empty table.")
            return self.create_new_table()

    def create_new_table(self):
        return self.db.create_table(self.facts_table_name, schema=self.FactChecked)

    def add_fact_if_not_exists(self, fact):
        logger.debug(f"Searching for existing fact: '{fact['sentence']}'")
        existing_facts = self.table.search(
            fact["sentence"], query_type="vector").limit(1).to_pandas()

        result = existing_facts.iloc[0] if len(existing_facts) > 0 else None

        if result is None:
            self.table.add([fact])
            logger.debug(f"\nAdded new fact: '{fact['sentence']}'")
        elif result is not None:
            similarity = 1 / (1 + fact['_distance'])
            if similarity < APIConfig.SIMILARITY_THRESHOLD:
                self.table.add([fact])
                logger.debug(f"\nAdded new fact: '{fact['sentence']}'")
        else:
            logger.debug(f"\nFact already exists: '{fact['sentence']}'")

    def to_json(self, obj):
        return json.dumps(obj, cls=LanceDBJSONEncoder)

    def search_facts(self, query: str, limit: int = 10):
        results = self.table.search(
            query, query_type="vector").limit(limit).to_pandas()
        return results.to_dict(orient='records')

    def get_all_facts(self):
        return self.table.to_pandas().to_dict(orient='records')


# Custom JSON encoder for LanceDB objects

class LanceDBJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)
