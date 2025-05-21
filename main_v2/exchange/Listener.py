import asyncio
import websockets
import json
from config.ConfigManager import ConfigManager
from core.EventBus import EventBus
from state.StateManager import StateManager
from exchange.Hyperliquid import HyperliquidUtils
from core.Events import PositionOpenedEvent, PositionUpdatedEvent, PositionClosedEvent
from utils.Logger import get_logger
from utils.PerformanceLogger import FastLogger


logger = get_logger(__name__)

def format_symbol(symbol: str) -> str:
    return f"{symbol}/USDC:USDC"

class HyperliquidWebSocketListener:
    def __init__(
        self,
        config: ConfigManager,
        state_manager: StateManager,
        hyperliquid_executor: HyperliquidUtils,
        event_bus: EventBus,
        perf_logger = FastLogger
    ):
        self.user_address = config.get("PUBLIC_USER_ADDRESS")
        self.max_retries = config.get("CONNECTION_ERROR_MAX_RETRIES")
        self.retry_delay = config.get("CONNECTION_ERROR_RETRY_DELAY")
        self.TP = config.get("TP")
        self.ttp_percent = config.get("TTP_PERCENT")
        self.deviations = config.get("DEVIATIONS")
        self.buy_size = config.get("BUY_SIZE")
        self.multiplier = config.get("MULTIPLIER")
        self.state_manager = state_manager
        self.hyperliquid_executor = hyperliquid_executor
        self.event_bus = event_bus
        self.websocket_uri = "wss://api.hyperliquid.xyz/ws"
        self.running = True
        self.perf_logger = perf_logger
        self._close_and_reopen_position = self.perf_logger.measure_async(
            "close_and_reopen", sample_rate=1
        )(self._close_and_reopen_position)

    async def start(self):
        logger.info("Starting Hyperliquid WebSocket listener...")
        while self.running:
            try:
                async with websockets.connect(self.websocket_uri) as websocket:
                    logger.info("Connected to Hyperliquid WebSocket")
                    await self._subscribe(websocket)
                    await self._listen_messages(websocket)
            except (websockets.exceptions.ConnectionClosed, ConnectionError) as e:
                retry_count += 1
                if retry_count > self.max_retries:
                    logger.error(f"WebSocket connection lost with error: {e}. Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.exception(f"Unexpected error in WebSocket: {e}")
                await asyncio.sleep(self.retry_delay)

    async def _subscribe(self, websocket):
        subscribe_message = {
            "method": "subscribe",
            "subscription": {
                "type": "webData2",
                "user": self.user_address
            }
        }
        await websocket.send(json.dumps(subscribe_message))
        logger.info("Subscribed to webData2 updates")

    async def _listen_messages(self, websocket):
        async def send_heartbeat():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send(json.dumps({"method": "ping"}))
                    logger.debug("→ Sent ping")
                except websockets.exceptions.ConnectionClosed:
                    logger.error("Connection closed during heartbeat")
                    break

        async def process_messages():
            while True:
                try:
                    message = await websocket.recv()
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode JSON from WebSocket: {e}")
                        continue

                    if data.get("channel") == "webData2":
                        await self._handle_web_data2(data)

                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket connection closed unexpectedly")
                    break

        await asyncio.gather(
            send_heartbeat(),
            process_messages()
        )

    async def _handle_web_data2(self, data: dict):
        clearinghouse_state = data.get("data", {}).get("clearinghouseState", {})
        asset_positions = clearinghouse_state.get("assetPositions", [])

        if not asset_positions:
            return

        for pos in asset_positions:
            position_data = pos.get("position", {})
            coin = position_data.get("coin", "UNKNOWN")
            #print(f"checking {coin}")
            szi = float(position_data.get("szi", 0))
            entry_px = float(position_data.get("entryPx", 0))
            position_value = float(position_data.get("positionValue", 0))
            unrealized_pnl = float(position_data.get("unrealizedPnl", 0))
            pnl_percent = ((unrealized_pnl / position_value) * 100) if position_value else 0.0

            # Update existing position or add new one
            position = self.state_manager.get_position(coin)

            if position is None:
                logger.warning(f"Unexpected open position found: {coin}, Setting limit orders...")
                ticker = format_symbol(coin)
                limit_orders = await self.hyperliquid_executor.create_batch_limit_buy_order_custom_dca(
                    entry_px, self.buy_size, self.multiplier, ticker, self.deviations
                )
                logger.warning(f"Limit orders set, now adding it to DB.")
                await self.state_manager.add_position(
                    symbol=coin,
                    average_buy_price=entry_px,
                    pnl=pnl_percent,
                    peak_pnl=pnl_percent,
                    size_in_dollars=position_value,
                    size_in_quote=szi,
                    limit_orders=limit_orders,
                    ttp_active=False
                )
                await self.event_bus.publish("position_opened", PositionOpenedEvent(
                    symbol=coin,
                    ttp_active=True
                    )
                )
                continue

            # Check if trailing take profit should activate
            if pnl_percent >= self.TP and not position["ttp_active"]:
                logger.info("pnl over target and no ttp active")
                await self.state_manager.update_position(
                    coin,
                    update=PositionUpdatedEvent(
                        symbol=coin,
                        average_buy_price=entry_px,
                        pnl=pnl_percent,
                        peak_pnl=pnl_percent,
                        size_in_dollars=position_value,
                        size_in_quote=szi,
                        ttp_active=True
                    )
                )
                logger.info(f"TTP activated for {coin}")
                await self.event_bus.publish("position_updated", PositionUpdatedEvent(
                    symbol=coin,
                    ttp_active=True
                ))
                continue

            # If TTP active and threshold reached
            if position["ttp_active"] and position.get("peak_pnl", 0) - pnl_percent >= self.ttp_percent:
                #print("ttp active and hit ttp closing now")
                await self._close_and_reopen_position(coin, pnl_percent)###

            # General update
            elif self.state_manager.has_position(coin):
                #print(f"just updating with pnl {pnl_percent}")
                #logger.info(f"just updating {coin} with pnl {pnl_percent}")
                await self.state_manager.update_position(
                    coin,
                    update=PositionUpdatedEvent(
                        symbol=coin,
                        average_buy_price=entry_px,
                        pnl=pnl_percent,
                        size_in_dollars=position_value,
                        size_in_quote=szi,
                        ttp_active=False
                    )
                )

                await self.event_bus.publish("position_updated", PositionUpdatedEvent(
                    symbol=coin,
                    average_buy_price=entry_px,
                    pnl=pnl_percent,
                    size_in_dollars=position_value,
                    size_in_quote=szi
                ))

        #await self._check_for_new_symbols()

    async def _close_and_reopen_position(self, coin: str, pnl_percent: float):
        logger.info(f"Closing profitable position: {coin}")
        ticker = format_symbol(coin)
        try:
            await self.hyperliquid_executor.leveraged_market_close_Order(ticker, "buy")
            position = self.state_manager.get_position(coin)
            limit_orders = position["limit_orders"]
            await self.hyperliquid_executor.cancelLimitOrders(self.deviations, ticker, limit_orders)
            logger.info(f"Closed {coin} position with profit.")
            await self.event_bus.publish("position_closed", PositionClosedEvent(symbol=coin, final_pnl=pnl_percent))

            #remove_decision = await self.symbol_manager.is_pending_removal(coin)
            remove_decision= False
            if not remove_decision:
                logger.info(f"Reopening {coin} position...")
                order = await self.hyperliquid_executor.leveragedMarketOrder(ticker, "buy", self.buy_size)
                limit_orders = await self.hyperliquid_executor.create_batch_limit_buy_order_custom_dca(
                    order[0], self.buy_size, self.multiplier, ticker, self.deviations
                )
                await self.state_manager.update_position(  #add pak pnl
                    coin,
                    update=PositionUpdatedEvent(
                        symbol=coin,
                        average_buy_price=order[0],
                        pnl=0.0,
                        peak_pnl=0.0,
                        size_in_dollars=self.buy_size,
                        limit_orders=limit_orders,
                        ttp_active=False
                    )
                )
                await self.event_bus.publish("position_opened", PositionOpenedEvent(
                    symbol=coin,
                    average_buy_price=order[0],
                    size_in_dollars=self.buy_size,
                    size_in_quote=0,
                    ttp_active=False
                ))
                await asyncio.sleep(1)
                logger.info(f"Finished reopening {coin} position.")
            else:
                logger.info(f"{coin} removed after closing.")
                self.state_manager.delete_position(coin)

        except Exception as e:
            logger.error(f"Error handling close/reopen for {coin}: {e}")

    #async def _check_for_new_symbols(self):
    #    current_active_symbols = await self.symbol_manager.get_active_symbols()
    #    for symbol in current_active_symbols:
    #        if not self.state_manager.has_position(symbol):
    #            logger.info(f"Opening new position for: {symbol}")
    #            ticker = format_symbol(symbol)
    #            try:
    #                await self.hyperliquid_executor.setLeverage(self.leverage, ticker)
    #                order = await self.hyperliquid_executor.leveragedMarketOrder(ticker, "buy", self.buy_size)
    #                limit_orders = await self.hyperliquid_executor.create_batch_limit_buy_order_custom_dca(
    #                    order[0], self.buy_size, self.multiplier, ticker, self.deviations
    #                )
    #                self.state_manager.add_position(
    #                    symbol=symbol,
    #                    average_buy_price=order[0],
    #                    pnl=0.0,
    #                    size_in_dollars=self.buy_size,
    #                    size_in_quote=0,
    #                    limit_orders=limit_orders,
    #                    ttp_active=False
    #                )
    #                await self.event_bus.publish("position_opened", PositionOpenedEvent(
    #                    symbol=symbol,
    #                    average_buy_price=order[0],
    #                    size_in_dollars=self.buy_size,
    #                    size_in_quote=0,
    #                    ttp_active=False
    #                ))
    #                logger.info(f"Opened first position for {symbol}")
    #            except Exception as e:
    #                logger.error(f"Error placing first order for {symbol}: {e}")

    def stop(self):
        self.running = False
        logger.info("WebSocket listener stopped")