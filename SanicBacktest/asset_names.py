us_market_stocks_popular = [
    # Technology
    'AAPL',  # Apple Inc.
    'MSFT',  # Microsoft Corporation
    'GOOGL',  # Alphabet Inc. (Google)
    'AMZN',  # Amazon.com Inc.
    'NVDA',  # NVIDIA Corporation
    'META',  # Meta Platforms Inc. (Facebook)
    'TSLA',  # Tesla Inc.
    'AVGO',  # Broadcom Inc.
    'ORCL',  # Oracle Corporation
    'CSCO',  # Cisco Systems Inc.
    'ADBE',  # Adobe Inc.
    'CRM',   # Salesforce Inc.
    'AMD',   # Advanced Micro Devices Inc.
    'INTC',  # Intel Corporation

    # Finance
    'JPM',   # JPMorgan Chase & Co.
    'BAC',   # Bank of America Corporation
    'WFC',   # Wells Fargo & Company
    'GS',    # Goldman Sachs Group Inc.
    'MS',    # Morgan Stanley
    'C',     # Citigroup Inc.
    'BLK',   # BlackRock Inc.

    # Healthcare
    'JNJ',   # Johnson & Johnson
    'UNH',   # UnitedHealth Group Incorporated
    'PFE',   # Pfizer Inc.
    'ABBV',  # AbbVie Inc.
    'MRK',   # Merck & Co. Inc.
    'LLY',   # Eli Lilly and Company

    # Consumer Goods
    'PG',    # Procter & Gamble Company
    'KO',    # Coca-Cola Company
    'PEP',   # PepsiCo Inc.
    'WMT',   # Walmart Inc.
    'COST',  # Costco Wholesale Corporation
    'NKE',   # NIKE Inc.
    'MCD',   # McDonald's Corporation

    # Energy
    'XOM',   # Exxon Mobil Corporation
    'CVX',   # Chevron Corporation
    'COP',   # ConocoPhillips

    # Telecommunications
    'VZ',    # Verizon Communications Inc.
    'T',     # AT&T Inc.

    # Industrial
    'BA',    # Boeing Company
    'CAT',   # Caterpillar Inc.
    'GE',    # General Electric Company
    'HON',   # Honeywell International Inc.

    # Others
    'DIS',   # Walt Disney Company
    'NFLX',  # Netflix Inc.
    'V',     # Visa Inc.
    'MA',    # Mastercard Incorporated
    'PYPL',  # PayPal Holdings Inc.
]

us_market_stocks_more = [
    # Technology
    'IBM', 'QCOM', 'TXN', 'AMAT', 'MU', 'NXPI', 'LRCX', 'NOW', 'INTU', 'PANW',
    'SNPS', 'CDNS', 'KLAC', 'MRVL', 'FTNT', 'ADSK', 'CTSH', 'ANET', 'TEAM', 'ZS',

    # Finance
    'AXP', 'USB', 'PNC', 'SCHW', 'COF', 'TFC', 'AIG', 'MMC', 'SPGI', 'CME',
    'ICE', 'CB', 'PGR', 'TRV', 'ALL', 'AMP', 'TROW', 'DFS', 'FITB', 'KEY',

    # Healthcare
    'TMO', 'ABT', 'BMY', 'AMGN', 'MDT', 'GILD', 'ISRG', 'VRTX', 'REGN', 'HUM',
    'CI',  'BSX', 'ZTS', 'DXCM', 'BIIB', 'IDXX', 'A', 'IQV', 'BDX',

    # Consumer Goods
    'HD',  'LOW', 'SBUX', 'MO', 'PM', 'EL', 'CL', 'KMB', 'GIS',
    'HSY', 'SJM', 'CAG', 'CPB', 'TAP', 'KHC', 'STZ', 'TSN', 'HRL',

    # Energy
    'SLB', 'EOG',  'PSX', 'VLO', 'MPC', 'OXY', 'KMI', 'WMB', 'HAL',
    'BKR', 'DVN', 'HES', 'OKE', 'TRP', 'CNQ', 'SU', 'IMO', 'CVE', 'ENB',

    # Industrial
    'UNP', 'UPS', 'RTX', 'LMT', 'MMM', 'DE', 'EMR', 'ETN', 'ITW', 'PH',
    'ROK', 'CMI', 'DOV', 'IR', 'XYL', 'AME', 'ROP', 'TT', 'SWK', 'FTV',

    # Materials
    'LIN', 'APD', 'SHW', 'ECL', 'DD', 'NEM', 'FCX', 'NUE', 'VMC', 'MLM',
    'ALB', 'FMC', 'IFF', 'CE', 'PPG', 'EMN', 'LYB', 'MOS', 'CF', 'DOW',

    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'PEG', 'WEC',
    'ES', 'ED', 'EIX', 'PPL', 'AEE', 'ETR', 'FE', 'DTE', 'CMS', 'AES',

    # Real Estate
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'SPG', 'SBAC', 'AVB',
    'EQR', 'O', 'VTR', 'ARE', 'BXP', 'ESS', 'UDR', 'EXR', 'MAA', 'IRM',

    # Others
    'UBER', 'LYFT', 'SNAP', 'PINS', 'ZM', 'DOCU', 'TWLO', 'SQ', 'SHOP', 'ROKU',
    'TTD', 'OKTA', 'DDOG', 'NET', 'CRWD', 'ETSY', 'CHWY', 'BILI', 'SE'
]

