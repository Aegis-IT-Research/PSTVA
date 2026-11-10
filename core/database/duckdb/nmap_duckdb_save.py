from duckdb import DuckDBPyConnection


def save_data_to_duckdb(data: list, connection: DuckDBPyConnection):
    insert_data = [
        (
            item["ip"],
            item["state"],
        )
        for item in data
    ]
    connection.executemany("INSERT INTO tool_results VALUES (?, ?)", insert_data)
