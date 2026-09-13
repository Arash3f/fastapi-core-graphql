import pytest


async def _gql(
    client, query: str, variables: dict | None = None, token: str | None = None
):
    headers = {"User-Agent": "e2e-test-agent"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = await client.post(
        "/graphql",
        json={"query": query, "variables": variables or {}},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_introspection(client):
    body = await _gql(client, "{ __typename }")
    assert body["data"]["__typename"] == "Query"


@pytest.mark.asyncio
async def test_graphql_login(client):
    query = """
    mutation Login($input: LoginInput!) {
      login(input: $input) {
        accessToken
        refreshToken
      }
    }
    """
    body = await _gql(
        client,
        query,
        {"input": {"username": "admin", "password": "admin"}},
    )
    assert not body.get("errors"), body
    assert body["data"]["login"]["accessToken"]


@pytest.mark.asyncio
async def test_graphql_me_and_refresh(client):
    login_query = """
    mutation Login($input: LoginInput!) {
      login(input: $input) { accessToken refreshToken }
    }
    """
    login = await _gql(
        client,
        login_query,
        {"input": {"username": "admin", "password": "admin"}},
    )
    tokens = login["data"]["login"]

    me = await _gql(
        client,
        "{ me { username role } }",
        token=tokens["accessToken"],
    )
    assert not me.get("errors"), me
    assert me["data"]["me"]["username"] == "admin"

    refresh_query = """
    mutation Refresh($input: RefreshTokenInput!) {
      refreshToken(input: $input) { accessToken }
    }
    """
    refreshed = await _gql(
        client,
        refresh_query,
        {"input": {"refreshToken": tokens["refreshToken"]}},
    )
    assert not refreshed.get("errors"), refreshed
    assert refreshed["data"]["refreshToken"]["accessToken"]


@pytest.mark.asyncio
async def test_graphql_create_user(client):
    login = await _gql(
        client,
        """
        mutation Login($input: LoginInput!) {
          login(input: $input) { accessToken }
        }
        """,
        {"input": {"username": "admin", "password": "admin"}},
    )
    token = login["data"]["login"]["accessToken"]

    create = await _gql(
        client,
        """
        mutation Create($input: CreateUserInput!) {
          createUser(input: $input) { username role }
        }
        """,
        {
            "input": {
                "name": "E2E User",
                "username": "e2e_gql_user",
                "password": "password123",
                "role": "Member",
            }
        },
        token=token,
    )
    assert not create.get("errors"), create
    assert create["data"]["createUser"]["username"] == "e2e_gql_user"
