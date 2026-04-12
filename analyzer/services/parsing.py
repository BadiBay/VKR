import re
import statistics
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer


# Сервис для парсинга поисковых систем и анализа конкурентов
class ParsingService:

    # Домены-агрегаторы, которые не нужны при анализе конкурентов
    STOP_DOMAINS = [
        "ozon.ru", "wildberries.ru", "market.yandex.ru",
        "avito.ru", "youtube.com", "vk.com", "wikipedia.org",
    ]

    @staticmethod
    def search_engine_parser(query: str, limit: int = 50) -> list:
        """Собирает URL из поисковой выдачи. Сначала Google, потом DuckDuckGo."""
        print(f"🔎 Позиции: ищем '{query}'...")
        urls = []

        # Пробуем Google
        try:
            google_url = "https://www.google.com/search"
            params = {"q": query, "num": limit, "hl": "ru"}
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = requests.get(google_url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href")
                    if href and href.startswith("http") and "google" not in href:
                        urls.append(href)
                if len(urls) > 5:
                    print(f"✅ Google выдал {len(urls)} результатов.")
                    return urls[:limit]
        except Exception as exc:
            print(f"⚠️ Google search error: {exc}")

        # Если Google не сработал — пробуем DuckDuckGo
        print("🔄 Переключаемся на DuckDuckGo...")
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.post(ddg_url, data={"q": query}, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.find_all("a", class_="result__a"):
                href = link.get("href")
                if href:
                    if "uddg=" in href:
                        parsed = urlparse(href)
                        qs = parse_qs(parsed.query)
                        if "uddg" in qs:
                            urls.append(qs["uddg"][0])
                    else:
                        urls.append(href)
            print(f"✅ DDG выдал {len(urls)} результатов.")
        except Exception as exc:
            print(f"⚠️ DDG search error: {exc}")

        return urls[:limit]

    @staticmethod
    def analyze_serp(query: str) -> dict:
        """Анализирует топ-3 конкурента: текст, заголовки, LSI-слова."""
        print(f"Анализируем конкурентов для: {query}")
        headers = {"User-Agent": "Mozilla/5.0"}

        raw_urls = ParsingService.search_engine_parser(query, limit=30)
        competitor_urls = []
        for url in raw_urls:
            if any(bad in url.lower() for bad in ParsingService.STOP_DOMAINS):
                continue
            competitor_urls.append(url)
            if len(competitor_urls) >= 3:
                break

        text_lengths = []
        all_headers = []
        page_texts = []

        for url in competitor_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.extract()
                text = soup.get_text(separator=" ")
                clean_text = re.sub(r"\s+", " ", text).strip()

                if len(clean_text) > 500:
                    text_lengths.append(len(clean_text))
                    page_texts.append(clean_text)

                    headers_list = []
                    for h in soup.find_all(["h2", "h3"]):
                        txt = h.get_text().strip()
                        if 5 < len(txt) < 100:
                            headers_list.append(f"{h.name.upper()}: {txt}")
                    if headers_list:
                        domain = url.split("//")[-1].split("/")[0]
                        all_headers.append(
                            f"\n>>> {domain}:\n" + "\n".join(headers_list[:10])
                        )
            except Exception:
                continue

        avg_len = int(statistics.mean(text_lengths)) if text_lengths else 3500

        # Извлекаем LSI-слова через TF-IDF
        lsi_words = []
        if page_texts:
            try:
                vectorizer = TfidfVectorizer(
                    max_features=20,
                    token_pattern=r"(?u)\b[а-яА-ЯёЁ]{4,}\b",
                )
                tfidf_matrix = vectorizer.fit_transform(page_texts)
                feature_names = vectorizer.get_feature_names_out()
                sums = tfidf_matrix.sum(axis=0)
                data = [(term, sums[0, col]) for col, term in enumerate(feature_names)]
                lsi_words = [x[0] for x in sorted(data, key=lambda x: x[1], reverse=True)[:15]]
            except Exception as exc:
                print(f"TF-IDF Error: {exc}")

        return {
            "competitors_urls": competitor_urls,
            "avg_text_length": avg_len,
            "competitors_structure": "\n".join(all_headers),
            "lsi_words": lsi_words,
        }
