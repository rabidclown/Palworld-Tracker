import sqlalchemy

TABLE_NAME = "pal_breeding"  # <-- Update if your table name differs


class DB:


    def __init__(self, db_url):
        self.engine = sqlalchemy.create_engine(db_url)


    def fetch_all_pals(self):
        """Fetch all rows from the breeding table."""
        query = sqlalchemy.text("""
            SELECT id, pal_name, gender, parent_1, parent_2, complete
            FROM palworldbreeding
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [dict(row._mapping) for row in result]


    def upsert_pal(self, pal_id, pal_name, gender: str, parent_1: str | None = None, parent_2: str | None = None, complete: bool = False):
        """Insert or update a Pal record in the breeding table."""
        query = sqlalchemy.text("""
            INSERT INTO palworldbreeding (id, pal_name, gender, parent_1, parent_2, complete)
            VALUES (:id, :pal_name, :gender, :parent_1, :parent_2, :complete)
            ON CONFLICT (id) DO UPDATE SET
                pal_name = EXCLUDED.pal_name,
                gender = EXCLUDED.gender,
                parent_1 = EXCLUDED.parent_1,
                parent_2 = EXCLUDED.parent_2,
                complete = EXCLUDED.complete
        """)
        with self.engine.begin() as conn:
            conn.execute(
                query,
                {
                    "id": pal_id,
                    "pal_name": pal_name,
                    "gender": gender,
                    "parent_1": parent_1,
                    "parent_2": parent_2,
                    "complete": complete,
                },
            )
