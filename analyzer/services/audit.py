import time

import requests
from bs4 import BeautifulSoup


# Сервис для проверки здоровья сайта (SEO-аудит)
class AuditService:

    @staticmethod
    def check_site_health(url: str) -> dict:
        print(f"Аудит сайта: {url}")

        if not url.startswith("http"):
            url = "https://" + url

        stats = {"score": 100, "checks": []}

        def add_check(name, status, msg, penalty=0):
            stats["checks"].append({"name": name, "status": status, "msg": msg})
            if not status:
                stats["score"] = max(0, stats["score"] - penalty)

        try:
            start_time = time.time()
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            load_time = round((time.time() - start_time) * 1000)

            if resp.status_code == 200:
                add_check("Доступность", True, "200 OK")
            else:
                add_check("Доступность", False, f"Код {resp.status_code}", 50)

            if url.startswith("https"):
                add_check("SSL", True, "HTTPS есть")
            else:
                add_check("SSL", False, "Нет HTTPS", 20)

            if load_time < 500:
                add_check("Скорость", True, f"{load_time} мс")
            elif load_time < 1500:
                add_check("Скорость", True, f"{load_time} мс (Норм)")
            else:
                add_check("Скорость", False, f"{load_time} мс (Медленно)", 10)

            soup = BeautifulSoup(resp.text, "html.parser")

            if soup.title and soup.title.string:
                length = len(soup.title.string)
                if 10 < length < 70:
                    add_check("Title", True, f"OK ({length} симв.)")
                else:
                    add_check("Title", False, f"Неоптимально ({length} симв.)", 5)
            else:
                add_check("Title", False, "Отсутствует!", 20)

            desc = soup.find("meta", attrs={"name": "description"})
            if desc and desc.get("content"):
                add_check("Description", True, "Присутствует")
            else:
                add_check("Description", False, "Отсутствует!", 10)

            h1s = soup.find_all("h1")
            if len(h1s) == 1:
                add_check("H1", True, "Один H1 (Отлично)")
            elif len(h1s) == 0:
                add_check("H1", False, "Нет H1", 15)
            else:
                add_check("H1", False, f"Найдено {len(h1s)} H1", 10)

        except Exception as exc:
            add_check("Ошибка", False, str(exc)[:50], 100)
            stats["score"] = 0

        return stats
