import unittest
from pathlib import Path

from core.database.duckdb.nmap_duckdb_save import save_data_to_duckdb


DB = "test.db"


class TestDuckDB(unittest.TestCase):
    def setUp(self):
        import duckdb
        from modules.tools.nmap.utils.nmap_parser import parse_nmap_output
        self.connection = duckdb.connect(DB)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_results (
                ip VARCHAR,
                state VARCHAR 
            )
        """
        )
        real_text_output = (
            Path(__file__).resolve().parents[1] / "fixtures" / "real_nmap_data.xml"
        ).read_text()
        self.parsed_data = parse_nmap_output(real_text_output)
        return super().setUp()

    def tearDown(self):
        self.connection.close()
        Path(DB).unlink(missing_ok=True)
        return super().tearDown()

    def test_duckdb(self):
        save_data_to_duckdb(self.parsed_data, self.connection)

        result = self.connection.execute("SELECT ip FROM tool_results").fetchone()
        self.assertEqual(result[0], "192.168.5.241")
