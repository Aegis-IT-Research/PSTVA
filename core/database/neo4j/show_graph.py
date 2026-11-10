from pprint import pprint

from core.database.neo4j.neo4j_manager import Neo4jManager


def main():
    db = Neo4jManager()
    graph_ = db.dump_graph("b080bfe8-d179-4a17-bf3e-b2e735d85a6f")
    pprint(graph_)


if __name__ == "__main__":
    main()
