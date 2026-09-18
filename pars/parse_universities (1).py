import io
import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def fetch_kz_universities():
    url = "http://universities.hipolabs.com/search?country=Kazakhstan"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data)
    df = df[['name', 'web_pages', 'country', 'alpha_two_code']]
    df.to_csv("kz_universities.csv", index=False)
    print(f"kz_universities.csv -> {len(df)} вузов Казахстана")
    return df


def fetch_cwur_top1000():
    # Актуальный URL рейтинга CWUR
    url = "https://cwur.org/2023.php"

    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    # Оборачиваем HTML-строку в io.StringIO, чтобы pandas распознал её как поток данных
    tables = pd.read_html(io.StringIO(resp.text), header=0)

    if not tables:
        raise ValueError("Таблицы на странице CWUR не найдены")

    world_df = tables[0]

    # Сохраняем итоговый CSV-файл
    world_df.to_csv("top_world_universities.csv", index=False)
    print(f"top_world_universities.csv -> {len(world_df)} топовых вузов мира")
    return world_df


if __name__ == "__main__":
    fetch_kz_universities()
    world_df = fetch_cwur_top1000()
    print("Готово! Оба CSV файла успешно сформированы.")