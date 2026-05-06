import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CompanyParser:
    def __init__(self):
        self.session = requests.Session()
        
        # Те самые авторизованные куки с твоего скриншота!
        AUTHORIZED_COOKIES = "_ym_uid=1776416089216442067; _ym_d=1776416089; _ym_isad=2; BITRIX_SM_UIDD=2shma394cc1057lgcty0foo03y4zjgc0; PHPSESSID=nApsZclPDj4iWqx53SvSPVRAJ16pDeNG; BITRIX_SM_SOUND_LOGIN_PLAYED=Y"
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Origin": "https://stat.gov.kz",
            "Referer": "https://stat.gov.kz/ru/cabinet/juridical/by/bin/",
            "Cookie": AUTHORIZED_COOKIES
        })
        self.search_url = "https://stat.gov.kz/ru/cabinet/juridical/by/bin/"

    def _init_session(self):
        """Делаем GET-запрос для извлечения скрытого токена sessid"""
        try:
            response = self.session.get(self.search_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            sessid_input = soup.find('input', {'name': 'sessid'})
            return sessid_input['value'] if sessid_input else ""
        except Exception as e:
            logging.error(f"Ошибка получения sessid: {e}")
            return ""

    def get_company_info(self, bin_code: str) -> dict:
        sessid = self._init_session()
        
        if not sessid:
            return {"request_status": "error", "message": "Не удалось получить sessid. Возможно, Cookie протухли."}

        # Формируем Payload
        payload = {
            "sessid": sessid,
            "bin": bin_code,
            "search": "Поиск"
        }

        try:
            response = self.session.post(self.search_url, data=payload, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            clean_text = soup.get_text(separator=' ', strip=True)
            if "Пожалуйста, авторизуйтесь" in clean_text:
                logging.error("Сессия истекла! Нужно обновить Cookie.")
                return {"request_status": "error", "message": "Требуется обновление Cookie (авторизация истекла)"}

            return self._parse_html_table(soup, bin_code)

        except Exception as e:
            logging.error(f"Ошибка при запросе: {e}")
            return {"request_status": "error", "message": str(e)}

    def _parse_html_table(self, soup, bin_code) -> dict:
        company_data = {
            "bin": bin_code,
            "name": "Не найдено",
            "oked": "Не найдено",
            "head_name": "Не найдено",
            "address": "Не найдено",
            "status": "Не найдено",
            "size": "Не найдено",
            "request_status": "success"
        }

        table = soup.find('table')
        if not table:
            company_data["request_status"] = "error"
            company_data["message"] = "Предприятие не найдено или таблица отсутствует"
            return company_data

        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if "наименование" in key and "вида" not in key and "крп" not in key:
                    company_data["name"] = value
                elif "основной код окэд" in key:
                    company_data["oked"] = value
                elif "руководител" in key:
                    company_data["head_name"] = value
                elif "адрес" in key:
                    company_data["address"] = value
                elif "статус" in key:
                    company_data["status"] = value
                elif "наименование крп" in key:
                    company_data["size"] = value

        return company_data

# Для быстрого теста прямо из консоли сервера:
if __name__ == "__main__":
    parser = CompanyParser()
    print("Тестируем БИН 020240000555 (КазМунайГаз)...")
    res = parser.get_company_info("020240000555")
    print(res)
