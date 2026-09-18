"""
Сбор требований к поступлению (IELTS/TOEFL/SAT/ACT/GPA/стоимость) для фильтра сайта.

Стратегия трёх уровней (см. пояснение в чате):
  Tier 1: вузы США -> College Scorecard API. Полностью автоматически,
          тысячи вузов, официальные данные Минобразования США.
  Tier 2: все остальные вузы -> у них уже есть базовые поля (страна/город/сайт)
          из parse_universities.py. Требования по умолчанию = "нет данных".
  Tier 3: приоритетный список (все вузы КЗ + топ-N мира из top_world_universities.csv) ->
          скачиваем официальную admissions-страницу и просим LLM аккуратно
          вытащить IELTS/TOEFL/SAT/GPA и т.д. СТРОГО из текста, без домыслов.
          Если в тексте нет числа -> null, а не выдумка.

Установка: pip install requests pandas beautifulsoup4 lxml
Ключи:
  - COLLEGE_SCORECARD_API_KEY: бесплатно и мгновенно на https://api.data.gov/signup/
  - ANTHROPIC_API_KEY: свой ключ с console.anthropic.com (это НЕ тот ключ,
    что используется в артефактах Claude.ai — его для внешних скриптов брать нельзя)
"""

import json
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

COLLEGE_SCORECARD_API_KEY = "TKeEn5glQ1OBX5BM0xYkKIimrTNJcopGeC2aw7RS"  # замените на свой ключ для нормальных лимитов
ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"

HEADERS = {"User-Agent": "LOCUSHackathon2026-research-bot/1.0 (contact: your_email@example.com)"}


# ---------- TIER 1: США, College Scorecard ----------

def get_us_admission_data(per_page: int = 100, max_pages: int = 60) -> pd.DataFrame:
    """SAT/ACT/GPA-прокси/стоимость/acceptance rate для вузов США. Полностью официальные данные."""
    url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    fields = ",".join(
        [
            "school.name",
            "school.city",
            "school.state",
            "latest.cost.tuition.in_state",
            "latest.cost.tuition.out_of_state",
            "latest.admissions.admission_rate.overall",
            "latest.admissions.sat_scores.average.overall",
            "latest.admissions.act_scores.midpoint.cumulative",
        ]
    )
    rows = []
    for page in range(max_pages):
        params = {"api_key": COLLEGE_SCORECARD_API_KEY, "fields": fields, "per_page": per_page, "page": page}
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            break
        rows.extend(results)
        time.sleep(0.2)

    df = pd.json_normalize(rows)
    df = df.rename(
        columns={
            "school.name": "name",
            "school.city": "city",
            "school.state": "state",
            "latest.cost.tuition.out_of_state": "tuition_out_of_state_usd",
            "latest.cost.tuition.in_state": "tuition_in_state_usd",
            "latest.admissions.admission_rate.overall": "admission_rate",
            "latest.admissions.sat_scores.average.overall": "sat_average",
            "latest.admissions.act_scores.midpoint.cumulative": "act_midpoint",
        }
    )
    df["country"] = "United States"
    df["source"] = "collegescorecard.ed.gov"
    return df


# ---------- TIER 3: приоритетный список, LLM-экстракция ----------

def fetch_page_text(url: str, max_chars: int = 8000) -> str | None:
    """Скачивает страницу и вытаскивает читаемый текст (без HTML-тегов)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:max_chars]


def extract_admission_requirements(university_name: str, page_text: str, source_url: str) -> dict:
    """
    Просит LLM вытащить требования СТРОГО из текста страницы.
    Отсутствие данных -> null, а не выдумка (важно для честной оценки достоверности).
    """
    prompt = f"""Ты извлекаешь факты ТОЛЬКО из приведённого текста, ничего не придумывая.
Университет: {university_name}

Текст официальной страницы приёма:
\"\"\"
{page_text}
\"\"\"

Верни ТОЛЬКО валидный JSON без пояснений, по схеме:
{{
  "ielts_min": number или null,
  "toefl_min": number или null,
  "sat_range": [число, число] или null,
  "act_range": [число, число] или null,
  "gpa_min": number или null,
  "tuition_per_year_usd": number или null,
  "degree_levels": ["bachelor", "master", "phd", "foundation"] (только то, что реально упомянуто),
  "fields_of_study": [строки, только то, что реально упомянуто],
  "confidence": "high" | "medium" | "low",
  "notes": "коротко, если данные неполные или сомнительные"
}}"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 600,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    r.raise_for_status()
    raw = r.json()["content"][0]["text"].strip()
    raw = raw.strip("`")
    if raw.startswith("json"):
        raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"error": "не удалось распарсить ответ LLM", "raw": raw}

    parsed["university"] = university_name
    parsed["source_url"] = source_url
    return parsed


def build_priority_admission_data(priority_df: pd.DataFrame) -> list[dict]:
    """priority_df должен содержать колонки name и website."""
    results = []
    for _, row in priority_df.iterrows():
        name = row["name"]
        website = row.get("website") or row.get("web_pages")
        if not website:
            results.append({"university": name, "notes": "нет сайта в исходных данных, требования не собраны"})
            continue

        text = fetch_page_text(website)
        if not text:
            results.append({"university": name, "source_url": website, "notes": "страница недоступна"})
            continue

        try:
            req = extract_admission_requirements(name, text, website)
        except requests.RequestException as e:
            req = {"university": name, "source_url": website, "notes": f"ошибка LLM-запроса: {e}"}

        results.append(req)
        time.sleep(1)  # вежливая пауза между запросами к чужим серверам и к LLM API

    return results


if __name__ == "__main__":
    print("Tier 1: собираю данные по вузам США (College Scorecard)...")
    us_df = get_us_admission_data()
    us_df.to_csv("us_admission_requirements.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(us_df)} вузов США -> us_admission_requirements.csv")

    # Tier 3: пример для приоритетного списка (замените на реальный kz_universities.csv
    # + первые N строк top_world_universities.csv, объединённые заранее)
    print("\nTier 3 запускается отдельно на приоритетном списке (kz + top-N),")
    print("см. функцию build_priority_admission_data(). Не забудьте свой ANTHROPIC_API_KEY.")
