import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from app.config import settings

class StorageInterface(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile) -> str:
        """Загружает файл и возвращает путь/URL"""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Удаляет файл"""
        pass

class LocalStorage(StorageInterface):
    def __init__(self, upload_dir: str = None):
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile) -> str:
        ext = os.path.splitext(file.filename or "file")[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = self.upload_dir / unique_name
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        return str(file_path)

    async def delete(self, path: str) -> bool:
        full_path = Path(path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

# Factory for dependency injection
def get_storage() -> StorageInterface:
    return LocalStorage()
