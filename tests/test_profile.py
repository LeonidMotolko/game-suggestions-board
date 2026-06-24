import pytest

class TestProfile:
    async def test_change_password(self, client, user_token):
        resp = await client.post("/profile/change-password", data={"old_password": "testpass", "new_password": "newpass"},
                                 cookies={"access_token": user_token})
        assert resp.status_code == 200

    async def test_change_nickname(self, client, user_token):
        resp = await client.post("/profile/change-nickname", data={"nickname": "CoolUser"},
                                 cookies={"access_token": user_token})
        assert resp.status_code == 200