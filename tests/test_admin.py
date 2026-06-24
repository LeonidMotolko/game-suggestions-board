import re
import pytest

class TestAdmin:
    async def test_dashboard(self, client, admin_token):
        response = await client.get("/admin/dashboard", cookies={"access_token": admin_token})
        assert response.status_code == 200

    async def test_manage_suggestions(self, client, admin_token):
        response = await client.get("/admin/suggestions", cookies={"access_token": admin_token})
        assert response.status_code == 200

    async def test_change_status_and_delete(self, client, admin_token, user_token):
        await client.post("/suggestions/", data={"title": "S1", "description": "D1"},
                         cookies={"access_token": user_token})
        list_resp = await client.get("/suggestions/")
        ids = re.findall(r'/suggestions/([^"]+)', list_resp.text)
        sug_id = ids[0]
        status_resp = await client.post(f"/admin/suggestions/{sug_id}/status", data={"status": "reviewed"},
                                        cookies={"access_token": admin_token})
        assert status_resp.status_code == 303
        del_resp = await client.post(f"/admin/suggestions/{sug_id}/delete",
                                     cookies={"access_token": admin_token})
        assert del_resp.status_code == 303

    async def test_ban_user(self, client, admin_token):
        await client.post("/auth/register", data={"email": "banme@test.com", "password": "pass"})
        resp = await client.get("/admin/users", cookies={"access_token": admin_token})
        user_ids = re.findall(r'/admin/users/([^"]+)/ban', resp.text)
        ban_id = user_ids[0]
        ban_resp = await client.post(f"/admin/users/{ban_id}/ban", cookies={"access_token": admin_token})
        assert ban_resp.status_code == 303