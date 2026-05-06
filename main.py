import os
import re
import pandas as pd
import hashlib
import pdfplumber
from docx import Document
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL, pool_pre_ping=True, isolation_level="AUTOCOMMIT")
DATA_FOLDER = "files_to_parse"

def generate_first_last_name(base_name, logical_name):
    """
    Берет первое и последнее слово из имени файла + короткий хэш + имя таблицы (страницы).
    """
    short_hash = hashlib.md5(base_name.encode('utf-8')).hexdigest()[:4]
    clean_base = re.sub(r'^[a-z0-9]{10,}_?', '', base_name.lower())
    if not clean_base:
        clean_base = base_name.lower()

    words_base = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]+', clean_base)
    words_logical = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]+', str(logical_name).lower())

    if len(words_base) > 1:
        base_part = f"{words_base[0]}_{words_base[-1]}_{short_hash}"
    elif len(words_base) == 1:
        base_part = f"{words_base[0]}_{short_hash}"
    else:
        base_part = f"data_{short_hash}"

    logical_part = "_".join(words_logical)[:15].strip('_')

    if logical_part and logical_part not in base_part:
        full_name = f"{base_part}_{logical_part}"
    else:
        full_name = base_part

    if full_name and full_name[0].isdigit():
        full_name = "t_" + full_name

    encoded = full_name.encode('utf-8')
    if len(encoded) > 63:
        full_name = encoded[:63].decode('utf-8', 'ignore').rstrip('_')

    return full_name

def process_sheet_to_table(df, table_name, logical_name, original_file_name):
    try:
        df = df.fillna("")
        df = df.astype(str)

        for col in df.columns:
            # Убираем системный мусор и переносы строк, которые часто бывают в PDF/Word
            df[col] = df[col].str.replace(r'\n', ' ', regex=True)
            df[col] = df[col].str.replace(r'^(nan|none|<na>|null)$', '', regex=True, flags=re.IGNORECASE)
            df[col] = df[col].str.replace(r'(#REF!|#VALUE!|#ERROR!|#N/A)', '', regex=True, flags=re.IGNORECASE)
            df[col] = df[col].str.replace(r'\.0$', '', regex=True)
            df[col] = df[col].str.strip()

        df = df[~df.replace("", pd.NA).isna().all(axis=1)]

        if df.empty:
            return False

        new_columns = [f"col_{i+1}" for i in range(len(df.columns))]
        df.columns = new_columns

        with engine.connect() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
            df.to_sql(table_name, conn, if_exists='replace', index=False)

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS "_справочник_файлов" (
                    имя_таблицы TEXT,
                    оригинальный_файл TEXT,
                    имя_листа TEXT
                )
            '''))
            conn.execute(text(f"DELETE FROM \"_справочник_файлов\" WHERE имя_таблицы = '{table_name}'"))
            query = text('INSERT INTO "_справочник_файлов" (имя_таблицы, оригинальный_файл, имя_листа) VALUES (:tbl, :file, :sheet)')
            conn.execute(query, {"tbl": table_name, "file": original_file_name, "sheet": logical_name})

        return True

    except Exception as e:
        print(f"❌ Ошибка при сохранении таблицы '{logical_name}': {e}")
        return False

def process_pdf_to_tables(file_path, base_name, original_file_name):
    saved_tables = 0
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Ищем таблицы на странице
                tables = page.extract_tables()
                for j, table in enumerate(tables):
                    if not table:
                        continue

                    df = pd.DataFrame(table)
                    logical_name = f"Стр_{i+1}_Табл_{j+1}"
                    table_name = generate_first_last_name(base_name, logical_name)

                    if process_sheet_to_table(df, table_name, logical_name, original_file_name):
                        saved_tables += 1
                        print(f"    ✔️ {logical_name} -> '{table_name}'")
    except Exception as e:
        print(f"❌ Ошибка чтения PDF {base_name}: {e}")
    return saved_tables

def process_docx_to_tables(file_path, base_name, original_file_name):
    saved_tables = 0
    try:
        doc = Document(file_path)
        for i, table in enumerate(doc.tables):
            data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                data.append(row_data)

            if not data:
                continue

            df = pd.DataFrame(data)
            logical_name = f"Word_Табл_{i+1}"
            table_name = generate_first_last_name(base_name, logical_name)

            if process_sheet_to_table(df, table_name, logical_name, original_file_name):
                saved_tables += 1
                print(f"    ✔️ {logical_name} -> '{table_name}'")
    except Exception as e:
        print(f"❌ Ошибка чтения DOCX {base_name}: {e}")
    return saved_tables

def main():
    print("🚀 СТАРТ: ПАРСИНГ ТАБЛИЦ ИЗ PDF И WORD")
    if not os.path.exists(DATA_FOLDER):
        print(f"❌ Папка {DATA_FOLDER} не найдена!")
        return

    # Оставляем пустым, чтобы парсить ВСЕ найденные pdf и docx.
    target_keywords = [
        "таблица в книжку по баллам бонитета",
        "6 объекты питания ско",
        "развит. туризма",
        "автостанции"
    ]

    total_files_processed = 0
    total_tables_created = 0

    for root, _, files in os.walk(DATA_FOLDER):
        for f in files:
            f_lower = f.lower()
            is_target = any(keyword in f_lower for keyword in target_keywords)

            # Берем ТОЛЬКО pdf и docx
            if is_target and f_lower.endswith(('.pdf', '.docx')) and not f.startswith('~$'):
                file_path = os.path.join(root, f)
                b_name = os.path.splitext(f)[0]

                print(f"\n📂 НАЙДЕН ФАЙЛ: {f}")

                tables_saved = 0
                if f_lower.endswith('.pdf'):
                    tables_saved = process_pdf_to_tables(file_path, b_name, f)
                elif f_lower.endswith('.docx'):
                    tables_saved = process_docx_to_tables(file_path, b_name, f)

                if tables_saved > 0:
                    total_files_processed += 1
                    total_tables_created += tables_saved
                else:
                    print("  ⚠️ Таблицы не найдены или они пустые.")

    print("\n" + "="*50)
    print("🏁 ИТОГОВЫЙ ОТЧЕТ:")
    print(f"   Обраработано файлов: {total_files_processed}")
    print(f"   Извлечено таблиц:    {total_tables_created}")
    print("="*50)

if __name__ == "__main__":
    main()
