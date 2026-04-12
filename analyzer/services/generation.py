from gigachat import GigaChat

from analyzer.models import APIKey


# Сервис для работы с GigaChat API — генерация контента и мета-тегов
class GenerationService:

    # Fallback ключ на случай, если в базе нет активного
    _FALLBACK_KEY = (
        "MDE5YWI3NTgtMWE0MC03NGU3LWI4YzgtMjM2NDJmOGM2M2ZjOjY5NWE2MjkzLWU4ZDgtNGM0OC1hNmZhLTg3YmZiZjRlNWY5OA=="
    )

    @staticmethod
    def get_gigachat_key() -> str:
        """Берём ключ из базы, если нет — используем захардкоженный."""
        key_record = APIKey.objects.filter(is_active=True, name__icontains="gigachat").first()
        if key_record:
            return key_record.key
        return GenerationService._FALLBACK_KEY

    @staticmethod
    def generate_content(cluster_name: str, top_keys: list, role_prompt: str = "Ты ведущий эксперт и редактор.") -> str:
        """Генерирует SEO-статью по теме кластера."""
        chat = GigaChat(
            credentials=GenerationService.get_gigachat_key(),
            verify_ssl_certs=False,
            model="GigaChat:latest",
            temperature=0.8,
        )
        prompt = (
            f"РОЛЬ: {role_prompt}. Твоя задача — написать информативную, экспертную и полезную SEO-статью.\n"
            f"ОСНОВНАЯ ТЕМА: {cluster_name}\n"
            f"ОБЯЗАТЕЛЬНЫЕ КЛЮЧЕВЫЕ СЛОВА (используй органично, можно склонять): {', '.join(top_keys)}\n\n"
            f"ТРЕБОВАНИЯ К ТЕКСТУ:\n"
            f"1. Объем: не менее 8000 символов. Тема должна быть раскрыта глубоко и подробно.\n"
            f"2. Структура: используй структуру статьи с введением, основным телом (заголовки H2, H3) и логичным заключением.\n"
            f"3. Оформление: разделяй текст на удобные абзацы (не более 4-5 предложений), обязательно используй маркированные списки для перечислений.\n"
            f"4. Стиль и польза: пиши естественным, понятным языком для людей. Избегай 'воды', сложных штампов и канцеляризмов. Давай конкретную пользу читателю.\n"
            f"Сгенерируй готовую статью в формате Markdown."
        )
        response = chat.chat(prompt)
        return response.choices[0].message.content

    @staticmethod
    def generate_meta(main_keyword: str, role_prompt: str = "Ты SEO-специалист.") -> str:
        """Генерирует 3 варианта Title + Description для страницы."""
        chat = GigaChat(
            credentials=GenerationService.get_gigachat_key(),
            verify_ssl_certs=False,
            model="GigaChat:latest",
        )
        prompt = (
            f"РОЛЬ: {role_prompt}. Твоя задача — составить качественные, кликабельные SEO метатеги.\n"
            f"ГЛАВНЫЙ ЗАПРОС СТРАНИЦЫ: '{main_keyword}'\n\n"
            f"Сгенерируй 3 уникальных варианта связки (Title + Description).\n"
            f"ТРЕБОВАНИЯ:\n"
            f"1. Title (заголовок): длина от 40 до 60 символов. Должен естественно включать главный запрос ближе к началу и привлекать внимание.\n"
            f"2. Description (описание): длина от 130 до 160 символов. Должен раскрывать суть страницы, содержать призыв к действию (CTA) и отражать ценность для пользователя.\n"
            f"Верни ответ в удобном читабельном текстовом формате без лишних вступлений."
        )
        res = chat.chat(prompt)
        return res.choices[0].message.content
