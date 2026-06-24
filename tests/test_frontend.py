class TestFrontend:
    async def test_login_page(self, client):
        resp = await client.get("/auth/login-page")
        assert resp.status_code == 200
        assert "form" in resp.text

    async def test_register_page(self, client):
        resp = await client.get("/auth/register-page")
        assert resp.status_code == 200
        assert "Регистрация" in resp.text

    async def test_admin_dashboard_page(self, client, admin_token):
        resp = await client.get("/admin/dashboard", cookies={"access_token": admin_token})
        assert resp.status_code == 200
        assert "Статистика" in resp.text or "Админ" in resp.text