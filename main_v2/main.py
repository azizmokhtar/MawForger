import asyncio
import logging
from utils.Logger import get_logger
from config.ConfigManager import ConfigManager
from state.StateManager import StateManager
from exchange.Hyperliquid import HyperliquidUtils
#from managers.SymbolManager import SymbolManager
from notifier.TelegramMessenger import TelegramNotifier
from core.EventBus import EventBus
from exchange.Listener import HyperliquidWebSocketListener
from exchange.MawLauncher import MawStartupLauncher

logger = get_logger(__name__)

async def main():

    # Load configuration
    config = ConfigManager()
    logger.info("Configuration loaded")
    config.print_config()
    telegram_notifier = TelegramNotifier(config)
    await telegram_notifier._safe_send("Starting trading bot...")
    logger.info("Telegram notifier initiated")
    # Initialize EventBus
    event_bus = EventBus()

    # Initialize shared services
    state_manager = StateManager(event_bus=event_bus)
    logger.info("Event Bus initiated")
    hyperliquid_executor = await HyperliquidUtils.create(config)
    await telegram_notifier._safe_send("Hyperliquid Executor initiated")
    logger.info("Hyperliquid Executor initiated")
    #symbol_manager = SymbolManager(initial_symbols=config.get("INITIAL_SYMBOLS", cast=list))
    

    logger.info("Shared services initialized")

    # Register event handlers (optional for now)
    event_bus.subscribe("position_opened", telegram_notifier.on_position_opened)
    #event_bus.subscribe("position_updated", telegram_notifier.on_position_updated)
    event_bus.subscribe("position_closed", telegram_notifier.on_position_closed)

    logger.info("Event handlers registered")
    startup = MawStartupLauncher(config, state_manager, hyperliquid_executor, telegram_notifier, event_bus)
    await startup.launcher()
    # Start WebSocket Listener
    listener = HyperliquidWebSocketListener(
        config=config,
        state_manager=state_manager,
        hyperliquid_executor=hyperliquid_executor,
        event_bus=event_bus
    )

    asyncio.create_task(listener.start())
    logger.info("WebSocket listener started")
    await telegram_notifier._safe_send("Websocket listener set up...")
    # Wait forever or until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await telegram_notifier._safe_send("Bot shutting down.")
        await listener.stop()
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())