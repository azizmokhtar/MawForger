import ccxt
import pandas as pd

class HyperliquidUtils:
    
# Bot INIT, will ask for keys and address as input (works only for hyperliquid format for now)
    def __init__(self, wallet_address, private_key):
        # Initialize the exchange connection with provided keys
        self.exchange = ccxt.hyperliquid({
            "walletAddress": wallet_address,
            "privateKey": private_key,
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
            },
        })

    #=======================================================================================
        """
        Create an instance of the HyperLiquid class.
        If wallet_address or private_key are not provided, prompt the user for input.
        """
    #=======================================================================================
    @classmethod
    async def create(cls, wallet_address=None, private_key=None):
        if not wallet_address or not private_key:
            wallet_address, private_key = cls.get_user_credentials()
            
        # Create and return an instance of the class
        return cls(wallet_address, private_key)

    #=======================================================================================
        """
        Prompt the user to input their wallet address and private key.
        Returns:
        tuple: (wallet_address, private_key)
        """
    #=======================================================================================
    @staticmethod
    def get_user_credentials():
        while True:
            wallet_address = input("Enter your wallet address (e.g., 0x...): ").strip()
            if wallet_address.startswith("0x") and len(wallet_address) == 42:
                break
            print("Invalid wallet address format. It must be a 42-character Ethereum address starting with '0x'.")
            
        while True:
            private_key = input("Enter your private key (e.g., 0x...): ").strip()
            if private_key.startswith("0x") and len(private_key) == 66:
                break
            print("Invalid private key format. It must be a 66-character string starting with '0x'.")
           
        return wallet_address, private_key
    
