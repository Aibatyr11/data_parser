import os
import re
import pandas as pd
import docx
from sqlalchemy import create_engine

DB_URL = "postgresql://postgres:123@127.0.0.1:5433/reports_db?client_encoding=utf8"
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
                text = [cell.text.strip() for cell in row.cells]
                
                if j == 0:
                    keys = text
                    continue
                
                row_dict = dict(zip(keys, text))
                data.append(row_dict)
            
            df = pd.DataFrame(data)
            df = fix_columns(df)
            
            table_name = base_table_name if len(tables) == 1 else f"{base_table_name}_part{i+1}"
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            print(f"Успех: {os.path.basename(file_path)} (Таблица {i+1}) -> таблица '{table_name}' ({len(df)} строк)")
            
    except Exception as e:
        print(f"Ошибка с Word файлом {os.path.basename(file_path)}:")
        print(f"Детали: {str(e)[:150]}...")

def main():
    print("Начинаем парсинг файлов...")
    if not os.path.exists(DATA_FOLDER):
        print(f"Создай папку '{DATA_FOLDER}'!")
        return

    for filename in os.listdir(DATA_FOLDER):
        file_path = os.path.join(DATA_FOLDER, filename)
        if not os.path.isfile(file_path) or filename.startswith('~'):
            continue
            
        table_name = clean_table_name(filename)
        
        if filename.endswith(('.xlsx', '.xls', '.csv')):
            parse_excel_csv(file_path, table_name)
        elif filename.endswith('.docx'):
            parse_word(file_path, table_name)

    print("Все готово! Открой pgAdmin и проверь таблицы.")

if __name__ == "__main__":
    main()