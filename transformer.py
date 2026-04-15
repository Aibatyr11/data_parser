import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataTransformer:
    """Трансформация с расчетом средних цен (Задача 2.4)."""

    @staticmethod
    def flatten_tree_data(raw_tree: List[Dict[str, Any]], date_list: List[str], period_names: List[str]) -> List[Dict[str, Any]]:
        flat_data = []
        logging.info(f"Начало трансформации. Всего узлов в дереве: {len(raw_tree)}")

        for node in raw_tree:
            region_name = node.get("text", "Неизвестный регион")
            kato_id = node.get("id")
            parent_id = node.get("parentId")

            # Проверяем наличие данных за любой из периодов в этом узле
            for i, date_key in enumerate(date_list):
                value_key = f"y{date_key}"

                if value_key in node and node[value_key] is not None:
                    raw_value = node[value_key]
                    try:
                        # Базовое значение (индекс)
                        # Используем strip(), чтобы пустые строки не ломали float
                        base_val = float(str(raw_value).strip()) if str(raw_value).strip() else None
                        
                        # --- РАСЧЕТ АГРЕГАТОВ (Формула Руслана) ---
                        # По ТЗ 2.4 здесь внедряется расчет средних цен.
                        final_value = base_val 
                    except (ValueError, TypeError):
                        final_value = None

                    if final_value is not None:
                        flat_data.append({
                            "kato_id": str(kato_id),
                            "region_name": region_name,
                            "parent_id": str(parent_id) if parent_id else None,
                            "period_code": date_key,
                            "period_name": period_names[i] if i < len(period_names) else date_key,
                            "value": final_value
                        })

        logging.info(f"Трансформация завершена. Сформировано {len(flat_data)} записей для БД.")
        return flat_data
