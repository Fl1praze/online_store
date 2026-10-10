"""
Создаёт товары по картинкам, которые уже лежат в static/img.

Для каждой пары файлов  <slug>_small.jpg + <slug>_large.jpg  создаётся товар
со slug = <slug>. Название восстанавливается из slug, категория определяется
по ключевым словам, цена / остаток / рейтинг ставятся ПРИБЛИЗИТЕЛЬНО
(детерминированно, зависят только от slug) — их нужно отредактировать в админке.

Скрипт идемпотентен: товары с уже существующим slug пропускаются.

Запуск из корня проекта (с активным .venv):
    python scripts/seed_from_images.py                 # только добавить товары
    python scripts/seed_from_images.py --clean-demo    # + удалить 33 демо-товара из seed_db.py
    python scripts/seed_from_images.py --dry-run       # ничего не писать, только показать итог
"""
import asyncio
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "static" / "img"

# Тестовые «мусорные» картинки из старой разработки — не создаём для них товары
SKIP_SLUGS = {
    "123", "govno", "govno-griba", "grib-daun", "grib-daun123",
    "iphone-govn1o", "iphone-govno", "kakashka", "novyi",
}

# Родительская категория -> подкатегории
CATEGORY_TREE = {
    "Смартфоны и гаджеты": ["Смартфоны", "Планшеты", "Умные часы"],
    "Ноутбуки и компьютеры": ["Ноутбуки"],
    "ТВ и аудио": ["Телевизоры", "Наушники", "Портативные колонки"],
    "Бытовая техника": ["Холодильники", "Пылесосы"],
    "Фото и видео": ["Фотоаппараты", "Экшн-камеры и дроны", "Видеокамеры"],
    "Другое": ["Прочее"],
}

# Порядок важен: первое совпавшее правило выигрывает
CATEGORY_RULES = [
    ("Умные часы", r"watch|mi-band|galaxy-fit|smartwatch"),
    ("Планшеты", r"^ipad|galaxy-tab|matepad|redmi-pad|xiaomi-pad|dexp-tab"),
    ("Портативные колонки", r"^bose-(s1|soundlink)"),
    ("Наушники", r"airpods|^bose-|^jbl-|^sony-(linkbuds|wf-|wh-)|^dexp-(tws|over-ear|noise)"),
    ("Ноутбуки", r"macbook|^dell-|^hp-|^lenovo-|dexp-ixion"),
    ("Телевизоры", r"dexp-tv|^lg-(c3|g3|nano|oled|qned|un|up|uq)|^samsung-(au|frame|qn|tu)|^sony-(bravia|kd-|xr-)|^tcl"),
    ("Холодильники", r"^bosch-|^haier-|^lg-g[lnr]-|^samsung-r[bft]"),
    ("Пылесосы", r"^dyson|^philips-|^redmond-|vacuum|roborock|mi-robot"),
    ("Экшн-камеры и дроны", r"^gopro|^dji-"),
    ("Видеокамеры", r"camcam|handycam|^panasonic-hc|fdr-ax|hdr-cx|pxw|^sony-fx6"),
    ("Фотоаппараты", r"^canon|^nikon|^fujifilm|^panasonic|^sony-(a\d|zv|cyber|rx)|photocam"),
    ("Смартфоны", r"iphone|^galaxy-(s|a|z|note)|^xiaomi-\d|^redmi-(\d|note)|^poco|^huawei-(enjoy|mate-\d|nova|p\d|y7)"),
]

# (мин, макс) цена в рублях по подкатегории — только для заглушек
PRICE_RANGE = {
    "Смартфоны": (15000, 120000), "Планшеты": (12000, 110000),
    "Умные часы": (3000, 60000), "Ноутбуки": (40000, 250000),
    "Телевизоры": (20000, 300000), "Наушники": (2000, 40000),
    "Портативные колонки": (8000, 25000), "Холодильники": (30000, 120000),
    "Пылесосы": (8000, 70000), "Фотоаппараты": (30000, 350000),
    "Экшн-камеры и дроны": (15000, 120000), "Видеокамеры": (15000, 300000),
    "Прочее": (3000, 30000),
}

BRANDS = {
    "iphone": "iPhone", "ipad": "iPad", "macbook": "MacBook", "airpods": "AirPods",
    "dexp": "DEXP", "hp": "HP", "lg": "LG", "tcl": "TCL", "jbl": "JBL", "dji": "DJI",
    "gopro": "GoPro", "tws": "TWS", "tv": "TV", "anc": "ANC", "uhd": "UHD",
    "qled": "QLED", "led": "LED", "oled": "OLED", "qned": "QNED", "hd": "HD",
    "xps": "XPS", "poco": "POCO", "ii": "II", "iii": "III", "iv": "IV", "se": "SE",
    "bravia": "Bravia", "powershot": "PowerShot", "eos": "EOS", "lumix": "Lumix",
    "coolpix": "Coolpix", "handycam": "Handycam", "cyber": "Cyber", "shot": "Shot",
    "thinkpad": "ThinkPad", "ideapad": "IdeaPad", "elitebook": "EliteBook",
    "zbook": "ZBook", "matepad": "MatePad", "magsafe": "MagSafe", "ixion": "IXION",
    "camcam": "CamCam", "photocam": "PhotoCam", "soundlink": "SoundLink",
    "quietcomfort": "QuietComfort", "quietcontrol": "QuietControl",
    "linkbuds": "LinkBuds", "linkbuds-s": "LinkBuds S", "mi": "Mi", "x": "X",
}
CAPITALIZE = {
    "pro", "max", "ultra", "mini", "air", "plus", "lite", "fit", "watch", "pad",
    "tab", "active", "classic", "black", "white", "mark", "gaming", "business",
    "action", "noise", "cancelling", "over", "ear", "smart", "smartwatch", "color",
    "galaxy", "note", "flip", "fold", "xiaomi", "samsung", "apple", "sony", "canon",
    "nikon", "dell", "lenovo", "huawei", "bose", "haier", "bosch", "philips",
    "redmond", "dyson", "redmi", "panasonic", "fujifilm", "frame", "series",
    "legion", "yoga", "slim", "dragonfly", "envy", "omen", "pavilion", "spectre",
    "victus", "latitude", "precision", "vostro", "inspiron", "alienware",
    "headphones", "sport", "open", "earbuds", "micro", "vacuum", "cleaner", "robot",
    "mop", "expert", "speedpro", "powerpro", "aqua", "with", "charging", "case",
    "hermes", "nike", "nova", "mate", "enjoy", "paper", "cordless", "omni", "glide",
    "animal", "absolute", "detect", "slim", "session", "avata", "osmo", "mobile",
    "pocket", "hero", "instax", "dragon", "rebel", "carbon", "studio",
}


