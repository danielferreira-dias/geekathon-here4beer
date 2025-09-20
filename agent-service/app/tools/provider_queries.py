import sqlite3
import os
from typing import List, Dict, Optional, Tuple

class ProviderDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'providers.db')
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_providers(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers")
            return [dict(row) for row in cursor.fetchall()]

    def get_provider_by_id(self, provider_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_providers_by_location(self, location: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers WHERE location LIKE ?", (f"%{location}%",))
            return [dict(row) for row in cursor.fetchall()]

    def get_providers_by_item(self, item: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers WHERE item LIKE ?", (f"%{item}%",))
            return [dict(row) for row in cursor.fetchall()]

    def get_providers_by_price_range(self, min_price: float, max_price: float) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM providers WHERE price BETWEEN ? AND ? ORDER BY price",
                (min_price, max_price)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_providers_in_stock(self, min_stock: int = 1) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers WHERE stock >= ? ORDER BY stock DESC", (min_stock,))
            return [dict(row) for row in cursor.fetchall()]

    def search_providers(self, search_term: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM providers
                WHERE provider_name LIKE ?
                OR item LIKE ?
                OR location LIKE ?
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            return [dict(row) for row in cursor.fetchall()]

    def get_cheapest_providers(self, limit: int = 5) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers ORDER BY price ASC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_providers_by_name(self, provider_name: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers WHERE provider_name LIKE ?", (f"%{provider_name}%",))
            return [dict(row) for row in cursor.fetchall()]

    def get_stock_summary(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_providers,
                    SUM(stock) as total_stock,
                    AVG(stock) as avg_stock,
                    MIN(stock) as min_stock,
                    MAX(stock) as max_stock
                FROM providers
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}


def get_provider_db() -> ProviderDatabase:
    return ProviderDatabase()


if __name__ == "__main__":
    db = get_provider_db()

    print("All providers:")
    providers = db.get_all_providers()
    for provider in providers[:3]:
        print(f"- {provider['provider_name']}: {provider['item']} (${provider['price']}) - {provider['location']}")

    print(f"\nTotal providers: {len(providers)}")

    print("\nProviders in California:")
    ca_providers = db.get_providers_by_location("California")
    for provider in ca_providers:
        print(f"- {provider['provider_name']}: {provider['item']}")

    print("\nCheapest 3 items:")
    cheap_items = db.get_cheapest_providers(3)
    for item in cheap_items:
        print(f"- {item['item']}: ${item['price']} from {item['provider_name']}")