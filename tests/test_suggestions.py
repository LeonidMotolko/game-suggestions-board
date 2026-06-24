import pytest

class TestSuggestions:
    async def test_create_suggestion(self, client, user_token):
        response = await client.post("/suggestions/", data={"title": "Test", "description": "Desc"},
                                      cookies={"access_token": user_token})
        assert response.status_code == 303

    async def test_create_suggestion_no_auth(self, client):
        response = await client.post("/suggestions/", data={"title": "T", "description": "D"})
        assert response.status_code == 401

    async def test_list_suggestions(self, client, user_token):
        await client.post("/suggestions/", data={"title": "T", "description": "D"},
                         cookies={"access_token": user_token})
        response = await client.get("/suggestions/")
        assert response.status_code == 200

    async def test_search(self, client, user_token):
        await client.post("/suggestions/", data={"title": "Gameplay", "description": "Ideas"},
                         cookies={"access_token": user_token})
        response = await client.get("/?search=Gameplay")
        assert response.status_code == 200