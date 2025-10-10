from app.celery_app import celery_app
from app.users.verif_email import  send_verification_email
from PIL import Image
import io
import os
from slugify import slugify
from app.products.dao import ProductsDAO

@celery_app.task
def send_verification_email_task(email: str, token: str):
    """
    Отправляет письмо с подтверждением email
    """
    send_verification_email(email, token)


@celery_app.task
def process_product_images_task(
    small_image_content: bytes,
    large_image_content: bytes,
    name: str,
    base_path: str = "static/img/"
) -> dict:
    """
    Обрабатывает и сохраняет два изображения: маленькое и большое.
    Возвращает словарь с путями.
    """
    safe_name = slugify(name)
    small_filename = f"{safe_name}_small.jpg"
    large_filename = f"{safe_name}_large.jpg"

    small_path = os.path.join(base_path, small_filename)
    large_path = os.path.join(base_path, large_filename)

    small_img = Image.open(io.BytesIO(small_image_content))
    small_img.thumbnail((200, 200))
    small_img.save(small_path, format="JPEG", optimize=True, quality=70)

    large_img = Image.open(io.BytesIO(large_image_content))
    large_img.thumbnail((800, 800))
    large_img.save(large_path, format="JPEG", optimize=True, quality=85)

    return {
        "small_image_url": f"/static/img/{small_filename}",
        "large_image_url": f"/static/img/{large_filename}"
    }
