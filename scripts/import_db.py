"""
Скрипт для импорта данных из SQL файла в Docker БД
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

def import_to_docker():
    """Импортирует данные из SQL файла в Docker БД"""
    sql_file = "database_export.sql"
    
    if not os.path.exists(sql_file):
        print(f"❌ Файл {sql_file} не найден!")
        print("Сначала выполните: python scripts/export_db.py")
        return
    
    print(f"Импорт данных из {sql_file} в Docker БД...")
    
    import subprocess
    
    # Параметры подключения к Docker БД
    db_host = "localhost"  # или "db" если запускать из контейнера
    db_port = "5432"
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "postgres")
    db_name = os.getenv("DB_NAME", "online_store")
    
    cmd = [
        'psql',
        '-h', db_host,
        '-p', db_port,
        '-U', db_user,
        '-d', db_name,
        '-f', sql_file
    ]
    
    # Устанавливаем пароль через переменную окружения
    env = os.environ.copy()
    env['PGPASSWORD'] = db_pass
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print("✅ Данные успешно импортированы в Docker БД")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("\nУбедитесь, что:")
        print("1. Docker контейнер с БД запущен: docker-compose up -d db")
        print("2. psql установлен и доступен в PATH")
    except FileNotFoundError:
        print("❌ psql не найден. Установите PostgreSQL client tools.")

if __name__ == "__main__":
    import_to_docker()

