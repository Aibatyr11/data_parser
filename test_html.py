import requests
from bs4 import BeautifulSoup

USER_COOKIE = "PHPSESSID=Mul2L5tujJ9C6ERebvLKcRU2fzElsk14; _ym_uid=1776416089216442067; _ym_d=1776416089; _ym_isad=2; BITRIX_SM_UIDD=2shma394cc1057lgcty0foo03y4zjgc0; BITRIX_SM_SOUND_LOGIN_PLAYED=Y"
SESSID = "ca20b4ce554a3c6b990b828d64fdb763"

url = "https://stat.gov.kz/ru/cabinet/juridical/by/bin/"

# ВОЗВРАЩАЕМ ПОЛНЫЕ ЗАГОЛОВКИ
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Cookie": USER_COOKIE,
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://stat.gov.kz",
    "Referer": "https://stat.gov.kz/ru/cabinet/juridical/by/bin/"
}

data = {
    "sessid": SESSID,
    "bin": "141040019612",
    "search": "Поиск"
}

print("[*] Отправляем полный запрос с заголовками...")
response = requests.post(url, headers=headers, data=data)
soup = BeautifulSoup(response.text, 'html.parser')

print("\n--- АНАЛИЗ ОТВЕТА СЕРВЕРА ---")
clean_text = soup.get_text(separator=' ', strip=True)

if "Пожалуйста, авторизуйтесь" in clean_text:
    print("❌ ОШИБКА: Сайт снова просит авторизацию!")
    print("Диагноз: Сработала привязка к IP-адресу. Твой Cookie действует только на твоем домашнем компьютере, а сервер Ubuntu он не пускает.")
elif "141040019612" in clean_text or "национальной статистики" in clean_text.lower():
    print("✅ УСПЕХ! Мы пробили защиту.")
    # Ищем таблицу
    table = soup.find('table')
    if table:
        for row in table.find_all('tr'):
            cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
            if cells: print(" | ".join(cells))
    else:
        print("Таблицы нет, но данные прошли. Вот кусок текста:")
        print(clean_text[:1000])
else:
    print("⚠️ НЕПОНЯТНЫЙ ОТВЕТ:")
    print(clean_text[:500])
print("-----------------------------")