us_market_stocks = us_market_stocks_popular + us_market_stocks_more

# Popular Cryptocurrencies with -USD pairs
cryptocurrencies = [
    'BTC-USD', 'ETH-USD', 'XRP-USD', 'ADA-USD', 'SOL-USD',
    'DOT-USD', 'DOGE-USD', 'LTC-USD', 'SHIB-USD', 'AVAX-USD', 'MATIC-USD',
    'LINK-USD', 'XLM-USD', 'ATOM-USD', 'FIL-USD', 'NEAR-USD', 'ICP-USD',
    'ALGO-USD', 'AAVE-USD',
]
# Major Pairs (Highest volume and tightest spreads)
major_pairs = [
    "EURUSD=X",  # Euro/US Dollar - Highest volume pair globally
    "USDJPY=X",  # US Dollar/Japanese Yen
    "GBPUSD=X",  # British Pound/US Dollar
    "USDCHF=X",  # US Dollar/Swiss Franc
    "AUDUSD=X",  # Australian Dollar/US Dollar
    "USDCAD=X",  # US Dollar/Canadian Dollar
    "NZDUSD=X",  # New Zealand Dollar/US Dollar
]

# Minor Pairs (Good volume and reasonable spreads)
minor_pairs = [
    "EURJPY=X",  # Euro/Japanese Yen
    "GBPJPY=X",  # British Pound/Japanese Yen
    "EURGBP=X",  # Euro/British Pound
    "EURCHF=X",  # Euro/Swiss Franc
    "AUDNZD=X",  # Australian Dollar/New Zealand Dollar
    "CADJPY=X",  # Canadian Dollar/Japanese Yen
    "CHFJPY=X",  # Swiss Franc/Japanese Yen
    "AUDCAD=X",  # Australian Dollar/Canadian Dollar
    "AUDCHF=X",  # Australian Dollar/Swiss Franc
    "AUDJPY=X",  # Australian Dollar/Japanese Yen
    "CADCHF=X",  # Canadian Dollar/Swiss Franc
    "EURAUD=X",  # Euro/Australian Dollar
    "EURCAD=X",  # Euro/Canadian Dollar
    "EURNZD=X",  # Euro/New Zealand Dollar
    "GBPAUD=X",  # British Pound/Australian Dollar
    "GBPCAD=X",  # British Pound/Canadian Dollar
    "GBPCHF=X",  # British Pound/Swiss Franc
    "GBPNZD=X",  # British Pound/New Zealand Dollar
    "NZDCAD=X",  # New Zealand Dollar/Canadian Dollar
    "NZDCHF=X",  # New Zealand Dollar/Swiss Franc
    "NZDJPY=X",  # New Zealand Dollar/Japanese Yen
]

# Asian Pairs (Good liquidity during Asian session)
asian_pairs = [
    "USDCNH=X",  # US Dollar/Chinese Yuan (Offshore)
    "USDHKD=X",  # US Dollar/Hong Kong Dollar
    "USDSGD=X",  # US Dollar/Singapore Dollar
    "USDINR=X",  # US Dollar/Indian Rupee
    "USDKRW=X",  # US Dollar/South Korean Won
    "USDTHB=X",  # US Dollar/Thai Baht
    "USDIDR=X",  # US Dollar/Indonesian Rupiah
    "USDPHP=X",  # US Dollar/Philippine Peso
    "USDTWD=X",  # US Dollar/Taiwan Dollar
]