# READ functions
    async def fetchTicker(self, symbol):
        try:
            data = self.exchange.fetch_ticker(symbol)
            return {
                "bid": data["bid"],
                "ask": data["ask"],
                "last": data["last"]
            }
        except Exception as e:
            print(f"Error fetching ticker: {e}")
            return None
        
    #=======================================================================================
        """Returns two instances:
            1: Complete overview of account: {'account_value': 697.548215, 'free_balance': 675.632015, 'used_margin': 21.5211, 'withdrawable': 676.027115, 'maintenance_margin': 0.93414, 'positions': [{'coin': 'BTC', 'size': 0.0004, 'entry_price': 82343.4, 'position_value': 32.4792, 'unrealized_pnl': -0.45816, 'return_on_equity': -0.0278200803, 'liquidation_price': None, 'margin_used': 16.2396, 'max_leverage': 40.0, 'leverage': 2.0, 'leverage_type': 'cross', 'funding': {'all_time': 0.249897, 'since_open': 0.003931, 'since_change': 0.002292}}, {'coin': 'ADA', 'size': -15.0, 'entry_price': 0.70452, 'position_value': 10.563, 'unrealized_pnl': 0.0048, 'return_on_equity': 0.0009084199, 'liquidation_price': 44.9336650794, 'margin_used': 5.2815, 'max_leverage': 10.0, 'leverage': 2.0, 'leverage_type': 'cross', 'funding': {'all_time': -0.074579, 'since_open': 0.0, 'since_change': 0.0}}], 'timestamp': 1741908024828}
            2: DF with openpositions:   symbol    size  side  entry_price  position_value  unrealized_pnl   pnl_pct  margin_used  leverage  funding_since_open
        """
    #=======================================================================================
    async def extensive_overview(self):
        try:
            # Fetch the balance information
            balance_info = self.exchange.fetch_balance()

            # Extract account value and liquidity information
            account_value = float(balance_info['info']['marginSummary']['accountValue'])
            free_balance = float(balance_info['info']['marginSummary']['totalRawUsd'])
            used_margin = float(balance_info['info']['marginSummary']['totalMarginUsed'])
            withdrawable = float(balance_info['info']['withdrawable'])

            # Extract risk management information
            maintenance_margin = float(balance_info['info']['crossMaintenanceMarginUsed'])

            # Initialize variables for position information
            positions_list = []  # Renamed to avoid conflict

            # Extract position details from assetPositions
            for asset_position in balance_info['info']['assetPositions']:
                if 'position' in asset_position:
                    position = asset_position['position']

                    coin = position['coin']
                    size = float(position['szi'])
                    entry_price = float(position['entryPx'])
                    position_value = float(position['positionValue'])
                    side = "long" if position_value >= 0 else "short"
                    unrealized_pnl = float(position['unrealizedPnl'])
                    return_on_equity = float(position['returnOnEquity'])

                    # Check if liquidationPx exists and is not None
                    liquidation_price = None
                    if 'liquidationPx' in position and position['liquidationPx'] is not None:
                        liquidation_price = float(position['liquidationPx'])

                    margin_used = float(position['marginUsed'])
                    max_leverage = float(position['maxLeverage'])

                    # Extract funding information with error handling
                    funding_data = {}
                    if 'cumFunding' in position:
                        funding = position['cumFunding']
                        funding_data = {
                            'all_time': float(funding.get('allTime', 0)),
                            'since_open': float(funding.get('sinceOpen', 0)),
                            'since_change': float(funding.get('sinceChange', 0))
                        }
                    else:
                        funding_data = {
                            'all_time': 0.0,
                            'since_open': 0.0,
                            'since_change': 0.0
                        }

                    # Get leverage value
                    if 'leverage' in position and 'value' in position['leverage']:
                        leverage = float(position['leverage']['value'])
                        leverage_type = position['leverage']['type']
                    else:
                        leverage = 1.0
                        leverage_type = "unknown"

                    # Create position object
                    position_info = {
                        'symbol': coin,
                        'size': size,
                        'side': side,
                        'entry_price': entry_price,
                        'position_value': position_value,
                        'unrealized_pnl': unrealized_pnl,
                        'pnl_pct': return_on_equity,
                        'liquidation_price': liquidation_price,
                        'margin_used': margin_used,
                        'max_leverage': max_leverage,
                        'leverage': leverage,
                        'leverage_type': leverage_type,
                        'funding': funding_data
                    }

                    positions_list.append(position_info)

            # Create a summary object with all extracted information
            account_summary = {
                'account_value': account_value,
                'free_balance': free_balance,
                'used_margin': used_margin,
                'withdrawable': withdrawable,
                'maintenance_margin': maintenance_margin,
                'positions': positions_list,
                'timestamp': balance_info['timestamp']
            }

            # Create DataFrame if positions exist
            if positions_list:
                positions_df = pd.DataFrame(positions_list)
                positions_df['pnl_pct'] = positions_df['pnl_pct'] * 100
                # Create a copy of funding data before dropping
                if 'funding' in positions_df.columns:
                    positions_df['funding_since_open'] = positions_df['funding'].apply(lambda x: x.get('since_open', 0))

                # Drop columns
                columns_to_drop = []
                for col in ['liquidation_price', 'max_leverage', 'leverage_type', 'funding']:
                    if col in positions_df.columns:
                        columns_to_drop.append(col)

                if columns_to_drop:
                    positions_df = positions_df.drop(columns=columns_to_drop)

                return account_summary, positions_df
            else:
                # Return empty DataFrame if no positions
                return account_summary, pd.DataFrame()

        except Exception as e:
            print(f"Error fetching Hyperliquid account info: {e}")
            return None, None  # Return None, None instead of just None
        
    #=======================================================================================
        """
        Returns a DF with open positions:   symbol size side entry_price position_value unrealized_pnl pnl_pct margin_used leverage
        """
    #=======================================================================================       
    async def positions(self):
        try:
            # Fetch the balance information
            balance_info = self.exchange.fetch_balance()

            # Initialize empty list for positions
            positions_list = []

            # Extract position details from assetPositions
            for asset_position in balance_info['info']['assetPositions']:
                if 'position' in asset_position:
                    position = asset_position['position']

                    coin = position['coin']
                    size = float(position['szi'])
                    entry_price = float(position['entryPx'])
                    position_value = float(position['positionValue'])
                    side = "long" if position_value >= 0 else "short"
                    unrealized_pnl = float(position['unrealizedPnl'])
                    return_on_equity = float(position['returnOnEquity'])
                    margin_used = float(position['marginUsed'])

                    # Get leverage value
                    if 'leverage' in position and 'value' in position['leverage']:
                        leverage = float(position['leverage']['value'])
                    else:
                        leverage = 1.0

                    # Create position object with only required fields
                    position_info = {
                        'symbol': coin,
                        'size': size,
                        'side': side,
                        'entry_price': entry_price,
                        'position_value': position_value,
                        'unrealized_pnl': unrealized_pnl,
                        'pnl_pct': return_on_equity,
                        'margin_used': margin_used,
                        'leverage': leverage
                    }

                    positions_list.append(position_info)

            # Create DataFrame if positions exist
            if positions_list:
                positions_df = pd.DataFrame(positions_list)
                positions_df['pnl_pct'] = positions_df['pnl_pct'] * 100
                return positions_df
            else:
                # Return empty DataFrame if no positions
                return pd.DataFrame()

        except Exception as e:
            print(f"Error fetching positions: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        
    #=======================================================================================
        """
            A function that returns (size in dollars, in quote) of the size of the position of a chosen symbol 
            Input format: btc/ada/sol
        """
    #=======================================================================================     
    async def get_position_size(self, symbol):
        # Get positions DataFrame directly from the positions function
        positions_df = await self.positions()
        symbol = symbol.upper()

        # Check if positions_df exists and is not empty
        if positions_df is not None and not positions_df.empty:
            # Filter for the specific coin
            coin_position = positions_df[positions_df['symbol'] == symbol]

            # Check if this coin exists in your positions
            if not coin_position.empty:
                # Return the position value for this coin
                return float(coin_position['position_value'].values[0]), float(coin_position['size'].values[0])
            else:
                #print(f"No position found for {symbol}") # what s heppeining here
                return 0.0, 0.0
        else:
            print("No positions found OR error fetching positions")
            return 0.0, 0.0
        

    #=======================================================================================
        """
            A function that returns position pnl in % of a chosen symbol 
            Input format: btc/ada/sol
        """
    #=======================================================================================
    async def get_position_pnl(self, symbol):
        # Get positions DataFrame directly from the positions function
        positions_df = await self.positions()
        symbol = symbol.upper()

        # Check if positions_df exists and is not empty
        if positions_df is not None and not positions_df.empty:
            # Filter for the specific coin
            coin_position = positions_df[positions_df['symbol'] == symbol]

            # Check if this coin exists in your positions
            if not coin_position.empty:
                # Return the position value for this coin
                return float(coin_position['pnl_pct'].values[0])
            else:
                #print(f"No position found for {symbol}") # what s heppeining here
                return 0.0
        else:
            print("No positions found OR error fetching positions")
            return 0.0
        
    #=======================================================================================
        """
        function that takes two inputs: a dictionary of order IDs and a list of order data. 
        It iterates through the order IDs, looks up their statuses in the order data, and returns a dictionary mapping the order IDs to their respective statuses, returns:{87483187719: 'open', 87483189538: 'filled', 87483190832: 'canceled'}
        Input format: order_ids_input = {1: '87483187719', 1.6: '87483189538', 6: '87483190832'} From .create_batch_limit_buy_order_custom_dca
                     order_data_input = [
                                        {'info': {'order': {...}, 'status': 'open'}, 'id': '87483187719', ...},
                                        {'info': {'order': {...}, 'status': 'filled'}, 'id': '87483189538', ...},
                                        {'info': {'order': {...}, 'status': 'canceled'}, 'id': '87483190832', ...},
                                        # ... other order data entries ...
                                    ]  From .fetch_orders(symbol) 
        """
    #=======================================================================================
    async def get_order_statuses(order_ids, order_data):
        result = {}
        # Create a lookup dictionary from order_data for quick access by ID
        order_lookup = {item['id']: item['info']['status'] for item in order_data}

        # Iterate over the given order IDs and find their statuses
        for key, order_id in order_ids.items():
            status = order_lookup.get(order_id, 'Not Found')  # Default to 'Not Found' if ID is missing
            result[int(order_id)] = status

        return result
    
    # MANIPULATION functions
    async def setLeverage(self, leverage, symbol):
            try:
                self.exchange.set_leverage(leverage=leverage, symbol=symbol)
                print("Leverage set")
            except Exception as e:
                print(f"Error setting leverage: {e}")

    async def leveragedMarketOrder(self, symbol, side, amount):
            try:
                # Fetch the current price for the symbol
                ticker_data = await self.fetchTicker(symbol)  
                if not ticker_data:
                    print("Failed to fetch ticker data for placing a market order!")
                    return None, None
                price = ticker_data["ask"] if side.lower() == "buy" else ticker_data["bid"]

                # Calculate the amount (in base asset) to achieve the desired order value
                amount_in_base = amount / price

                # Place the market order
                order =  self.exchange.create_market_order(
                    symbol=symbol,
                    side=side.lower(),
                    amount=amount_in_base,
                    price=price,
                )

                # Extract relevant information from the order response
                buy_price = float(order['info']['filled']['avgPx'])
                order_id = order['info']['filled']['oid']

                return buy_price, order_id, amount_in_base

            except Exception as e:
                print(f"Error placing leveraged market {side} order: {e}")
                return None, None, None
            
#=======================================================================================
    """
        A function that closes an open order (long or short)
        input: symbol from the remapped
        side_to_close: side of the order
        amount: use self.get_position_size("btc")[1]
    """
#=======================================================================================
    
    async def leveraged_market_close_Order(self, symbol, side_to_close):
        try:
            print(f"Starting close order for {symbol}!")
            # Fetch the current price for the symbol
            ticker_data = self.exchange.fetch_ticker(symbol)  # Removed await as per your comment
            if not ticker_data:
                print("Failed to fetch ticker data for closing a market order!")
                return None, None
            price = ticker_data["ask"] if side_to_close.lower() == "buy" else ticker_data["bid"]
            
            # Determine the correct side for closing the position
            close_side = "sell" if side_to_close.lower() == "buy" else "buy"
            amount = await self.get_position_size(symbol)
            amount = abs(amount[1])

            #print(f"amount to close is {amount}!") # check, this 0
            # Place the market order
            order = self.exchange.create_market_order(
                symbol=symbol,
                side=close_side,
                price=price,
                amount=amount,
                params={'reduceOnly': True}
            )

            # Extract relevant information from the order response
            buy_price = order['info']['filled']['avgPx'] if 'filled' in order['info'] else None
            order_id = order['info']['filled']['oid'] if 'filled' in order['info'] else order['id']
            return buy_price, order_id

        except Exception as e:
            print(f"Error placing leveraged market close order: {e}")
            return None, None
        
    #=======================================================================================
        """
            A function that creates limit buy order
            Input: amount in dollars
                   symbol as mapped
        """
    #=======================================================================================
    async def create_limit_buy_order(self, amount, symbol, deviation):
        try:
            ticker_data = self.exchange.fetchTicker(symbol) 
            if not ticker_data:
                print("Failed to fetch ticker data for placing a market order!")
                return None, None
            price = ticker_data["ask"] * (1 - deviation/100)
            amount_in_base = amount / price
            order = self.exchange.create_limit_buy_order(
                symbol, 
                amount_in_base, 
                price, 
                params ={'postOnly': True }
            )
            order_id = order['info']['resting']['oid']
            return order_id
        except Exception as e:
            print(f"Error placing leveraged limit buy order: {e}")
            return None
        
    #=======================================================================================
        """
            A function that creates limit buy order
            CUSTOM
            Input: pivot_price is the first buy that dcais based on it
                   amount in dollars
                   multiplier if i want to double the buy size or whatever multiplier
                   symbol as mapped
                   deviations=[0.2, ..., 0.3]
            NORMAL
            Input: pivot_price is the first buy that dca is based on it
                   amount in dollars
                   multiplier if i want to double the buy size or whatever multiplier
                   symbol as mapped
                   deviation_levels= how many SO buys
                   deviation = deviation percent
        """
    #=======================================================================================

    async def create_limit_deviation_list(self, number_of_levels, deviation):
        deviations = []
        for i in range(1, number_of_levels + 1):  # Start from 1 and go up to number_of_levels
            deviations.append(float(deviation * i))
        return deviations
        
    async def create_batch_limit_buy_order_custom_dca(self, pivot_price, base_amount, multiplier, symbol, deviations):
        orders = {}
        #current_amount = base_amount  # Start with the initial amount
        #print(deviations)

        for deviation in deviations:
            #print(f"opening limit order for deviation: {deviation}")
            #print(deviation)
            price = pivot_price * (1 - deviation/100)
           # print(f"price is {price}")

            # Update the amount for each iteration
            #print(f"buy size {current_amount}")

            # Calculate amount in base currency
            amount_in_base = base_amount / price
            #print(f"base size {amount_in_base}")

            # Create the order
            order = self.exchange.create_limit_buy_order(
                symbol,
                amount_in_base,
                price,
                params={'postOnly': True}
            )

            orders[deviation] = order['info']['resting']['oid']

            # Update the current_amount for the next iteration
            base_amount = base_amount * multiplier

        return orders
    
    #=======================================================================================
        """
        Cancels limit orders for specified deviations, continuing even if some orders fail.

        Inputs:
            - deviations (list): List of deviation values to cancel orders for
            - symbol (str): Trading pair symbol
            - order_ids (dict): Dictionary mapping deviations to order IDs

        Outputs:
            - 1 if at least one order was successfully canceled, 0 if all failed
        """
    #=======================================================================================
    async def cancelLimitOrders(self, deviations, symbol, order_ids):

        cancelled_count = 0
        failed_count = 0

        for deviation in deviations:
            if deviation in order_ids:
                order_id = order_ids[deviation]
                try:
                    # Attempt to cancel this specific order
                    cancelled_order = self.exchange.cancel_order(order_id, symbol)
                    print(f"Successfully canceled order for deviation {deviation}")
                    cancelled_count += 1
                except Exception as e:
                    # If this specific order fails, log it but continue with others
                    print(f"Failed to cancel order for deviation {deviation}, error: {e}")
                    failed_count += 1
                    

        # Report summary
        print(f"Cancellation complete: {cancelled_count} orders canceled, {failed_count} failed")

        # Return 1 if at least one order was canceled successfully
        return failed_count if cancelled_count > 0 else 0
    


