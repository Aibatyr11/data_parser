import logging
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_config: dict = None):
        if db_config is None:
            self.db_config = {
                "host": "127.0.0.1",
                "port": "5432",
                "database": "reports_db",
                "user": "postgres",
                "password": "AiDataParser2026!"
            }
        else:
            self.db_config = db_config

        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
            logging.info("Database connection established.")
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            raise

    def save_statistics(self, flat_data: List[Dict[str, Any]]):
        """Пакетное сохранение с поддержкой parent_id для иерархии КАТО."""
        if not flat_data:
            logging.info("No data to save.")
            return []

        logging.info(f"Starting database load for {len(flat_data)} records...")
        records_to_insert = []

        for record in flat_data:
            records_to_insert.append((
                record.get("kato_id"),
                record.get("region_name"),
                record.get("period_code"),
                record.get("period_name"),
                record.get("value"),
                record.get("parent_id")  # По ТЗ 2.2
            ))

        # ВАЖНО: Мы добавили parent_id в INSERT
        insert_query = """
            INSERT INTO statistics_table
            (kato_id, region_name, period_code, period_name, value, parent_id)
            VALUES %s
        """

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, insert_query, records_to_insert)
            self.conn.commit()
            logging.info(f"Successfully saved records: {len(records_to_insert)}")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Transaction failed, rolling back. Error: {e}")
            raise

        return flat_data

    def save_company_info(self, company_data: dict):
        """Сохранение данных о компании из stat.gov.kz"""
        if not company_data:
            return

        # Запрос с обновлением (ON CONFLICT), если такой БИН уже есть
        insert_query = """
            INSERT INTO companies_table (bin, name, oked, head_name, address)
            VALUES (%(bin)s, %(name)s, %(oked)s, %(head_name)s, %(address)s)
            ON CONFLICT (bin) DO UPDATE SET 
                name = EXCLUDED.name,
                oked = EXCLUDED.oked,
                head_name = EXCLUDED.head_name,
                address = EXCLUDED.address;
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(insert_query, company_data)
            self.conn.commit()
            logging.info(f"Сохранена компания: {company_data.get('bin')} - {company_data.get('name')}")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Ошибка сохранения компании {company_data.get('bin')}: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")
