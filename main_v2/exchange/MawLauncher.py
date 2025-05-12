from utils.Logger import get_logger
from config.ConfigManager import ConfigManager
from state.StateManager import StateManager
from exchange.Hyperliquid import HyperliquidUtils
from core.Events import PositionOpenedEvent, PositionUpdatedEvent, PositionClosedEvent
from notifier.TelegramMessenger import TelegramNotifier
from core.EventBus import EventBus

logger = get_logger(__name__)

def format_symbol(symbol: str) -> str:
    return f"{symbol}/USDC:USDC"

class MawStartupLauncher:
    def __init__(
        self,
        config: ConfigManager,
        state_manager: StateManager,
        hyperliquid_executor: HyperliquidUtils,
        telegram_notifier: TelegramNotifier,
        event_bus: EventBus
    ):
        self.hyperliquid_executor = hyperliquid_executor
        self.telegram_notifier = telegram_notifier
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.leverage = config.get("LEVERAGE")
        self.multiplier = config.get("MULTIPLIER")
        self.deviations = config.get("DEVIATIONS")
        self.buy_size = config.get("BUY_SIZE")
        self.symbols = config.get("INITIAL_SYMBOLS")


    async def launcher(self):
        print("starting bot ")
        logger.info("Telegram notifier initiated")
        for symbol in self.symbols:
            ticker = format_symbol(symbol)
            try:
                await self.hyperliquid_executor.setLeverage(self.leverage, ticker)
                logger.info(f"Set leverage for {symbol}")
                order = await self.hyperliquid_executor.leveragedMarketOrder(ticker, "buy", self.buy_size)
                limit_orders = await self.hyperliquid_executor.create_batch_limit_buy_order_custom_dca(
                    order[0], self.buy_size, self.multiplier, ticker, self.deviations
                )
                await self.state_manager.add_position(symbol=symbol, average_buy_price=order[0], pnl=0.0,
                       size_in_dollars=self.buy_size , size_in_quote=self.buy_size, limit_orders=limit_orders, ttp_active=False)
                
                await self.event_bus.publish("position_opened", PositionOpenedEvent(
                    symbol=symbol,
                    average_buy_price=order[0],
                    size_in_dollars=self.buy_size,
                    size_in_quote=0,
                    ttp_active=False
                ))
                logger.info(f"Opened first position for {symbol}")
                await self.telegram_notifier._safe_send(f"Opened first position for: {symbol}")
            except Exception as e:
                logger.error(f"Error placing first order for {symbol}: {e}")
                await self.telegram_notifier._safe_send(f"ERROR - Error placing first order for: {symbol}")
