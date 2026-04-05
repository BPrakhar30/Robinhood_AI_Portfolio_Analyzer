import pytest
from app.broker_integrations.base import BrokerInterface, PositionData, TransactionData, AccountSummary


def test_position_data_defaults():
    pos = PositionData(
        symbol="AAPL",
        name="Apple Inc",
        quantity=10,
        average_cost=150.0,
        current_price=175.0,
    )
    assert pos.symbol == "AAPL"
    assert pos.realized_gains == 0.0
    assert pos.unrealized_gains == 0.0
    assert pos.asset_type == "stock"
    assert pos.currency == "USD"
    assert pos.purchase_date is None
    assert pos.sector is None


def test_transaction_data_defaults():
    txn = TransactionData(
        symbol="MSFT",
        transaction_type="buy",
        quantity=5,
        price=400.0,
        total_amount=2000.0,
    )
    assert txn.fees == 0.0
    assert txn.executed_at is not None


def test_account_summary_defaults():
    summary = AccountSummary(
        total_value=100000.0,
        cash_balance=5000.0,
        positions_count=10,
    )
    assert summary.buying_power == 0.0
    assert summary.total_realized_gains == 0.0
    assert summary.total_unrealized_gains == 0.0


def test_broker_interface_is_abstract():
    with pytest.raises(TypeError):
        BrokerInterface()
