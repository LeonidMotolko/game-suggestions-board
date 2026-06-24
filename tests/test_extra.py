import pytest

class TestExtra:
    async def test_api_register_json(self, client):
        resp = await client.post("/api/auth/register", json={"email": "api@test.com", "password": "api"})
        assert resp.status_code == 200

    async def test_api_login_json(self, client):
        await client.post("/api/auth/register", json={"email": "api2@test.com", "password": "api2"})
        resp = await client.post("/api/auth/login", json={"email": "api2@test.com", "password": "api2"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_storage_service(self):
        from app.services.storage_service import LocalStorage
        from fastapi import UploadFile
        import io
        storage = LocalStorage(upload_dir="tests/test_uploads")
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))
        path = await storage.upload(file)
        assert "test" in path
        await storage.delete(path)