# European Pairs (Good liquidity during European session)
european_pairs = [
    "USDSEK=X",  # US Dollar/Swedish Krona
    "USDNOK=X",  # US Dollar/Norwegian Krone
    "USDDKK=X",  # US Dollar/Danish Krone
    "USDPLN=X",  # US Dollar/Polish Złoty
    "USDHUF=X",  # US Dollar/Hungarian Forint
    "USDCZK=X",  # US Dollar/Czech Koruna
    "USDRUB=X",  # US Dollar/Russian Ruble
]


# All pairs combined for easy access
forex = (
    major_pairs +
    minor_pairs +
    asian_pairs +
    european_pairs
)

# Dictionary mapping pairs to typical trading sessions for best liquidity
pair_sessions = {
    "Asian Session (00:00-08:00 GMT)": ["USDJPY=X", "AUDUSD=X", "NZDUSD=X", "USDCNH=X", "USDHKD=X"],
    "European Session (07:00-16:00 GMT)": ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDCHF=X"],
    "US Session (12:00-21:00 GMT)": ["EURUSD=X", "USDJPY=X", "USDCAD=X", "GBPUSD=X"]
}


commodities = [
    # Precious Metals
    "GC=F",  # Gold
    "SI=F",  # Silver
    "PL=F",  # Platinum
    "PA=F",  # Palladium

    # Energy
    "CL=F",  # Crude Oil (WTI)
    "BZ=F",  # Brent Crude Oil
    "NG=F",  # Natural Gas
    "HO=F",  # Heating Oil
    "RB=F",  # RBOB Gasoline

    # Agricultural
    "ZC=F",  # Corn
    "ZW=F",  # Wheat
    "ZS=F",  # Soybeans
    "ZL=F",  # Soybean Oil
    "ZM=F",  # Soybean Meal
    "KC=F",  # Coffee
    "SB=F",  # Sugar
    "CC=F",  # Cocoa
    "CT=F",  # Cotton
    "OJ=F",  # Orange Juice

    # Livestock
    "LE=F",  # Live Cattle
    "HE=F",  # Lean Hogs
    "GF=F",  # Feeder Cattle

    # Industrial Metals
    "HG=F",  # Copper
    "ALI=F",  # Aluminum

    # Softs
    "ZO=F",  # Oats
    "ZR=F",  # Rough Rice

]

# Indices
indices = [
    # US Indices
    "^GSPC",  # S&P 500
    "^DJI",   # Dow Jones Industrial Average
    "^IXIC",  # NASDAQ Composite
    "^RUT",   # Russell 2000

    # Global Indices
    "^FTSE",  # FTSE 100 (UK)
    "^N225",  # Nikkei 225 (Japan)
    "^GDAXI",  # DAX (Germany)
    "^FCHI",  # CAC 40 (France)

    # Other Important Indices
    "^VIX",   # CBOE Volatility Index
    "^TNX",   # 10-Year Treasury Yield
]

all_assets = [us_market_stocks, cryptocurrencies, forex, commodities, indices]

rigorous_symbols = [
    # Forex Symbols
    "AUDJPY=X",
    "NZDJPY=X",
    "GBPAUD=X",
    "EURUSD=X",  # Less popular
    "GBPUSD=X",  # Less popular
    "USDJPY=X",  # Less popular
    "USDCAD=X",  # Less popular
    # "USDZAR=X",
    # "USDBRL=X",
    # "USDKRW=X",

    # Cryptocurrency Symbols
    "BTC-USD",
    "ETH-USD",
    "XRP-USD",
    "DOGE-USD",  # Less popular
    # "LTC-USD",  # Less popular
    # "SOL-USD",  # Less popular
    # "ADA-USD",  # Less popular
    # "DOT-USD",  # Less popular
    # "LINK-USD",  # Less popular

    # Stock Symbols
    "TSLA",
    "AAPL",
    "NFLX",
    "MSFT",  # Less popular
    "GOOGL",  # Less popular
    "AMZN",  # Less popular
    "META",  # Less popular

    # Gold Symbol
    "GC=F",

    # Silver Symbol
    "SI=F",

    # Oil Symbols
    "CL=F",  # Crude Oil
    "NG=F",  # Less popular

    # Indices
    "^GSPC",  # S&P 500
    "^DJI",   # Dow Jones Industrial Average
    "^IXIC",  # NASDAQ Composite
]
