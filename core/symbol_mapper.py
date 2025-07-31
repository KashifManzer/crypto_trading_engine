class SymbolMapper:
    """
    A utility to standardize trading pair symbols, as they often differ across exchanges.
    This class handles conversions between a universal format (e.g., 'BTC/USDT')
    and exchange-specific formats (e.g., 'BTCUSDT' for Binance, 'BTC-USDT' for KuCoin).
    """
    def __init__(self):
        # This can be expanded with more complex rules or loaded from a config file.
        self.mapping_rules = {
            'binance': {'separator': '', 'case': 'upper'},
            'kucoin': {'separator': '-', 'case': 'upper'},
            'bybit': {'separator': '', 'case': 'upper'},
            'okx': {'separator': '-', 'case': 'upper'},
            'bitmart': {'separator': '_', 'case': 'upper'},
        }
        self.universal_separator = '/'

    def to_exchange(self, universal_pair: str, exchange_name: str) -> str:
        """
        Converts a universal pair symbol to an exchange-specific one.
        
        Args:
            universal_pair (str): The pair in universal format (e.g., 'BTC/USDT').
            exchange_name (str): The name of the exchange (e.g., 'binance').
            
        Returns:
            The pair symbol in the exchange's format (e.g., 'BTCUSDT').
        """
        if exchange_name not in self.mapping_rules:
            raise ValueError(f"No mapping rules found for exchange: {exchange_name}")
            
        rules = self.mapping_rules[exchange_name]
        parts = universal_pair.split(self.universal_separator)
        
        exchange_pair = rules['separator'].join(parts)
        
        if rules['case'] == 'upper':
            return exchange_pair.upper()
        else:
            return exchange_pair.lower()

    def to_universal(self, exchange_pair: str, exchange_name: str) -> str:
        """
        Converts an exchange-specific pair symbol to the universal format.
        
        Args:
            exchange_pair (str): The pair in the exchange's format (e.g., 'BTCUSDT').
            exchange_name (str): The name of the exchange.
            
        Returns:
            The pair symbol in the universal format (e.g., 'BTC/USDT').
        """
        if exchange_name not in self.mapping_rules:
            raise ValueError(f"No mapping rules found for exchange: {exchange_name}")
            
        rules = self.mapping_rules[exchange_name]
        
        # Handle cases where there is no separator
        separator = rules['separator']
        if separator:
            parts = exchange_pair.split(separator)
        else:
            # Simple logic for pairs like BTCUSDT, assuming 3 or 4 letter quote currency
            if exchange_pair.endswith('USDT') or exchange_pair.endswith('USDC'):
                base = exchange_pair[:-4]
                quote = exchange_pair[-4:]
            elif exchange_pair.endswith('BTC') or exchange_pair.endswith('ETH'):
                 base = exchange_pair[:-3]
                 quote = exchange_pair[-3:]
            else:
                # Fallback for other quote currencies - may need refinement
                base = exchange_pair[:-3]
                quote = exchange_pair[-3:]
            parts = [base, quote]

        return self.universal_separator.join(parts).upper()

# Example Usage
if __name__ == '__main__':
    mapper = SymbolMapper()
    universal = 'BTC/USDT'
    
    # To Exchange
    binance_symbol = mapper.to_exchange(universal, 'binance')
    kucoin_symbol = mapper.to_exchange(universal, 'kucoin')
    print(f"Universal '{universal}' -> Binance: '{binance_symbol}'")
    print(f"Universal '{universal}' -> KuCoin: '{kucoin_symbol}'")
    
    # To Universal
    universal_from_binance = mapper.to_universal(binance_symbol, 'binance')
    universal_from_kucoin = mapper.to_universal(kucoin_symbol, 'kucoin')
    print(f"Binance '{binance_symbol}' -> Universal: '{universal_from_binance}'")
    print(f"KuCoin '{kucoin_symbol}' -> Universal: '{universal_from_kucoin}'")
