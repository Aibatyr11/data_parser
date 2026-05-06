import requests
import logging
import time
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TaldauClient:
    BASE_URL = "http://taldau.stat.gov.kz/ru/Api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://taldau.stat.gov.kz/"
        })

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=120)
            if response.status_code == 500:
                logging.error(f"Сервер Талдау вернул 500 для {url}")
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Ошибка запроса к {endpoint}: {e}")
            return None

    def search_index(self, keyword: str) -> List[Dict[str, Any]]:
        data = self._make_request("Search", params={"keyword": keyword})
        results = []
        if data and 'results' in data:
            for item in data['results']:
                results.append({"id": item["id"], "Name": item["Name"]})
        return results

    def get_periods(self, index_id: int) -> Any:
        return self._make_request("GetPeriodList", params={"indexId": index_id})

    def get_segments(self, index_id: int, period_id: int) -> Any:
        return self._make_request("GetSegmentList", params={"indexId": index_id, "periodId": period_id})

    def get_index_periods(self, params_dict: Dict[str, Any]) -> Any:
        return self._make_request("GetIndexPeriods", params=params_dict)

    def get_full_tree_recursive(self, params_dict: Dict[str, Any], parent_id: str = "") -> List[Dict[str, Any]]:
        all_nodes = []
        current_params = params_dict.copy()
        current_params["p_parent_id"] = parent_id

        logging.info(f"Запрос дерева: parent_id='{parent_id}'")
        nodes = self._make_request("GetIndexTreeData", params=current_params)

        if not nodes or not isinstance(nodes, list):
            return all_nodes

        for node in nodes:
            all_nodes.append(node) 
           
            is_leaf = str(node.get('leaf', 'true')).lower() == 'true'
    
            if not is_leaf:
                child_id = str(node.get('id'))
                logging.info(f"  --> Узел {node.get('text')} имеет дочерние регионы! Спускаемся в id: {child_id}...")
                
                time.sleep(0.3) # Пауза для стабильности
                child_nodes = self.get_full_tree_recursive(params_dict, parent_id=child_id)
                all_nodes.extend(child_nodes)
                    
        return all_nodes
