from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class PositionEvent:
    timestamp: datetime = datetime.now()

@dataclass
class PositionOpenedEvent(PositionEvent):
    symbol: str = ""
    average_buy_price: float = 0.0
    size_in_dollars: float = 0.0
    size_in_quote: float = 0.0
    ttp_active: bool = False

@dataclass
class PositionUpdatedEvent(PositionEvent):
    symbol: str = ""
    pnl: Optional[float] = None
    peak_pnl: Optional[float] = None
    size_in_dollars: Optional[float] = None
    size_in_quote: Optional[float] = None
    limit_orders: Optional[dict] = None
    ttp_active: Optional[bool] = None
    average_buy_price: Optional[float] = None

@dataclass
class PositionClosedEvent(PositionEvent):
    symbol: str = ""
    final_pnl: float = 0.0