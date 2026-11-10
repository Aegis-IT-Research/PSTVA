import json

from core.database.neo4j.neo4j_manager import Neo4jManager


def export_data(output_path: str = "export.json"):
    db = Neo4jManager()

    # Get all hosts
    hosts = db.get_all_data()

    db.close()

    # Note: output_path is kept for backwards compatibility; caller can decide whether to write.
    return hosts
