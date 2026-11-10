from pathlib import Path
import unittest
import duckdb

DB = "test.db"


class TestDuckDB(unittest.TestCase):
    def setUp(self):
        return super().setUp()

    def tearDown(self):
        Path(DB).unlink(missing_ok=True)
        return super().tearDown()

    def test_duckdb(self):
        # Arrange
        connection = duckdb.connect(DB)
        a = {"this": "that", "key2": "value2", "key3": "value3"}

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS example (
                key VARCHAR,
                value VARCHAR
            )
        """
        )

        # Act
        data = list(a.items())
        connection.executemany("INSERT INTO example VALUES (?, ?)", data)

        # Assert
        result = connection.execute("SELECT COUNT(*) FROM example").fetchone()
        self.assertEqual(result[0], len(data))

        connection.close()
