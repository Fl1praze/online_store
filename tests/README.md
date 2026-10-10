# Selenium Тесты

Этот проект использует **Selenium** для автоматизированного тестирования пользовательского интерфейса (UI) через реальный браузер.

## 🎯 Что такое Selenium?

**Selenium** — это инструмент для автоматизации браузера. Он позволяет:
- Открывать веб-страницы в реальном браузере (Chrome, Firefox, Edge)
- Взаимодействовать с элементами страницы (клики, ввод текста, заполнение форм)
- Проверять наличие элементов, текст, стили
- Тестировать реальное поведение пользователя

### Как это работает?

1. **WebDriver** — управляет браузером
   - Selenium использует WebDriver API для управления браузером
   - WebDriver отправляет команды браузеру (открыть страницу, кликнуть, ввести текст)
   - Браузер выполняет команды и возвращает результаты

2. **Элементы страницы** — поиск и взаимодействие
   - Находим элементы по ID, классу, тегу, XPath, CSS селектору
   - Взаимодействуем: клик, ввод текста, выбор из списка
   - Проверяем: наличие, текст, атрибуты, видимость

3. **Ожидания (Waits)** — ждем загрузки элементов
   - Страницы загружаются асинхронно
   - Используем `WebDriverWait` для ожидания появления элементов
   - Избегаем ошибок "элемент не найден"

## 📦 Установка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

Это установит:
- `selenium` — библиотека для автоматизации браузера
- `webdriver-manager` — автоматически скачивает драйвер браузера
- `pytest` — фреймворк для запуска тестов

### 2. Установите Chrome браузер

Selenium тесты используют Chrome. Убедитесь, что Chrome установлен:
- Windows: скачайте с [google.com/chrome](https://www.google.com/chrome/)
- Linux: `sudo apt-get install google-chrome-stable`
- Mac: скачайте с официального сайта

**Примечание**: `webdriver-manager` автоматически скачает ChromeDriver, вам не нужно делать это вручную!

## 🚀 Запуск тестов

### Перед запуском тестов

**Важно**: Убедитесь, что приложение запущено!

```bash
# В одном терминале запустите приложение
uvicorn main:app --reload

# В другом терминале запустите тесты
pytest tests/
```

### Запуск всех тестов

```bash
pytest tests/
```

### Запуск конкретного файла

```bash
pytest tests/test_shop_ui.py
```

### Запуск с подробным выводом

```bash
pytest tests/ -v
```

### Запуск с выводом print-ов

```bash
pytest tests/ -s
```

### Запуск в headless режиме (без открытия браузера)

Отредактируйте `tests/conftest.py` и раскомментируйте строку:
```python
chrome_options.add_argument("--headless")
```

## 📝 Структура тестов

```
tests/
├── conftest.py          # Настройки и фикстуры (driver, base_url)
├── test_shop_ui.py      # Тесты UI магазина
└── README.md            # Этот файл
```

### conftest.py

Содержит общие настройки:
- `driver` — фикстура для создания WebDriver
- `base_url` — базовый URL приложения (http://localhost:8000)

### test_shop_ui.py

Содержит тесты:
- `TestShopUI` — тесты главной страницы
- `TestRegistration` — тесты регистрации
- `TestLogin` — тесты входа
- `TestProductCatalog` — тесты каталога

## 🔍 Примеры использования Selenium

### Поиск элементов

```python
# По ID
element = driver.find_element(By.ID, "username")

# По классу
element = driver.find_element(By.CLASS_NAME, "btn-primary")

# По тегу
element = driver.find_element(By.TAG_NAME, "button")

# По CSS селектору
element = driver.find_element(By.CSS_SELECTOR, "input[type='email']")

# По XPath
element = driver.find_element(By.XPATH, "//button[@class='submit']")
```

### Взаимодействие с элементами

```python
# Клик
button = driver.find_element(By.ID, "submit")
button.click()

# Ввод текста
input_field = driver.find_element(By.ID, "email")
input_field.send_keys("user@example.com")

# Очистка поля
input_field.clear()

# Получение текста
text = element.text

# Получение атрибута
value = element.get_attribute("value")
```

### Ожидание элементов

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)  # Ждем до 10 секунд

# Ждем появления элемента
element = wait.until(
    EC.presence_of_element_located((By.ID, "username"))
)

# Ждем кликабельности
button = wait.until(
    EC.element_to_be_clickable((By.ID, "submit"))
)

# Ждем видимости
element = wait.until(
    EC.visibility_of_element_located((By.ID, "message"))
)
```

### Навигация

```python
# Переход на страницу
driver.get("http://localhost:8000/login")

# Назад
driver.back()

# Вперед
driver.forward()

# Обновить
driver.refresh()

# Текущий URL
current_url = driver.current_url

# Заголовок страницы
title = driver.title
```

## 🎨 Преимущества Selenium тестов

✅ **Реальное тестирование** — тестируем как настоящий пользователь  
✅ **Визуальная проверка** — видим, что происходит в браузере  
✅ **Интеграционное тестирование** — проверяем весь стек (UI + Backend)  
✅ **Автоматизация** — не нужно вручную проверять каждую страницу  
✅ **Регрессионное тестирование** — находим баги при изменениях  

## ⚠️ Важные моменты

1. **Приложение должно быть запущено** перед запуском тестов
2. **Chrome должен быть установлен** (webdriver-manager скачает драйвер автоматически)
3. **Тесты могут быть медленными** — браузер открывается реально
4. **Headless режим** ускоряет тесты, но не показывает визуально что происходит

## 🐛 Отладка тестов

### Сохранить скриншот при ошибке

Добавьте в тест:
```python
def test_example(self, driver, base_url):
    try:
        driver.get(base_url)
        # ваш тест
    except Exception as e:
        driver.save_screenshot("error.png")
        raise
```

### Замедлить выполнение (для наблюдения)

```python
import time
time.sleep(2)  # Пауза 2 секунды
```

### Вывести HTML страницы

```python
print(driver.page_source)
```

## 📚 Дополнительные ресурсы

- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Pytest Documentation](https://docs.pytest.org/)
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager)

---

**Примечание**: Эти тесты проверяют UI, а не логику приложения. Для тестирования логики используйте unit-тесты.

