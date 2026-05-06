import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)

def check_table_data():
    print("🔍 АУДИТ ДАННЫХ В ТАБЛИЦАХ...\n")
    
    with engine.connect() as conn:
        # 1. Получаем список всех таблиц
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in conn.execute(query).fetchall()]
        
        if not tables:
            print("⚠️ В базе нет таблиц!")
            return

        print(f"Всего найдено таблиц: {len(tables)}\n")
        
        # 2. Заглядываем внутрь каждой таблицы
        for tbl in tables:
            print("=" * 70)
            print(f"🗂 ТАБЛИЦА: {tbl}")
            
            # Считаем количество строк
            count_query = text(f'SELECT COUNT(*) FROM "{tbl}"')
            row_count = conn.execute(count_query).scalar()
            print(f"📊 Строк в базе: {row_count}")
            
            # Если есть данные, показываем кусочек
            if row_count > 0:
                print("👀 Превью (первые 3 строки):")
                # Используем Pandas просто для красивого табличного вывода в консоль
                df_preview = pd.read_sql(f'SELECT * FROM "{tbl}" LIMIT 3', conn)
                print(df_preview.to_string(index=False))
            else:
                print("⚠️ Таблица абсолютно пустая!")
            print("\n")

if __name__ == "__main__":
    check_table_data()
