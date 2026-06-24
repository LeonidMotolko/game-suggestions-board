import re
import pytest

class TestVotes:
    async def test_vote_up(self, client, user_token):
        await client.post("/suggestions/", data={"title": "V", "description": "V"},
                         cookies={"access_token": user_token})
        list_resp = await client.get("/suggestions/")
        ids = re.findall(r'/suggestions/([^"]+)', list_resp.text)
        sug_id = ids[0]
        resp = await client.post(f"/suggestions/{sug_id}/vote", data={"vote_type": "up"},
                                 cookies={"access_token": user_token})
        assert resp.status_code == 200

    async def test_vote_toggle(self, client, user_token):
        await client.post("/suggestions/", data={"title": "VT", "description": "VT"},
                         cookies={"access_token": user_token})
        list_resp = await client.get("/suggestions/")
        ids = re.findall(r'/suggestions/([^"]+)', list_resp.text)
        sug_id = ids[0]
        await client.post(f"/suggestions/{sug_id}/vote", data={"vote_type": "up"}, cookies={"access_token": user_token})
        resp2 = await client.post(f"/suggestions/{sug_id}/vote", data={"vote_type": "up"}, cookies={"access_token": user_token})
        assert resp2.status_code == 200