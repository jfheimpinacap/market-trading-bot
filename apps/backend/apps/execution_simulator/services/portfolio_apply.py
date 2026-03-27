from decimal import Decimal

from apps.execution_simulator.models import PaperOrder, PaperOrderSide
from apps.paper_trading.services.execution import execute_paper_trade


def apply_fill_to_portfolio(*, order: PaperOrder, fill_quantity: Decimal, fill_price: Decimal):
    side_map = {
        PaperOrderSide.BUY_YES: ('BUY', 'YES'),
        PaperOrderSide.BUY_NO: ('BUY', 'NO'),
        PaperOrderSide.SELL_YES: ('SELL', 'YES'),
        PaperOrderSide.SELL_NO: ('SELL', 'NO'),
        PaperOrderSide.REDUCE: ('SELL', (order.metadata or {}).get('position_side', 'YES')),
        PaperOrderSide.CLOSE: ('SELL', (order.metadata or {}).get('position_side', 'YES')),
    }
    trade_type, position_side = side_map[order.side]
    return execute_paper_trade(
        market=order.market,
        trade_type=trade_type,
        side=position_side,
        quantity=fill_quantity,
        account=order.paper_account,
        execution_price=fill_price,
        notes=f'Execution simulator fill for order #{order.id}',
        metadata={
            'origin': 'execution_simulator',
            'paper_order_id': order.id,
            'paper_demo_only': True,
        },
    )
