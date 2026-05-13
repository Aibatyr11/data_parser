# Data Parser (ETL & API Gateway)

Проект для извлечения, трансформации и загрузки (ETL) статистических и корпоративных данных в базу данных PostgreSQL. Поддерживает сбор данных через внешние API (ИС «Талдау»), веб-парсинг (stat.gov.kz) и обработку локальных файлов (Excel, PDF, Word). 

Взаимодействие с парсером и запуск пайплайна осуществляется через REST API.

## Структура проекта

* `api_gateway.py` — REST API шлюз. Точка входа в приложение, оркестрирует ETL-процесс.
* `taldau_client.py` — клиент для взаимодействия с API ИС «Талдау» (Extract).
* `company_parser.py` — веб-парсер данных юридических лиц по БИН (Extract).
* `main.py` — обработка и парсинг локальных документов (Excel, PDF, Word).
* `transformer.py` — логика трансформации данных: сплющивание JSON, типизация, очистка, расчет агрегатов (Transform).
* `db_manager.py` — управление БД PostgreSQL: пакетная загрузка (batch insert) и обновление записей (upsert) (Load).
* `check_data.py` — скрипт для аудита таблиц и проверки данных в БД.
* `test_html.py`, `test_transformer.py` — юнит-тесты.

## Стек технологий

* Python 3
* Flask
* PostgreSQL (psycopg2)
* Pandas
* BeautifulSoup4 (bs4)
