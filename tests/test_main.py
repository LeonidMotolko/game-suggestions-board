class TestMain:
    async def test_homepage(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        assert "GameSuggest" in response.text

    async def test_static_files(self, client):
        response = await client.get("/static/css/style.css")
        assert response.status_code == 200