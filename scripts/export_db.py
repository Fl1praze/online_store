"""
Скрипт для экспорта данных из локальной БД в SQL файл
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings

async def export_database():
    """Экспортирует данные из БД в SQL файл"""
    # Используем синхронный движок для pg_dump
    sync_url = settings.DATABASE_URL.replace('+asyncpg', '')
    engine = create_engine(sync_url)
    
    print(f"Подключение к БД: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    # Получаем список всех таблиц
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]
    
    print(f"Найдено таблиц: {len(tables)}")
    print(f"Таблицы: {', '.join(tables)}")
    
    # Экспортируем данные
    output_file = "database_export.sql"
    print(f"\nЭкспорт данных в {output_file}...")
    
    import subprocess
    cmd = [
        'pg_dump',
        '-h', settings.DB_HOST,
        '-p', str(settings.DB_PORT),
        '-U', settings.DB_USER,
        '-d', settings.DB_NAME,
        '--data-only',  # Только данные, без схемы
        '--inserts',    # Использовать INSERT вместо COPY
        '-f', output_file
    ]
    
    # Устанавливаем пароль через переменную окружения
    env = os.environ.copy()
    env['PGPASSWORD'] = settings.DB_PASS
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"✅ Данные успешно экспортированы в {output_file}")
        print(f"Размер файла: {os.path.getsize(output_file) / 1024:.2f} KB")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка экспорта: {e}")
        print("\nУбедитесь, что pg_dump установлен и доступен в PATH")
    except FileNotFoundError:
        print("❌ pg_dump не найден. Установите PostgreSQL client tools.")

if __name__ == "__main__":
    asyncio.run(export_database())

