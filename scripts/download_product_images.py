"""
Скрипт для автоматического поиска и скачивания изображений товаров.
Использует Unsplash API для поиска изображений по названию товара.
"""
import asyncio
import os
import sys
from pathlib import Path

# Устанавливаем UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from PIL import Image, ImageDraw, ImageFont
import io
from urllib.parse import quote, urlparse, parse_qs
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import time
import re
import json
from bs4 import BeautifulSoup

from app.config import settings
from app.products.models import Product
from app.products.dao import ProductsDAO
from app.category.dao import CategoriesDAO

# API ключи (можно получить бесплатно)
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# URLs для API
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"
PEXELS_API_URL = "https://api.pexels.com/v1/search"


def download_image_from_url(url: str, timeout: int = 20, max_retries: int = 3) -> bytes | None:
    """Скачивает изображение по URL с retry механизмом."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    
    # Пропускаем миниатюры Bing (они не скачиваются напрямую)
    if 'tse' in url and 'bing.net' in url:
        return None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            # Проверяем, что это изображение
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                # Иногда сервер не возвращает правильный content-type, но это изображение
                if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                    return None
            
            content = response.content
            
            # Проверяем минимальный размер (должно быть больше 1KB)
            if len(content) < 1024:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            
            return content
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"[WARNING] Timeout при скачивании {url[:80]}...")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            print(f"[WARNING] Ошибка скачивания {url[:80]}...: {str(e)[:80]}")
            return None
        except Exception as e:
            print(f"[WARNING] Неожиданная ошибка при скачивании {url[:80]}...: {str(e)[:80]}")
            return None
    
    return None


def search_image_unsplash(product_name: str, category_name: str = None) -> str | None:
    """Ищет изображение через Unsplash API."""
    if not UNSPLASH_ACCESS_KEY:
        return None
    
    try:
        # Формируем поисковый запрос
        search_query = product_name.lower()
        
        # Улучшаем запрос на основе категории
        category_keywords = {
            "смартфон": "smartphone mobile phone",
            "ноутбук": "laptop computer",
            "планшет": "tablet",
            "телевизор": "tv television",
            "наушник": "headphones",
            "фотоаппарат": "camera",
            "камера": "camera",
            "часы": "smartwatch watch",
            "пылесос": "vacuum cleaner",
            "холодильник": "refrigerator fridge"
        }
        
        if category_name:
            for key, value in category_keywords.items():
                if key in category_name.lower():
                    search_query = value
                    break
        
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        params = {
            "query": search_query,
            "per_page": 1,
            "orientation": "squarish"
        }
        
        response = requests.get(UNSPLASH_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results") and len(data["results"]) > 0:
            return data["results"][0]["urls"]["regular"]
    except Exception as e:
        print(f"[WARNING] Unsplash API ошибка: {str(e)[:100]}")
    
    return None


def search_image_pexels(product_name: str, category_name: str = None) -> str | None:
    """Ищет изображение через Pexels API."""
    if not PEXELS_API_KEY:
        return None
    
    try:
        # Формируем поисковый запрос
        search_query = product_name.lower()
        
        # Улучшаем запрос на основе категории
        category_keywords = {
            "смартфон": "smartphone mobile phone",
            "ноутбук": "laptop computer",
            "планшет": "tablet",
            "телевизор": "tv television",
            "наушник": "headphones",
            "фотоаппарат": "camera",
            "камера": "camera",
            "часы": "smartwatch watch",
            "пылесос": "vacuum cleaner",
            "холодильник": "refrigerator fridge"
        }
        
        if category_name:
            for key, value in category_keywords.items():
                if key in category_name.lower():
                    search_query = value
                    break
        
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": search_query,
            "per_page": 1,
            "orientation": "square"
        }
        
        response = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("photos") and len(data["photos"]) > 0:
            return data["photos"][0]["src"]["large"]
    except Exception as e:
        print(f"[WARNING] Pexels API ошибка: {str(e)[:100]}")
    
    return None


def search_image_google_images(product_name: str) -> str | None:
    """Ищет изображение через Google Images (веб-скрапинг)."""
    try:
        # Формируем поисковый запрос
        search_query = quote(product_name)
        url = f"https://www.google.com/search?q={search_query}&tbm=isch&tbs=isz:m"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем изображения в структуре Google Images
        # Google использует JSON данные в скриптах
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Ищем прямые URL изображений в JSON
                # Паттерн 1: прямые URL
                matches = re.findall(r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', script.string)
                if matches:
                    for img_url in matches[:5]:  # Проверяем первые 5
                        # Пропускаем Google proxy и иконки
                        if 'gstatic.com' not in img_url and 'googleusercontent.com' not in img_url:
                            if 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                                return img_url
                
                # Паттерн 2: извлекаем из Google proxy
                matches2 = re.findall(r'"(https?://[^"]+)"', script.string)
                for match in matches2[:10]:
                    if 'imgurl=' in match:
                        try:
                            parsed = urlparse(match)
                            params = parse_qs(parsed.query)
                            if 'imgurl' in params:
                                img_url = params['imgurl'][0]
                                if 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                                    return img_url
                        except:
                            continue
        
        # Альтернативный метод: ищем в data-атрибутах
        images = soup.find_all('img', {'data-src': True})
        for img in images[:10]:  # Берём первые 10
            img_url = img.get('data-src') or img.get('src')
            if img_url and img_url.startswith('http'):
                # Пропускаем Google proxy и иконки
                if 'gstatic.com' not in img_url and 'googleusercontent.com' not in img_url:
                    if 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                        return img_url
        
    except Exception as e:
        print(f"[WARNING] Google Images ошибка: {str(e)[:100]}")
    
    return None


def search_image_bing_images(product_name: str) -> str | None:
    """Ищет изображение через Bing Images (веб-скрапинг)."""
    try:
        search_query = quote(product_name)
        url = f"https://www.bing.com/images/search?q={search_query}&qft=+filterui:imagesize-large"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем JSON данные с прямыми URL изображений
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Ищем прямые URL изображений в JSON
                # Bing использует структуру с murl (media URL)
                matches = re.findall(r'"murl":"(https?://[^"]+)"', script.string)
                if matches:
                    for match in matches[:3]:  # Проверяем первые 3
                        # Пропускаем миниатюры Bing
                        if 'tse' not in match and 'bing.net' not in match:
                            # Пропускаем иконки и логотипы
                            if 'logo' not in match.lower() and 'icon' not in match.lower():
                                return match
                
                # Альтернативный паттерн
                matches2 = re.findall(r'"contentUrl":"(https?://[^"]+)"', script.string)
                if matches2:
                    for match in matches2[:3]:
                        if 'tse' not in match and 'bing.net' not in match:
                            if 'logo' not in match.lower() and 'icon' not in match.lower():
                                return match
        
        # Ищем в data-атрибутах (резервный метод)
        images = soup.find_all('img', {'data-src': True})
        for img in images[:10]:
            img_url = img.get('data-src') or img.get('src')
            if img_url and img_url.startswith('http'):
                # Пропускаем миниатюры Bing и иконки
                if 'tse' not in img_url and 'bing.net' not in img_url:
                    if 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                        return img_url
        
    except Exception as e:
        print(f"[WARNING] Bing Images ошибка: {str(e)[:100]}")
    
    return None


def search_image_yandex_images(product_name: str) -> str | None:
    """Ищет изображение через Yandex Images (веб-скрапинг)."""
    try:
        search_query = quote(product_name)
        url = f"https://yandex.ru/images/search?text={search_query}&itype=jpg"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Yandex использует data-bem атрибуты с JSON
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Паттерн 1: прямые URL в JSON
                matches = re.findall(r'"url":"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', script.string)
                if matches:
                    for match in matches[:5]:
                        # Пропускаем Yandex proxy и иконки
                        if 'yandex' not in match.lower() or 'img.yandex' in match.lower():
                            if 'logo' not in match.lower() and 'icon' not in match.lower():
                                return match
                
                # Паттерн 2: origin в JSON
                matches2 = re.findall(r'"origin":"(https?://[^"]+)"', script.string)
                if matches2:
                    for match in matches2[:5]:
                        if 'logo' not in match.lower() and 'icon' not in match.lower():
                            return match
        
        # Альтернативный метод: ищем в data-атрибутах
        images = soup.find_all('img', src=True)
        for img in images[:15]:
            img_url = img.get('src') or img.get('data-src')
            if img_url and img_url.startswith('http'):
                # Пропускаем Yandex proxy (кроме img.yandex.ru)
                if 'yandex' not in img_url.lower() or 'img.yandex.ru' in img_url.lower():
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        if 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                            return img_url
        
    except Exception as e:
        print(f"[WARNING] Yandex Images ошибка: {str(e)[:100]}")
    
    return None


def search_real_image(product_name: str, category_name: str = None) -> bytes | None:
    """Ищет реальное изображение товара из различных источников."""
    image_url = None
    source = None
    
    # 1. Пробуем Unsplash API (если есть ключ)
    if not image_url and UNSPLASH_ACCESS_KEY:
        image_url = search_image_unsplash(product_name, category_name)
        if image_url:
            source = "Unsplash API"
    
    # 2. Пробуем Pexels API (если есть ключ)
    if not image_url and PEXELS_API_KEY:
        image_url = search_image_pexels(product_name, category_name)
        if image_url:
            source = "Pexels API"
    
    # 3. Пробуем Google Images (веб-скрапинг, без API ключа)
    if not image_url:
        image_url = search_image_google_images(product_name)
        if image_url:
            source = "Google Images"
    
    # 4. Пробуем Yandex Images (веб-скрапинг, без API ключа)
    if not image_url:
        image_url = search_image_yandex_images(product_name)
        if image_url:
            source = "Yandex Images"
    
    # 5. Пробуем Bing Images (веб-скрапинг, без API ключа)
    if not image_url:
        image_url = search_image_bing_images(product_name)
        if image_url:
            source = "Bing Images"
    
    # Если нашли URL, скачиваем изображение
    if image_url:
        if source:
            print(f"[INFO] Найдено через {source}")
        image_content = download_image_from_url(image_url)
        if image_content:
            # Проверяем размер изображения (должно быть достаточно большим)
            try:
                img = Image.open(io.BytesIO(image_content))
                width, height = img.size
                # Пропускаем слишком маленькие изображения (меньше 200x200)
                if width >= 200 and height >= 200:
                    return image_content
                else:
                    print(f"[WARNING] Изображение слишком маленькое ({width}x{height}), пропускаю")
            except:
                return image_content
    
    return None


def generate_image_locally(product_name: str, category_name: str = None) -> bytes | None:
    """Генерирует изображение локально для товара."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Генерируем цвет на основе названия товара
        colors = [
            (74, 144, 226),   # Синий
            (80, 200, 120),   # Зелёный
            (255, 107, 107),  # Красный
            (255, 165, 0),    # Оранжевый
            (155, 89, 182),   # Фиолетовый
            (231, 76, 60),    # Красный тёмный
            (52, 152, 219),   # Голубой
            (26, 188, 156)    # Бирюзовый
        ]
        color_index = hash(product_name) % len(colors)
        bg_color = colors[color_index]
        
        # Создаём изображение 800x800
        img = Image.new('RGB', (800, 800), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Пробуем использовать системный шрифт
        try:
            # Windows
            font_path = "C:/Windows/Fonts/arial.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/calibri.ttf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 48)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Текст (первые 30 символов)
        text = product_name[:30] if len(product_name) <= 30 else product_name[:27] + "..."
        
        # Получаем размеры текста для центрирования
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Рисуем текст по центру
        position = ((800 - text_width) // 2, (800 - text_height) // 2)
        draw.text(position, text, fill=(255, 255, 255), font=font)
        
        # Сохраняем в bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        img_bytes.seek(0)
        return img_bytes.read()
    except Exception as e:
        print(f"[ERROR] Ошибка генерации изображения для {product_name}: {e}")
        return None


def process_and_save_image(image_content: bytes, product_name: str, base_path: str = "static/img/"):
    """Обрабатывает и сохраняет изображение (small и large версии)."""
    try:
        safe_name = slugify(product_name)
        small_filename = f"{safe_name}_small.jpg"
        large_filename = f"{safe_name}_large.jpg"
        
        small_path = os.path.join(base_path, small_filename)
        large_path = os.path.join(base_path, large_filename)
        
        # Создаём папку, если её нет
        os.makedirs(base_path, exist_ok=True)
        
        # Открываем изображение
        img = Image.open(io.BytesIO(image_content))
        
        # Конвертируем в RGB, если нужно
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Создаём small версию (200x200)
        small_img = img.copy()
        small_img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        small_img.save(small_path, format="JPEG", optimize=True, quality=70)
        
        # Создаём large версию (800x800)
        large_img = img.copy()
        large_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        large_img.save(large_path, format="JPEG", optimize=True, quality=85)
        
        print(f"[OK] Сохранено: {small_filename}, {large_filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка обработки изображения для {product_name}: {e}")
        return False


async def download_images_for_all_products():
    """Скачивает изображения для всех товаров в БД."""
    # Создаём подключение к БД
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Получаем все товары
        products = await ProductsDAO.find_all(session)
        
        print(f"[INFO] Найдено товаров: {len(products)}")
        print("=" * 50)
        
        downloaded = 0
        skipped = 0
        errors = 0
        
        for product in products:
            safe_name = slugify(product.name)
            small_path = f"static/img/{safe_name}_small.jpg"
            large_path = f"static/img/{safe_name}_large.jpg"
            
            # Проверяем, есть ли уже изображения
            FORCE_UPDATE = os.getenv("FORCE_UPDATE_IMAGES", "false").lower() == "true"
            UPDATE_FAILED_ONLY = os.getenv("UPDATE_FAILED_ONLY", "false").lower() == "true"
            
            if os.path.exists(small_path) and os.path.exists(large_path):
                if UPDATE_FAILED_ONLY:
                    # Проверяем размер файла - placeholder обычно меньше 150KB
                    # Реальные фотографии обычно больше
                    large_size = os.path.getsize(large_path)
                    if large_size > 150 * 1024:  # Больше 150KB - вероятно реальное фото
                        print(f"[SKIP] Пропущено (реальное фото найдено): {product.name} ({large_size // 1024}KB)")
                        skipped += 1
                        continue
                    else:
                        print(f"[RETRY] Переищу изображение для: {product.name} (текущий файл {large_size // 1024}KB - вероятно placeholder)")
                elif not FORCE_UPDATE:
                    print(f"[SKIP] Пропущено (уже есть): {product.name}")
                    skipped += 1
                    continue
            
            print(f"[SEARCH] Ищу изображение для: {product.name}")
            
            # Получаем название категории для лучшего поиска
            category_name = None
            if product.category_id:
                category = await CategoriesDAO.find_by_id(session, product.category_id)
                if category:
                    category_name = category.name
            
            # Сначала пытаемся найти реальное изображение
            image_content = search_real_image(product.name, category_name)
            
            # Если не нашли, генерируем placeholder
            if not image_content:
                print(f"[WARNING] Реальное изображение не найдено, создаю placeholder")
                image_content = generate_image_locally(product.name, category_name)
                if not image_content:
                    print(f"[ERROR] Не удалось создать изображение для: {product.name}")
                    errors += 1
                    continue
            
            # Задержка между запросами, чтобы не перегружать серверы
            # Больше задержка для веб-скрапинга, меньше для API
            time.sleep(1.0)
            
            # Обрабатываем и сохраняем
            if process_and_save_image(image_content, product.name):
                downloaded += 1
                # Обновляем БД, если нужно
                if product.small_image != f"{safe_name}_small.jpg" or product.large_image != f"{safe_name}_large.jpg":
                    await ProductsDAO.update(
                        session,
                        product.id,
                        small_image=f"{safe_name}_small.jpg",
                        large_image=f"{safe_name}_large.jpg"
                    )
                    await session.commit()
            else:
                errors += 1
            
            print("-" * 50)
        
        print("=" * 50)
        print(f"[OK] Скачано: {downloaded}")
        print(f"[SKIP] Пропущено: {skipped}")
        print(f"[ERROR] Ошибок: {errors}")
    
    await engine.dispose()


if __name__ == "__main__":
    print("[START] Начинаю скачивание изображений для товаров...")
    print("=" * 50)
    asyncio.run(download_images_for_all_products())
    print("=" * 50)
    print("[DONE] Готово!")

