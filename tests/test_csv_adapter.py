import pytest
from app.broker_integrations.csv_adapter import CSVImportAdapter
from app.utils.exceptions import CSVParseError, BrokerAuthenticationError


VALID_CSV = """symbol,name,quantity,average_cost,current_price,purchase_date,asset_type,sector
AAPL,Apple Inc,10,150.00,175.50,2024-01-15,stock,Technology
NVDA,NVIDIA Corp,5,450.00,890.00,2024-03-01,stock,Technology
VTI,Vanguard Total Stock Market ETF,20,220.00,235.00,2023-06-15,etf,
QQQ,Invesco QQQ Trust,8,380.00,445.00,2024-02-01,etf,
BTC,Bitcoin,0.5,42000.00,68000.00,2024-01-01,crypto,"""

MINIMAL_CSV = """symbol,quantity,average_cost
AAPL,10,150.00
MSFT,5,400.00"""

INVALID_CSV_MISSING_COLUMNS = """name,quantity,price
Apple,10,150.00"""

INVALID_CSV_BAD_DATA = """symbol,quantity,average_cost
AAPL,-5,150.00
MSFT,0,400.00"""


@pytest.mark.asyncio
async def test_csv_authenticate_valid():
    adapter = CSVImportAdapter()
    result = await adapter.authenticate({
        "csv_content": VALID_CSV,
        "cash_balance": 5000.0,
        "filename": "test.csv",
    })
    assert result["status"] == "connected"
    assert result["broker"] == "csv"
    assert result["positions_count"] == 5
    assert adapter.is_connected()


@pytest.mark.asyncio
async def test_csv_authenticate_minimal():
    adapter = CSVImportAdapter()
    result = await adapter.authenticate({
        "csv_content": MINIMAL_CSV,
    })
    assert result["positions_count"] == 2


@pytest.mark.asyncio
async def test_csv_authenticate_missing_columns():
    adapter = CSVImportAdapter()
    with pytest.raises(CSVParseError):
        await adapter.authenticate({"csv_content": INVALID_CSV_MISSING_COLUMNS})


@pytest.mark.asyncio
async def test_csv_authenticate_no_content():
    adapter = CSVImportAdapter()
    with pytest.raises(CSVParseError):
        await adapter.authenticate({"csv_content": ""})


@pytest.mark.asyncio
async def test_csv_authenticate_bad_data():
    adapter = CSVImportAdapter()
    with pytest.raises(CSVParseError, match="No valid positions"):
        await adapter.authenticate({"csv_content": INVALID_CSV_BAD_DATA})


@pytest.mark.asyncio
async def test_csv_get_positions():
    adapter = CSVImportAdapter()
    await adapter.authenticate({"csv_content": VALID_CSV})
    positions = await adapter.get_positions()
    assert len(positions) == 5

    aapl = next(p for p in positions if p.symbol == "AAPL")
    assert aapl.quantity == 10
    assert aapl.average_cost == 150.00
    assert aapl.current_price == 175.50
    assert aapl.asset_type == "stock"
    assert aapl.sector == "Technology"


@pytest.mark.asyncio
async def test_csv_get_cash_balance():
    adapter = CSVImportAdapter()
    await adapter.authenticate({"csv_content": VALID_CSV, "cash_balance": 10000.0})
    cash = await adapter.get_cash_balance()
    assert cash == 10000.0


@pytest.mark.asyncio
async def test_csv_get_account_summary():
    adapter = CSVImportAdapter()
    await adapter.authenticate({"csv_content": VALID_CSV, "cash_balance": 5000.0})
    summary = await adapter.get_account_summary()
    assert summary.positions_count == 5
    assert summary.cash_balance == 5000.0
    assert summary.total_value > 0


@pytest.mark.asyncio
async def test_csv_disconnect():
    adapter = CSVImportAdapter()
    await adapter.authenticate({"csv_content": VALID_CSV})
    assert adapter.is_connected()
    await adapter.disconnect()
    assert not adapter.is_connected()


@pytest.mark.asyncio
async def test_csv_operations_before_auth():
    adapter = CSVImportAdapter()
    with pytest.raises(BrokerAuthenticationError):
        await adapter.get_positions()


@pytest.mark.asyncio
async def test_csv_unrealized_gains_calculated():
    adapter = CSVImportAdapter()
    await adapter.authenticate({"csv_content": VALID_CSV})
    positions = await adapter.get_positions()

    aapl = next(p for p in positions if p.symbol == "AAPL")
    expected_unrealized = (175.50 - 150.00) * 10
    assert abs(aapl.unrealized_gains - expected_unrealized) < 0.01


@pytest.mark.asyncio
async def test_csv_sample_template():
    template = CSVImportAdapter.get_sample_template()
    assert "symbol" in template
    assert "quantity" in template
    assert "average_cost" in template
    assert "AAPL" in template
