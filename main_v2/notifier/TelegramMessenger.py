from telegram import Bot
from core.Events import PositionOpenedEvent, PositionUpdatedEvent, PositionClosedEvent

class TelegramNotifier:
    def __init__(self, config):
        self.token = config.get("TELEGRAM_MESSENGER_TOKEN")
        print(self.token)
        self.chat_id = config.get("MESSENGER_CHAT_ID")
        self.bot = Bot(token=self.token)
        
    async def on_position_opened(self, event: PositionOpenedEvent):
        message = (
            "Position Opened\n"
            f"Symbol: {event.symbol}\n"
            f"Average Buy Price: ${event.average_buy_price:.4f}\n"
            f"Size: ${event.size_in_dollars:.2f}"
        )
        await self._safe_send(message)
        
    async def on_position_closed(self, event: PositionClosedEvent):
        message = (
            "Position Closed\n"
            f"Symbol: {event.symbol}\n"
            f"Final PnL: {event.final_pnl:.2f}%"
        )
        await self._safe_send(message)


    async def _safe_send(self, text: str):
        try:
            async with self.bot:
                await self.bot.send_message(text=text, chat_id=self.chat_id)
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")


