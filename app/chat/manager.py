import asyncio  # Для создания Task
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set

class ConnectionManager:
    def __init__(self):
        # Храним отдельно клиентов и админов
        self.clients: Dict[int, WebSocket] = {}
        self.admins: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int, is_admin: bool):
        await websocket.accept()
        if is_admin:
            self.admins[user_id] = websocket
            print(f"Admin #{user_id} connected. Total admins: {len(self.admins)}")
        else:
            self.clients[user_id] = websocket
            print(f"Client #{user_id} connected. Total clients: {len(self.clients)}")

    def disconnect(self, user_id: int, is_admin: bool):
        if is_admin:
            if user_id in self.admins:
                del self.admins[user_id]
                print(f"Admin #{user_id} disconnected. Total admins: {len(self.admins)}")
        else:
            if user_id in self.clients:
                del self.clients[user_id]
                print(f"Client #{user_id} disconnected. Total clients: {len(self.clients)}")

    async def send_to_client(self, message: str, client_id: int) -> bool:
        """Отправляет сообщение конкретному клиенту."""
        websocket = self.clients.get(client_id)
        if websocket:
            try:
                await websocket.send_text(message)
                return True  # Успешно отправлено
            except RuntimeError as e:
                # --- УЛУЧШЕННОЕ ЛОГГИРОВАНИЕ ---
                print(f"!!! RuntimeError sending to client {client_id}: {e}. Disconnecting them.")
                # Если отправка не удалась (клиент отключился), удаляем его
                self.disconnect(client_id, is_admin=False)
                return False  # Возвращаем False, т.к. отправка не завершилась
            except Exception as e:
                # Ловим другие возможные ошибки
                print(f"!!! Unexpected error sending to client {client_id}: {e}. Disconnecting them.")
                self.disconnect(client_id, is_admin=False)
                return False
        else:
            # Клиент не найден (возможно, уже отключился)
            print(f"!!! Attempted to send to non-existent client {client_id}")
            return False  # Клиента нет

    async def broadcast_to_admins(self, message: str):
        """Рассылает сообщение всем подключенным админам."""
        if not self.admins:
            return  # Некому отправлять

        # Создаем список задач на отправку
        tasks = [admin_ws.send_text(message) for admin_ws in self.admins.values()]

        # Запускаем отправку параллельно и ждем завершения
        # Мы используем gather с return_exceptions=True, чтобы одна ошибка не сломала все
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Проверяем результаты на наличие ошибок (опционально, для отладки)
        disconnected_admins = []
        for admin_id, result in zip(self.admins.keys(), results):
            if isinstance(result, Exception):
                print(f"!!! Error broadcasting to admin {admin_id}: {result}. Disconnecting them.")
                disconnected_admins.append(admin_id)

        # Удаляем админов, которым не удалось отправить
        for admin_id in disconnected_admins:
            self.disconnect(admin_id, is_admin=True)


# Создаем единственный экземпляр менеджера
manager = ConnectionManager()

