import pytest

class TestAuth:
    async def test_register(self, client):
        response = await client.post("/auth/register", data={"email": "new@test.com", "password": "pass123"})
        assert response.status_code == 303  # редирект

    async def test_register_existing(self, client):
        response = await client.post("/auth/register", data={"email": "admin@test.com", "password": "pass"})
        assert response.status_code == 400

    async def test_login(self, client):
        response = await client.post("/auth/login", data={"email": "admin@test.com", "password": "admin123"})
        assert response.status_code == 303

    async def test_login_bad(self, client):
        response = await client.post("/auth/login", data={"email": "admin@test.com", "password": "wrong"})
        assert response.status_code == 401

    async def test_logout(self, client):
        response = await client.get("/auth/logout")
        assert response.status_code == 303