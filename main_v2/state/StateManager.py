import asyncio
from typing import Optional, Dict, List
from core.EventBus import EventBus  # We'll define this next
from core.Events import PositionOpenedEvent, PositionUpdatedEvent, PositionClosedEvent

class StateManager:
    def __init__(self, event_bus: EventBus):
        self.positions: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()
        self.event_bus = event_bus

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        return self.positions.get(symbol)

    async def add_position(self, symbol: str, average_buy_price: float, pnl: float,
                           size_in_dollars: float, size_in_quote: float, limit_orders: Dict, ttp_active: bool):
        async with self.lock:
            if symbol in self.positions:
                raise ValueError(f"Position with symbol '{symbol}' already exists.")
            self.positions[symbol] = {
                "symbol": symbol,
                "average_buy_price": average_buy_price,
                "pnl": pnl,
                "peak_pnl": max(pnl, 0.0),
                "size_in_dollars": size_in_dollars,
                "size_in_quote": size_in_quote,
                "limit_orders": limit_orders,
                "ttp_active": ttp_active
            }
            await self.event_bus.publish("position_opened", PositionOpenedEvent(symbol=symbol))

    async def update_position(self, symbol: str, update: PositionUpdatedEvent):
        async with self.lock:
            if symbol not in self.positions:
                return

            position = self.positions[symbol]
            for key, value in update.__dict__.items():
                if value is not None:
                    position[key] = value

            if update.pnl is not None:
                position['peak_pnl'] = max(position.get('peak_pnl', 0), update.pnl)

            await self.event_bus.publish("position_updated", PositionUpdatedEvent(symbol=symbol))

    async def delete_position(self, symbol: str):
        async with self.lock:
            if symbol in self.positions:
                del self.positions[symbol]
                await self.event_bus.publish("position_closed", PositionClosedEvent(symbol=symbol))