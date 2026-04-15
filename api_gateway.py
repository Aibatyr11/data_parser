from flask import Flask, jsonify, request
import logging
import re
from taldau_client import TaldauClient
from transformer import DataTransformer
from db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.json.ensure_ascii = False
client = TaldauClient()
transformer = DataTransformer()
db = DatabaseManager()

@app.route('/api/ui/search', methods=['GET'])
def search_index():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({"status": "error", "message": "Введите ключевое слово"}), 400
    results = client.search_index(keyword)
    return jsonify({"status": "success", "data": results})

@app.route('/api/etl/sync', methods=['POST'])
def sync_data():
    req_data = request.json or {}
    index_id = req_data.get('index_id')
    if not index_id:
        return jsonify({"status": "error", "message": "No index_id"}), 400

    logging.info(f"--- УЛЬТИМАТИВНЫЙ ETL ЗАПУСК: {index_id} ---")

    try:
        # 1. Получаем базу (Периоды и Сегменты)
        periods = client.get_periods(index_id)
        period_id = periods[0]['id'] if periods else 7
        segments = client.get_segments(index_id, period_id)
        segment = next((s for s in segments if "КАТО" in str(s.get('fullNames', ''))), segments[0])

        clean_dic_id = segment['dicId'].replace(' + ', ',').replace('+', ',')
        clean_terms = segment['termIds'].replace(' + ', ',').replace('+', ',')

        # Формируем полный набор параметров
        params_full = {
            "p_measure_id": 1,
            "p_index_id": index_id,
            "p_period_id": period_id,
            "p_terms": clean_terms,
            "p_term_id": clean_terms.split(',')[0],
            "p_dicIds": clean_dic_id,
            "idx": segment.get('idx', 0)
        }

        # 2. ШАГ 1: Скачиваем дерево ПЕРВЫМ ДЕЛОМ (Оно стабильнее)
        logging.info("Скачиваем дерево данных (рекурсивно)...")
        raw_tree = client.get_full_tree_recursive(params_full)
        
        if not raw_tree:
            return jsonify({"status": "error", "message": "Не удалось скачать дерево данных (Талдау лежит)"}), 500

        # 3. ШАГ 2: ПОЛУЧАЕМ ДАТЫ (План А или План Ц)
        date_list = []
        period_names = []

        logging.info("Пытаемся получить список дат...")
        dates_res = client.get_index_periods(params_full)

        if dates_res and isinstance(dates_res, list) and len(dates_res) > 0:
            # План А: Официальный ответ
            date_list = dates_res[0].get("dateList", [])
            period_names = dates_res[0].get("periodNameList", [])
            logging.info(f"Даты получены официально: {len(date_list)} шт.")
        else:
            # План Ц: Если сервер выдал 500, вытаскиваем ключи 'yXXXX' прямо из данных дерева!
            logging.warning("Талдау выдал 500 на даты. Включаю 'План Ц' (экстракция из дерева)...")
            # Берем первый узел (обычно это РК) и ищем ключи, начинающиеся на 'y'
            first_node = raw_tree[0]
            date_list = [re.sub(r'^y', '', key) for key in first_node.keys() if re.match(r'^y\d+', key)]
            period_names = [f"Период {d}" for d in date_list]
            logging.info(f"Даты извлечены из структуры данных: {len(date_list)} шт.")

        if not date_list:
            return jsonify({"status": "error", "message": "Даты не найдены ни в API, ни в данных дерева"}), 500

        # 4. Трансформация и сохранение
        flat_data = transformer.flatten_tree_data(raw_tree, date_list, period_names)
        db.save_statistics(flat_data)

        return jsonify({
            "status": "success", 
            "records_saved": len(flat_data), 
            "nodes_processed": len(raw_tree),
            "dates_found": len(date_list)
        })

    except Exception as e:
        logging.error(f"Критическая ошибка: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    kato_code = request.args.get('kato_code')
    return jsonify({"status": "success", "kato_filter": kato_code})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
