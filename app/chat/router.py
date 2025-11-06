import json
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Request,
    status
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession  # <-- Добавили AsyncSession
from app.database import get_async_session  # <-- Добавили зависимость сессии
from app.chat.manager import manager
from app.users.models import Users
# Убедись, что V2/V3 здесь верное и импортируется правильно
from app.users.dependencies import get_current_user
from app.chat.dependencies import get_user_from_ws_token
from app.users.auth import create_websocket_token
from app.chat.dao import ChatMessageDAO
import os


# --- Настройка Jinja2 ---
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_path = os.path.join(base_dir, "templates")
if not os.path.isdir(templates_path):
    print(f"ОШИБКА: Папка шаблонов не найдена по пути: {templates_path}")

templates = Jinja2Templates(directory=templates_path)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/page")
async def get_chat_page(
        request: Request,
        user: Users = Depends(get_current_user)
):

    ws_token = create_websocket_token(user_id=user.id)
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "user": user, "ws_token": ws_token}
    )


@router.websocket("/ws")#Разобраться в работе
async def websocket_endpoint(
        websocket: WebSocket,
        user: Users = Depends(get_user_from_ws_token),
        session: AsyncSession = Depends(get_async_session)
):

    await manager.connect(websocket, user_id=user.id, is_admin=user.is_admin)
    broadcast_message = f"{'Админ' if user.is_admin else 'Клиент'} #{user.id} ({user.username}) вошел в чат"
    await manager.broadcast_to_admins(broadcast_message)

    # --- ЗАГРУЗКА ИСТОРИИ ---
    if not user.is_admin:
        await manager.send_to_client(f"Вы #{user.id}. Ожидайте ответа поддержки.", user.id)
        try:
            history = await ChatMessageDAO.get_history_for_client(session, user.id, n=50)
            await session.commit()
            for msg in history:
                if msg.is_admin_message:
                    prefix = "Поддержка: "
                else:
                    prefix = f"Вы ({msg.timestamp.strftime('%H:%M')}): "
                await websocket.send_text(prefix + msg.message)
            print(f"History loaded for client {user.id}")
        except Exception as e:
            print(f"Error loading history for user {user.id}: {e}")
            await session.rollback()
            await websocket.send_text("Не удалось загрузить историю сообщений.")
    else:
        await websocket.send_text("Вы подключены как админ.")
    try:
        while True:
            data = await websocket.receive_text()
            # --- Логика сохранения сообщений ---
            try:
                async with session.begin():
                    if user.is_admin:
                        try:
                            payload = json.loads(data)
                            recipient_id_str = payload.get("recipient_id")
                            text = payload.get("text")

                            if not recipient_id_str or text is None:
                                await websocket.send_text(
                                    "Ошибка: JSON должен содержать 'recipient_id' (число) и 'text' (строка).")
                                continue

                            recipient_id = int(recipient_id_str)  # Может вызвать ValueError

                            await ChatMessageDAO.add(
                                session=session,
                                sender_id=user.id,
                                recipient_id=recipient_id,
                                message=text,
                                is_admin_message=True
                            )
                            #----------------------------------------------------- Понять че как делается/______________________________________________
                            await websocket.send_text(f"Вы (клиенту #{recipient_id}): {text}")
                            success = await manager.send_to_client(f"Поддержка: {text}", recipient_id)
                            # ... (обработка success из предыдущей версии) ...
                            if not success and recipient_id in manager.clients:
                                await websocket.send_text(
                                    f"Предупреждение: Не удалось отправить сообщение клиенту #{recipient_id}. Возможно, он не в сети.")
                            elif not success:
                                await websocket.send_text(f"Информация: Клиент #{recipient_id} отключился.")


                        except (json.JSONDecodeError, ValueError) as e:
                            # Не сохраняем, просто отправляем ошибку админу
                            error_msg = "Ошибка: Админы должны отправлять JSON." if isinstance(e,
                                                                                               json.JSONDecodeError) else "Ошибка: 'recipient_id' должен быть числом."
                            await websocket.send_text(error_msg)
                            continue  # Переходим к следующей итерации while
                        except Exception as e_json_proc:  # Ловим другие ошибки обработки JSON
                            print(f"Error processing admin message OUTSIDE save: {e_json_proc}")
                            await websocket.send_text("Произошла ошибка при обработке вашего сообщения.")
                            continue  # Не сохраняем, если JSON неверный

                    else:
                        # Клиент отправляет просто текст
                        # Сохраняем сообщение клиента в БД
                        await ChatMessageDAO.add(
                            session=session,
                            sender_id=user.id,
                            recipient_id=None,  # Сообщение всем админам
                            message=data,
                            is_admin_message=False
                        )
                        # Отправляем сообщение себе и админам (уже после сохранения)
                        await websocket.send_text(f"Вы: {data}")
                        await manager.broadcast_to_admins(f"Клиент #{user.id} ({user.username}): {data}")

                # Конец блока 'async with session.begin()' - commit или rollback произошел

            except Exception as e_save:  # Ловим ошибки ИМЕННО при сохранении в БД
                print(f"!!! Database Error saving message for user {user.id}: {e_save}")
                # Важно откатить сессию, если begin() не смог этого сделать
                try:
                    await session.rollback()
                except Exception as e_rb:
                    print(f"Error during rollback: {e_rb}")
                # Сообщаем пользователю об ошибке сохранения
                await websocket.send_text("Ошибка: Не удалось сохранить ваше сообщение.")
                # Продолжаем работу чата, не отключая пользователя
                continue

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user {user.id}")
        manager.disconnect(user_id=user.id, is_admin=user.is_admin)
        broadcast_message = f"{'Админ' if user.is_admin else 'Клиент'} #{user.id} ({user.username}) покинул чат"
        await manager.broadcast_to_admins(broadcast_message)
        # Окончательно коммитим сессию при отключении, на всякий случай
        try:
            await session.commit()
        except Exception:
            await session.rollback()
    except Exception as e:
        print(f"!!! WebSocket Error for user {user.id}: {e}")
        manager.disconnect(user_id=user.id, is_admin=user.is_admin)
        broadcast_message = f"{'Админ' if user.is_admin else 'Клиент'} #{user.id} ({user.username}) отключился из-за ошибки"
        await manager.broadcast_to_admins(broadcast_message)
        # Откатываем сессию при любой другой ошибке
        try:
            await session.rollback()
        except Exception:
            pass
        # Закрываем WebSocket
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=f"Server error: {e}")
        except RuntimeError:
            pass
        except Exception as close_exc:
            print(f"Error trying to close WebSocket for user {user.id}: {close_exc}")
    finally:
        # Важно закрыть сессию SQLAlchemy, когда WebSocket соединение завершается
        # Это делается автоматически благодаря `finally` в `get_async_session`
        print(f"Session for user {user.id} should be closed by get_async_session.")
