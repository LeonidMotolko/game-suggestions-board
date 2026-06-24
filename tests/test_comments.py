import re
import pytest

class TestComments:
    async def test_add_comment(self, client, user_token):
        await client.post("/suggestions/", data={"title": "C", "description": "D"},
                         cookies={"access_token": user_token})
        list_resp = await client.get("/suggestions/")
        ids = re.findall(r'/suggestions/([^"]+)', list_resp.text)
        sug_id = ids[0]
        resp = await client.post(f"/suggestions/{sug_id}/comments", data={"text": "Cool idea"},
                                 cookies={"access_token": user_token})
        assert resp.status_code == 303

    async def test_delete_comment(self, client, user_token, admin_token):
        await client.post("/suggestions/", data={"title": "C", "description": "D"},
                         cookies={"access_token": user_token})
        list_resp = await client.get("/suggestions/")
        ids = re.findall(r'/suggestions/([^"]+)', list_resp.text)
        sug_id = ids[0]
        await client.post(f"/suggestions/{sug_id}/comments", data={"text": "Del me"},
                         cookies={"access_token": user_token})
        detail = await client.get(f"/suggestions/{sug_id}")
        comment_ids = re.findall(r'/suggestions/\w+/comments/([^"]+)/delete', detail.text)
        c_id = comment_ids[0]
        resp = await client.post(f"/suggestions/{sug_id}/comments/{c_id}/delete",
                                 cookies={"access_token": user_token})
        assert resp.status_code == 303