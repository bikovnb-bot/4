import hashlib
import requests
from django.core.cache import cache
from django.conf import settings

class YandexTranslateAPI:
    """
    Клиент для Yandex Cloud Translate API.
    """
    def __init__(self):
        self.api_key = settings.YANDEX_CLOUD_API_KEY
        self.folder_id = settings.YANDEX_CLOUD_FOLDER_ID
        self.url = "https://translate.api.cloud.yandex.net/translate/v2/translate"

    def _get_cache_key(self, text, target_lang='ru'):
        """Генерирует уникальный ключ для кэширования."""
        hash_object = hashlib.md5(f"{text}_{target_lang}".encode())
        return f'yandex_translate_{hash_object.hexdigest()}'

    def translate(self, text, target_lang='ru'):
        """
        Переводит текст на указанный язык с кэшированием результата.
        """
        if not text or not text.strip():
            return text

        # Проверяем кэш
        cache_key = self._get_cache_key(text, target_lang)
        cached_text = cache.get(cache_key)
        if cached_text:
            return cached_text

        # Подготавливаем запрос к API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
        }
        body = {
            "targetLanguageCode": target_lang,
            "texts": [text],
        }

        try:
            response = requests.post(self.url, json=body, headers=headers)
            response.raise_for_status() # Выбросит исключение при HTTP-ошибке

            # Извлекаем переведённый текст из ответа
            # API возвращает JSON: { "translations": [{"text": "...", ...}] }
            translated_text = response.json()["translations"][0]["text"]
            
            # Сохраняем в кэш на неделю (время можно регулировать)
            cache.set(cache_key, translated_text, timeout=60*60*24*7)
            return translated_text
        except Exception as e:
            # Логируем ошибку, но возвращаем оригинал, чтобы не ломать форму
            print(f"Translation error: {e}")
            return text

# Создаём глобальный экземпляр клиента
translator = YandexTranslateAPI()

def translate_to_russian(text):
    """Вспомогательная функция для перевода текста на русский."""
    return translator.translate(text)