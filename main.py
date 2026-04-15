import os
import re
import pandas as pd
import docx
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)

DATA_FOLDER = "files_to_parse"

def clean_table_name(filename):
    name = os.path.splitext(filename)[0]
    clean_name = re.sub(r'\W+', '_', name.lower()).strip('_')
    return clean_name[:25].rstrip('_')

def fix_columns(df):
    new_cols = []
    seen = {}
    for i, c in enumerate(df.columns):
        c_str = str(c).strip()

        if not c_str or c_str.lower() == 'nan' or 'unnamed' in c_str.lower():
            c_str = f"колонка_{i+1}"

        if c_str in seen:
            seen[c_str] += 1
            final_col = f"{c_str}_{seen[c_str]}"
        else:
            seen[c_str] = 0
            final_col = c_str

        new_cols.append(final_col)

    df.columns = new_cols
    return df

def parse_excel_csv(file_path, table_name):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, skiprows=5)

        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        df = fix_columns(df)

        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"Успех: {os.path.basename(file_path)} -> таблица '{table_name}' ({len(df)} строк)")

    except Exception as e:
        print(f"Ошибка с Excel файлом {os.path.basename(file_path)}:")
        print(f"Детали: {str(e)[:150]}...")

def parse_word(file_path, base_table_name):
    try:
        doc = docx.Document(file_path)
        tables = doc.tables

        if not tables:
            print(f"Пропуск: В файле {os.path.basename(file_path)} нет таблиц.")
            return

        for i, table in enumerate(tables):
            data = []
            keys = None

            for j, row in enumerate(table.rows):
                text_cells = [cell.text.strip() for cell in row.cells]

                if j == 0:
                    keys = text_cells
                    continue

                row_dict = dict(zip(keys, text_cells))
                data.append(row_dict)

            df = pd.DataFrame(data)
            df = fix_columns(df)

            table_name = base_table_name if len(tables) == 1 else f"{base_table_name}_part{i+1}"
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            print(f"Успех: {os.path.basename(file_path)} (Таблица {i+1}) -> таблица '{table_name}' ({len(df)} строк)")

    except Exception as e:
        print(f"Ошибка с Word файлом {os.path.basename(file_path)}:")
        print(f"Детали: {str(e)[:150]}...")

def merge_split_tables():
    print("\nНачинаем процесс объединения разделенных таблиц (part1, part2...)...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Группируем таблицы по базовому имени
    groups = {}
    for t in tables:
        match = re.search(r'^(.*)_part(\d+)$', t)
        if match:
            base = match.group(1)
            if base not in groups:
                groups[base] = []
            groups[base].append(t)
            
    if not groups:
        print("Таблиц для объединения не найдено.")
        return

    report = ["Отчет об объединении разбитых таблиц:\n" + "-"*50]
    
    for base_name, parts in groups.items():
        # Сортируем части по номеру (чтобы part10 шла после part9, а не после part1)
        parts.sort(key=lambda x: int(re.search(r'_part(\d+)$', x).group(1)))
        
        dfs = []
        for p in parts:
            try:
                df = pd.read_sql_table(p, engine)
                dfs.append(df)
            except Exception as e:
                print(f"Ошибка при чтении таблицы {p}: {e}")
                
        if dfs:
            # Склеиваем все DataFrame'ы в один
            merged_df = pd.concat(dfs, ignore_index=True)
            # Сохраняем в базу под общим именем
            merged_df.to_sql(base_name, engine, if_exists='replace', index=False)
            
            report.append(f"✅ Создана единая таблица: '{base_name}'")
            report.append(f"   Объединено частей: {len(parts)} (от {parts[0]} до {parts[-1]})")
            report.append(f"   Всего строк: {len(merged_df)}\n")
            
            # Удаляем старые куски из базы, чтобы не занимали место
            with engine.begin() as conn:
                for p in parts:
                    conn.execute(text(f'DROP TABLE "{p}"'))
                    
    # Сохраняем отчет в текстовый файл
    with open("merged_tables_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"✅ Все части успешно объединены! Отчет сохранен в 'merged_tables_report.txt'")

def main():
    print("Начинаем парсинг файлов...")
    if not os.path.exists(DATA_FOLDER):
        print(f"Создай папку '{DATA_FOLDER}'!")
        return

    processed_files = []

    for root, dirs, files in os.walk(DATA_FOLDER):
        for filename in files:
            file_path = os.path.join(root, filename)

            if not os.path.isfile(file_path) or filename.startswith('~') or filename.startswith('.'):
                continue

            table_name = clean_table_name(filename)

            if filename.endswith(('.xlsx', '.xls', '.csv')):
                parse_excel_csv(file_path, table_name)
                processed_files.append(filename)
            elif filename.endswith('.docx'):
                parse_word(file_path, table_name)
                processed_files.append(filename)

    if processed_files:
        with open("list_of_files.txt", "w", encoding="utf-8") as f:
            f.write("Список загруженных файлов (датасетов):\n")
            f.write("-" * 40 + "\n")
            for name in set(processed_files):
                f.write(f"- {name}\n")
        print("\nУспешно сгенерирован файл 'list_of_files.txt' со списком файлов!")
    else:
        print("\nВ папке и подпапках не найдено ни одного Excel или Word файла.")

    # ЗАПУСКАЕМ ОБЪЕДИНЕНИЕ ТАБЛИЦ СРАЗУ ПОСЛЕ ПАРСИНГА
    merge_split_tables()

if __name__ == "__main__":
    main()
