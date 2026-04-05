import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_status_endpoint(client: AsyncClient):
    response = await client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "components" in data


@pytest.mark.asyncio
async def test_list_connections_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/broker/connections")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/broker/connections", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_positions_empty(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/broker/positions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_transactions_empty(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/broker/transactions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_account_summary_empty(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/broker/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["positions_count"] == 0
    assert data["total_value"] == 0


@pytest.mark.asyncio
async def test_csv_template_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/broker/csv/template")
    assert response.status_code == 200
    data = response.json()
    assert "template" in data
    assert "symbol" in data["required_columns"]
    assert "quantity" in data["required_columns"]
    assert "average_cost" in data["required_columns"]


@pytest.mark.asyncio
async def test_csv_connect(client: AsyncClient, auth_headers):
    csv_content = """symbol,name,quantity,average_cost,current_price,asset_type
AAPL,Apple Inc,10,150.00,175.50,stock
NVDA,NVIDIA Corp,5,450.00,890.00,stock"""

    response = await client.post(
        "/api/v1/broker/connect/csv",
        json={
            "csv_content": csv_content,
            "cash_balance": 5000.0,
            "filename": "test_portfolio.csv",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["broker_type"] == "csv"
    assert data["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_csv_connect_then_positions(client: AsyncClient, auth_headers):
    csv_content = """symbol,name,quantity,average_cost,current_price,asset_type
MSFT,Microsoft,8,350.00,420.00,stock
GOOGL,Alphabet,3,140.00,170.00,stock"""

    await client.post(
        "/api/v1/broker/connect/csv",
        json={"csv_content": csv_content, "cash_balance": 2000.0},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/broker/positions", headers=auth_headers)
    assert response.status_code == 200
    positions = response.json()
    assert len(positions) >= 2

    symbols = [p["symbol"] for p in positions]
    assert "MSFT" in symbols
    assert "GOOGL" in symbols

    msft = next(p for p in positions if p["symbol"] == "MSFT")
    assert msft["quantity"] == 8
    assert msft["average_cost"] == 350.00
    assert msft["market_value"] == 8 * 420.00


@pytest.mark.asyncio
async def test_csv_connect_invalid(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/broker/connect/csv",
        json={"csv_content": "bad,data\n1,2", "cash_balance": 0},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_disconnect_nonexistent(client: AsyncClient, auth_headers):
    response = await client.delete("/api/v1/broker/connections/9999", headers=auth_headers)
    assert response.status_code == 502
