import unittest
from pathlib import Path
from importer import import_customers

class ImportTests(unittest.TestCase):
    def test_loads_customer_fields(self):
        rows = import_customers(Path(__file__).resolve().parents[1] / "customers.csv")
        self.assertEqual(rows[0]["name"], "Nora Chen")
        self.assertEqual(rows[0]["postcode"], "10001")

if __name__ == "__main__":
    unittest.main()