def classify(slug: str) -> str:
    for sub, pattern in CATEGORY_RULES:
        if re.search(pattern, slug):
            return sub
    return "Прочее"


def prettify(slug: str) -> str:
    parts = []
    for token in slug.split("-"):
        low = token.lower()
        if low in BRANDS:
            parts.append(BRANDS[low])
        elif low in CAPITALIZE:
            parts.append(low.capitalize())
        elif any(ch.isdigit() for ch in token):
            parts.append(token.upper())
        elif len(token) <= 3:
            parts.append(token.upper())
        else:
            parts.append(token.capitalize())
    return " ".join(parts)


def _frac(slug: str, salt: str) -> float:
    h = hashlib.md5((salt + slug).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def fake_price(slug: str, sub: str) -> int:
    lo, hi = PRICE_RANGE[sub]
    value = lo + (hi - lo) * (_frac(slug, "p") ** 1.4)
    return int(round(value / 1000) * 1000 - 10) if value > 2000 else int(round(value))


def fake_stock(slug: str) -> int:
    return 3 + int(_frac(slug, "s") * 47)


def fake_rating(slug: str) -> float:
    return round(4.0 + _frac(slug, "r") * 0.9, 1)


def find_slugs() -> list[str]:
    if not IMG_DIR.is_dir():
        raise SystemExit(f"Папка {IMG_DIR} не найдена. Запускайте из корня проекта.")
    small = {p.name[: -len("_small.jpg")] for p in IMG_DIR.glob("*_small.jpg")}
    large = {p.name[: -len("_large.jpg")] for p in IMG_DIR.glob("*_large.jpg")}
    return sorted((small & large) - SKIP_SLUGS)


async def seed(clean_demo: bool, dry_run: bool) -> None:
    # Тяжёлые импорты — только здесь, чтобы функции выше можно было тестировать отдельно
    from slugify import slugify
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    sys.path.insert(0, str(ROOT))
    from app.config import settings
    from app.category.models import Category
    from app.products.models import Product
    from app.users.models import Users  # noqa: F401
    from app.orders.models import Order, OrderItem  # noqa: F401
    from app.cart.models import Cart, CartItem  # noqa: F401
    from app.review.models import Review  # noqa: F401
    from app.chat.models import ChatMessage  # noqa: F401
    from scripts.seed_db import PRODUCTS as DEMO_PRODUCTS

    demo_slugs = {slugify(p[1]) for p in DEMO_PRODUCTS}
    slugs = [s for s in find_slugs() if s not in demo_slugs]

    print(f"БД: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"Пар картинок в static/img (без демо и тестовых): {len(slugs)}")

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        if clean_demo:
            res = await session.execute(delete(Product).where(Product.slug.in_(demo_slugs)))
            print(f"Удалено демо-товаров: {res.rowcount}")

        # Категории
        sub_ids: dict[str, int] = {}
        for parent_name, children in CATEGORY_TREE.items():
            parent = await session.scalar(select(Category).where(Category.slug == slugify(parent_name)))
            if not parent:
                parent = Category(name=parent_name, slug=slugify(parent_name), is_active=True)
                session.add(parent)
                await session.flush()
            for child_name in children:
                child = await session.scalar(select(Category).where(Category.slug == slugify(child_name)))
                if not child:
                    child = Category(name=child_name, slug=slugify(child_name),
                                     is_active=True, parent_id=parent.id)
                    session.add(child)
                    await session.flush()
                sub_ids[child_name] = child.id

        # Товары
        existing = set((await session.scalars(select(Product.slug))).all())
        added, per_cat = 0, {}
        for slug in slugs:
            if slug in existing:
                continue
            sub = classify(slug)
            name = prettify(slug)
            session.add(Product(
                name=name,
                slug=slug,
                description=f"{name}. Описание будет уточнено.",
                price=fake_price(slug, sub),
                stock=fake_stock(slug),
                rating=fake_rating(slug),
                is_active=True,
                category_id=sub_ids[sub],
                small_image=f"{slug}_small.jpg",
                large_image=f"{slug}_large.jpg",
            ))
            per_cat[sub] = per_cat.get(sub, 0) + 1
            added += 1

        if dry_run:
            await session.rollback()
            print("\n[dry-run] В БД ничего не записано.")
        else:
            await session.commit()
    await engine.dispose()

    print(f"\nДобавлено товаров: {added}")
    for sub, n in sorted(per_cat.items(), key=lambda x: -x[1]):
        print(f"  {sub}: {n}")
    print("\nВАЖНО: цены, остатки и рейтинги — заглушки. Отредактируйте их в админке.")


if __name__ == "__main__":
    asyncio.run(seed(clean_demo="--clean-demo" in sys.argv, dry_run="--dry-run" in sys.argv))