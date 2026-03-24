"""
Market Data Integration Module
Handles real-time market data from multiple sources:
- Gold prices: Alpha Vantage (with local cache fallback)
- Stocks, Crypto, Indices: TWELVEDATA (with local cache fallback)
- AI Investment suggestions: Based on market conditions
"""

import requests
from datetime import datetime, timedelta
from config import Config
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

logger = logging.getLogger(__name__)

_HTTP_SESSION = requests.Session()
_SNAPSHOT_CACHE = {}
_TWELVEDATA_TTL_SECONDS = 120
_FAIL_TTL_SECONDS = 60
_LOG_THROTTLE_SECONDS = 180
_LOG_CACHE = {}
_GOLDAPI_COOLDOWN_UNTIL = 0.0


FALLBACK_PRICE_ANCHORS = {
    # Updated anchors reduce large mismatch when live APIs are unavailable.
    'MRF': 138780.00,
}

TWELVEDATA_STOCK_SYMBOL_MAP = {
    'HDFC': ['HDB'],
    'ICICIBANK': ['IBN'],
    'INFY': ['INFY'],
    'WIPRO': ['WIT'],
    'TCS': ['TCS.NS', 'TCS'],
    'LT': ['LT.NS', 'LT'],
}

YAHOO_STOCK_SYMBOL_MAP = {
    'HDFC': ['HDFCBANK.NS'],
    'ICICIBANK': ['ICICIBANK.NS'],
    'TCS': ['TCS.NS'],
    'RELIANCE': ['RELIANCE.NS'],
    'INFY': ['INFY.NS'],
    'WIPRO': ['WIPRO.NS'],
    'LT': ['LT.NS'],
    'MARUTI': ['MARUTI.NS'],
    'TATAMOTORS': ['TATAMOTORS.NS'],
    'ITC': ['ITC.NS'],
    'SUNPHARMA': ['SUNPHARMA.NS'],
    'AXISBANK': ['AXISBANK.NS'],
    'KOTAKBANK': ['KOTAKBANK.NS'],
}

TWELVEDATA_INDEX_SYMBOLS = {
    # TWELVEDATA doesn't provide NSE/SENSEX directly for most plans; use broad ETFs.
    'nifty_50': ['INDA'],
    'sensex': ['INDY'],
    'sp500': ['SPY'],
}

YAHOO_INDEX_SYMBOLS = {
    'nifty_50': '^NSEI',
    'sensex': '^BSESN',
    'sp500': '^GSPC',
}

USDINR_FALLBACK = 83.0


def _get_live_usdinr_rate():
    """Fetch live USD to INR exchange rate from Yahoo Finance."""
    try:
        usdinr_closes = _fetch_yahoo_chart_closes("INR=X", range_value='1d')
        if usdinr_closes and len(usdinr_closes) > 0:
            return float(usdinr_closes[-1])
    except Exception:
        pass
    return USDINR_FALLBACK


def _is_reasonable_crypto_snapshot(name, snapshot):
    """Reject obviously bad live values before showing in UI."""
    if not snapshot:
        return False
    price = snapshot.get('price')
    if price is None:
        return False

    ranges = {
        'bitcoin': (1_000_000, 20_000_000),
        'ethereum': (50_000, 1_500_000),
        'dogecoin': (1, 100),
    }
    lower, upper = ranges.get(name, (0, float('inf')))
    return lower <= price <= upper


def _snapshot_from_closes(closes):
    """Build normalized snapshot from a list/series of close prices."""
    if not closes:
        return None

    current = float(closes[-1])
    previous = float(closes[-2]) if len(closes) > 1 else current
    start = float(closes[0])

    change_24h = ((current - previous) / previous * 100) if previous else 0.0
    change_period = ((current - start) / start * 100) if start else 0.0

    return {
        'price': round(current, 2),
        'change_24h': round(change_24h, 2),
        'change_period': round(change_period, 2)
    }


def _log_throttled(level, key, message):
    """Avoid flooding logs with same integration error on every request."""
    now = time.time()
    last = _LOG_CACHE.get(key)
    if last and (now - last < _LOG_THROTTLE_SECONDS):
        return
    _LOG_CACHE[key] = now
    if level == 'error':
        logger.error(message)
    else:
        logger.warning(message)


def _get_TWELVEDATA_json(path, params, cache_key):
    """Call TWELVEDATA endpoint and return JSON payload with short TTL cache."""
    now = time.time()
    cached = _SNAPSHOT_CACHE.get(cache_key)
    if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
        return cached['data']

    api_key = Config.TWELVEDATA_API_KEY
    if not api_key:
        _log_throttled('warning', 'TWELVEDATA:no_key', "TWELVEDATA_API_KEY is not configured")
        _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': None}
        return None

    query_params = (params or {}).copy()
    query_params['apikey'] = api_key

    try:
        response = _HTTP_SESSION.get(
            f"{Config.TWELVEDATA_API_URL}{path}",
            params=query_params,
            timeout=4
        )
        if response.status_code != 200:
            if response.status_code == 404:
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                return None
            _log_throttled(
                'warning',
                f"TWELVEDATA:http:{cache_key}:{response.status_code}",
                f"TWELVEDATA request failed for {cache_key}: HTTP {response.status_code}"
            )
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        payload = response.json()
        if isinstance(payload, dict) and payload.get('status') == 'error':
            _log_throttled('warning', f"TWELVEDATA:payload:{cache_key}", f"TWELVEDATA API issue for {cache_key}: {payload}")
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': payload}
        return payload
    except Exception as e:
        _log_throttled('warning', f"TWELVEDATA:exc:{cache_key}", f"TWELVEDATA request failed for {cache_key}: {str(e)}")
        _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
        return None


def _extract_TWELVEDATA_daily_closes(payload):
    """Extract ordered close prices from TWELVEDATA time_series payload."""
    if not isinstance(payload, dict):
        return []

    values = payload.get('values') or []
    if not isinstance(values, list):
        return []

    closes = []
    # TWELVEDATA returns latest first; reverse for chronological order.
    for row in reversed(values):
        try:
            close = row.get('close')
            if close is not None:
                closes.append(float(close))
        except (TypeError, ValueError):
            continue
    return closes


def _resolve_TWELVEDATA_stock_candidates(symbol):
    """Resolve app symbol to TWELVEDATA ticker candidates."""
    if symbol in TWELVEDATA_STOCK_SYMBOL_MAP:
        return TWELVEDATA_STOCK_SYMBOL_MAP[symbol]
    return [f"{symbol}.NS", symbol]


def _fetch_TWELVEDATA_daily_snapshot(candidates):
    """Fetch stock/index snapshot from TWELVEDATA time_series endpoint."""

    for ticker in candidates:
        payload = _get_TWELVEDATA_json(
            path="/time_series",
            params={
                'symbol': ticker,
                'interval': '1day',
                'outputsize': 14,
                'format': 'JSON',
            },
            cache_key=f"TWELVEDATA_daily:{ticker}"
        )
        closes = _extract_TWELVEDATA_daily_closes(payload)
        if len(closes) >= 2:
            return _snapshot_from_closes(closes[-5:])

    return None


def _resolve_yahoo_stock_candidates(symbol):
    """Resolve app symbol to Yahoo ticker candidates."""
    if symbol in YAHOO_STOCK_SYMBOL_MAP:
        return YAHOO_STOCK_SYMBOL_MAP[symbol]
    return [f"{symbol}.NS", symbol]


def _fetch_yahoo_stock_snapshot(candidates):
    """Fetch stock snapshot from Yahoo chart API (quote API is blocked)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://finance.yahoo.com/'
    }
    
    for ticker in candidates:
        cache_key = f"yahoo_quote:{ticker}"
        now = time.time()
        cached = _SNAPSHOT_CACHE.get(cache_key)
        if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
            if cached['data']:
                return cached['data']
            continue

        try:
            # Use chart API instead of quote API (quote API returns 401)
            encoded = quote(ticker, safe='')
            response = _HTTP_SESSION.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}",
                params={'interval': '1d', 'range': '5d'},
                headers=headers,
                timeout=6
            )
            if response.status_code != 200:
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                continue

            payload = response.json()
            result_list = payload.get('chart', {}). get('result', [])
            if not result_list:
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                continue

            quote_data = result_list[0].get('indicators', {}).get('quote', [{}])[0]
            closes = [float(v) for v in quote_data.get('close', []) if v is not None]
            
            if len(closes) < 2:
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                continue

            current = closes[-1]
            previous = closes[-2]
            change_today = ((current - previous) / previous) * 100

            # Calculate 5d change
            start_5d = closes[-5] if len(closes) >= 5 else closes[0]
            change_5d = ((current - start_5d) / start_5d * 100) if start_5d else 0.0

            snapshot = {
                'price': round(current, 2),
                'change_24h': round(change_today, 2),
                'change_period': round(change_5d, 2),
            }
            _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': snapshot}
            return snapshot
        except Exception:
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            continue

    return None


def _fetch_TWELVEDATA_crypto_snapshot(symbol):
    """Fetch crypto snapshot from TWELVEDATA (e.g., BTC/USD, ETH/USD, DOGE/USD)."""
    payload = _get_TWELVEDATA_json(
        path="/time_series",
        params={
            'symbol': symbol,
            'interval': '1day',
            'outputsize': 5,
            'format': 'JSON',
        },
        cache_key=f"TWELVEDATA_crypto:{symbol}"
    )
    if not isinstance(payload, dict):
        return None

    series = payload.get('values') or []
    closes_usd = []
    for row in reversed(series):
        try:
            close = row.get('close')
            if close is not None:
                closes_usd.append(float(close))
        except (TypeError, ValueError):
            continue

    if len(closes_usd) < 2:
        return None

    # Get current and previous price
    current_usd = closes_usd[-1]
    prev_usd = closes_usd[-2]
    
    # Calculate 24h change in percentage
    change_24h = ((current_usd - prev_usd) / prev_usd * 100) if prev_usd else 0.0
    
    # Convert USD to INR using live exchange rate
    usdinr_rate = _get_live_usdinr_rate()
    current_inr = current_usd * usdinr_rate
    
    return {
        'price': round(current_inr, 2),
        'change_24h': round(change_24h, 2),
        'currency': 'INR'
    }


def _fetch_TWELVEDATA_crypto_old(ticker):
    """Fetch crypto snapshot from TWELVEDATA time_series endpoint (OLD METHOD)."""
    payload = _get_TWELVEDATA_json(
        path="/time_series",
        params={
            'symbol': ticker,
            'interval': '1day',
            'outputsize': 14,
            'format': 'JSON',
        },
        cache_key=f"TWELVEDATA_crypto:{ticker}"
    )
    if not isinstance(payload, dict):
        return None

    series = payload.get('values') or []
    closes_usd = []
    for row in reversed(series):
        try:
            close = row.get('close')
            if close is not None:
                closes_usd.append(float(close))
        except (TypeError, ValueError):
            continue

    if len(closes_usd) < 2:
        return None

    # Convert USD to INR using live exchange rate
    usdinr_rate = _get_live_usdinr_rate()
    closes_inr = [value * usdinr_rate for value in closes_usd[-5:]]
    return _snapshot_from_closes(closes_inr)


def _fetch_coingecko_crypto_snapshot():
    """Fetch BTC/ETH/DOGE spot + 24h change from CoinGecko (INR)."""
    cache_key = "coingecko:crypto:inr"
    now = time.time()
    cached = _SNAPSHOT_CACHE.get(cache_key)
    if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
        return cached['data']

    try:
        response = _HTTP_SESSION.get(
            f"{Config.COINGECKO_API_URL}/simple/price",
            params={
                'ids': 'bitcoin,ethereum,dogecoin',
                'vs_currencies': 'inr',
                'include_24hr_change': 'true',
            },
            timeout=6
        )
        if response.status_code != 200:
            _log_throttled(
                'warning',
                f"coingecko:http:{response.status_code}",
                f"CoinGecko request failed: HTTP {response.status_code}"
            )
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        payload = response.json()
        btc = payload.get('bitcoin', {})
        eth = payload.get('ethereum', {})
        doge = payload.get('dogecoin', {})

        result = {
            'bitcoin': {
                'price': round(float(btc.get('inr')), 2),
                'change_24h': round(float(btc.get('inr_24h_change', 0.0)), 2),
                'currency': 'INR'
            },
            'ethereum': {
                'price': round(float(eth.get('inr')), 2),
                'change_24h': round(float(eth.get('inr_24h_change', 0.0)), 2),
                'currency': 'INR'
            },
            'dogecoin': {
                'price': round(float(doge.get('inr')), 2),
                'change_24h': round(float(doge.get('inr_24h_change', 0.0)), 2),
                'currency': 'INR'
            },
        }

        _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': result}
        return result
    except Exception as exc:
        _log_throttled('warning', "coingecko:exception", f"CoinGecko request failed: {str(exc)}")
        _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
        return None


def _fetch_TWELVEDATA_index_snapshot(index_name):
    """Fetch index snapshot via TWELVEDATA ETF proxies."""
    candidates = TWELVEDATA_INDEX_SYMBOLS.get(index_name, [])
    return _fetch_TWELVEDATA_daily_snapshot(candidates)


def _fetch_yahoo_index_snapshot(index_name):
    """Fetch index snapshot from Yahoo chart API."""
    symbol = YAHOO_INDEX_SYMBOLS.get(index_name)
    if not symbol:
        return None

    cache_key = f"yahoo_index:{symbol}"
    now = time.time()
    cached = _SNAPSHOT_CACHE.get(cache_key)
    if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
        return cached['data']

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://finance.yahoo.com/'
    }
    
    try:
        encoded = quote(symbol, safe='')
        response = _HTTP_SESSION.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}",
            params={'interval': '1d', 'range': '5d'},
            headers=headers,
            timeout=6
        )
        if response.status_code != 200:
            _log_throttled(
                'warning',
                f"yahoo_index:http:{symbol}:{response.status_code}",
                f"Yahoo index request failed for {symbol}: HTTP {response.status_code}"
            )
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        payload = response.json()
        result_list = payload.get('chart', {}).get('result', [])
        if not result_list:
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        quote_data = result_list[0].get('indicators', {}).get('quote', [{}])[0]
        closes = [float(v) for v in quote_data.get('close', []) if v is not None]
        if len(closes) < 2:
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        snapshot = _snapshot_from_closes(closes[-5:])
        _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': snapshot}
        return snapshot
    except Exception as exc:
        _log_throttled('warning', f"yahoo_index:exception:{symbol}", f"Yahoo index request failed for {symbol}: {str(exc)}")
        _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
        return None


def _fetch_yahoo_chart_closes(symbol, range_value='5d'):
    """Fetch close series for a Yahoo symbol via chart API."""
    cache_key = f"yahoo_chart:{symbol}:{range_value}"
    now = time.time()
    cached = _SNAPSHOT_CACHE.get(cache_key)
    if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
        return cached['data']

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://finance.yahoo.com/'
    }
    
    try:
        encoded = quote(symbol, safe='')
        response = _HTTP_SESSION.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}",
            params={'interval': '1d', 'range': range_value},
            headers=headers,
            timeout=6
        )
        if response.status_code != 200:
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        payload = response.json()
        result_list = payload.get('chart', {}).get('result', [])
        if not result_list:
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

        quote_data = result_list[0].get('indicators', {}).get('quote', [{}])[0]
        closes = [float(v) for v in quote_data.get('close', []) if v is not None]
        _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': closes}
        return closes
    except Exception:
        _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
        return None


def _build_fallback_stock_quote(stock):
    """Build deterministic fallback quote when live providers fail."""
    stock_copy = stock.copy()
    anchor_price = FALLBACK_PRICE_ANCHORS.get(stock['symbol'], stock['base_price'])
    stock_copy['current_price'] = round(anchor_price, 2)
    stock_copy['change_24h'] = 0.0
    stock_copy['change_5d'] = 0.0
    stock_copy['data_source'] = 'fallback'
    return stock_copy


def _attach_supplemental_metrics(stock_copy):
    """Keep supplemental metrics available for watchlist/search UI."""
    # Values stay simulated for now; these are not part of live quote feeds.
    stock_copy['pe_ratio'] = round(random.uniform(15, 35), 2)
    stock_copy['dividend_yield'] = round(random.uniform(0.5, 7), 2)
    stock_copy['market_cap'] = random.choice(['Large Cap', 'Mid Cap', 'Small Cap'])
    return stock_copy


class MarketDataCollector:
    """Fetch real-time market data from multiple sources"""

    def __init__(self):
        self.TWELVEDATA_api_key = Config.TWELVEDATA_API_KEY
        self.goldapi_api_key = Config.GOLDAPI_API_KEY
        self.cache = {}
        self.cache_timestamp = {}
    
    def get_gold_prices(self):
        """Fetch gold and silver prices from MetalPriceAPI (primary) or GoldAPI."""
        try:
            # Try MetalPriceAPI first (primary)
            metal_prices = self._get_metalpriceapi_gold_prices()
            if metal_prices:
                return metal_prices

            # Fallback to GoldAPI
            gold_prices = self._get_goldapi_gold_prices()
            if gold_prices:
                return gold_prices

            # Fallback to Yahoo Finance
            yahoo_prices = self._get_yahoo_gold_prices()
            if yahoo_prices:
                return yahoo_prices

            return self._get_default_prices()
        
        except Exception as e:
            logger.error(f"Error fetching gold prices: {str(e)}")
            return self._get_default_prices()
    
    def _get_metalpriceapi_gold_prices(self):
        """Get gold/silver prices from MetalPriceAPI (PRIMARY SOURCE)."""
        api_key = Config.METALPRICEAPI_API_KEY
        if not api_key:
            return None
        
        cache_key = "metalpriceapi:INR:XAUXAG"
        now = time.time()
        cached = _SNAPSHOT_CACHE.get(cache_key)
        if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
            return cached['data']
        
        try:
            response = _HTTP_SESSION.get(
                f"{Config.METALPRICEAPI_API_URL}/latest",
                params={
                    'api_key': api_key,
                    'base': 'INR',
                    'currencies': 'XAU,XAG'
                },
                timeout=6
            )
            
            if response.status_code != 200:
                _log_throttled(
                    'warning',
                    f"metalpriceapi:http:{response.status_code}",
                    f"MetalPriceAPI request failed: HTTP {response.status_code}"
                )
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                return None
            
            payload = response.json()
            
            if not payload.get('success'):
                _log_throttled('warning', 'metalpriceapi:invalid_response', f"MetalPriceAPI invalid response: {payload}")
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                return None
            
            rates = payload.get('rates', {})
            
            # INRXAU is price per ounce, convert to per gram (÷ 31.1035)
            gold_inr_oz = float(rates.get('INRXAU', 0))
            silver_inr_oz = float(rates.get('INRXAG', 0))
            
            if gold_inr_oz <= 0 or silver_inr_oz <= 0:
                _log_throttled('warning', 'metalpriceapi:invalid_rates', f"Invalid rates from MetalPriceAPI: {rates}")
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                return None
            
            # Convert from per ounce to per gram
            gold_inr_price = round(gold_inr_oz / 31.1035, 2)
            silver_inr_price = round(silver_inr_oz / 31.1035, 2)
            
            result = {
                'gold_price_24k': gold_inr_price,
                'silver_price_999': silver_inr_price,
                'currency': 'INR',
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'source': 'metalpriceapi'
            }
            
            _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': result}
            return result
            
        except Exception as e:
            _log_throttled('warning', f"metalpriceapi:exception", f"MetalPriceAPI request failed: {str(e)}")
            _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
            return None

    def _get_goldapi_gold_prices(self):
        """Get XAU/XAG to INR rates using GoldAPI as primary gold source."""
        global _GOLDAPI_COOLDOWN_UNTIL

        now = time.time()
        if now < _GOLDAPI_COOLDOWN_UNTIL:
            return None

        if not self.goldapi_api_key:
            _log_throttled('warning', 'goldapi:no_key', "GOLDAPI_API_KEY is not configured")
            return None

        cache_key = "goldapi:INR:XAUXAG"
        cached = _SNAPSHOT_CACHE.get(cache_key)
        if cached and (now - cached['ts'] < _TWELVEDATA_TTL_SECONDS):
            payload = cached['data']
        else:
            try:
                headers = {'x-access-token': self.goldapi_api_key}
                gold_response = _HTTP_SESSION.get(f"{Config.GOLDAPI_API_URL}/XAU/INR", headers=headers, timeout=8)
                silver_response = _HTTP_SESSION.get(f"{Config.GOLDAPI_API_URL}/XAG/INR", headers=headers, timeout=8)

                use_usd_fallback = (
                    gold_response.status_code in (401, 403, 404) or
                    silver_response.status_code in (401, 403, 404)
                )
                if use_usd_fallback:
                    gold_response = _HTTP_SESSION.get(f"{Config.GOLDAPI_API_URL}/XAU/USD", headers=headers, timeout=8)
                    silver_response = _HTTP_SESSION.get(f"{Config.GOLDAPI_API_URL}/XAG/USD", headers=headers, timeout=8)

                if gold_response.status_code != 200 or silver_response.status_code != 200:
                    if gold_response.status_code in (401, 403) or silver_response.status_code in (401, 403):
                        _GOLDAPI_COOLDOWN_UNTIL = now + 86400
                    else:
                        _log_throttled(
                            'warning',
                            f"goldapi:http:{gold_response.status_code}:{silver_response.status_code}",
                            f"GoldAPI request failed: XAU HTTP {gold_response.status_code}, XAG HTTP {silver_response.status_code}"
                        )
                    _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                    return None

                payload = {'gold': gold_response.json(), 'silver': silver_response.json()}
                _SNAPSHOT_CACHE[cache_key] = {'ts': now, 'data': payload}
            except Exception as exc:
                # Timeout/network issue: back off for 10 minutes before retry.
                _GOLDAPI_COOLDOWN_UNTIL = now + 600
                _log_throttled('warning', "goldapi:exception", f"GoldAPI request failed: {str(exc)}")
                _SNAPSHOT_CACHE[cache_key] = {'ts': now - (_TWELVEDATA_TTL_SECONDS - _FAIL_TTL_SECONDS), 'data': None}
                return None

        if payload is None:
            return None

        gold_payload = payload.get('gold', {}) if isinstance(payload, dict) else {}
        silver_payload = payload.get('silver', {}) if isinstance(payload, dict) else {}

        try:
            # Prefer provider gram metric, fallback to ounce/31.1035 conversion.
            gold_inr_price = gold_payload.get('price_gram_24k')
            if gold_inr_price is None:
                gold_oz_price = float(gold_payload.get('price'))
                gold_currency = str(gold_payload.get('currency', '')).upper()
                if gold_currency == 'USD':
                    gold_oz_price *= USDINR_FALLBACK
                gold_inr_price = gold_oz_price / 31.1035

            silver_inr_price = silver_payload.get('price_gram_999')
            if silver_inr_price is None:
                silver_oz_price = float(silver_payload.get('price'))
                silver_currency = str(silver_payload.get('currency', '')).upper()
                if silver_currency == 'USD':
                    silver_oz_price *= USDINR_FALLBACK
                silver_inr_price = silver_oz_price / 31.1035

            gold_inr_price = round(float(gold_inr_price), 2)
            silver_inr_price = round(float(silver_inr_price), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            _log_throttled('warning', "goldapi:invalid_rates", f"Invalid GoldAPI rate values: {payload}")
            return None

        return {
            'gold_price_24k': gold_inr_price,
            'silver_price_999': silver_inr_price,
            'currency': 'INR',
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }

    def _get_yahoo_gold_prices(self):
        """Fallback live metals from Yahoo futures when GoldAPI is unavailable."""
        try:
            gold_closes = _fetch_yahoo_chart_closes("GC=F", range_value='5d')
            silver_closes = _fetch_yahoo_chart_closes("SI=F", range_value='5d')
            usdinr_closes = _fetch_yahoo_chart_closes("INR=X", range_value='5d')

            if not gold_closes or not silver_closes or not usdinr_closes:
                return None

            gold_usd_oz = float(gold_closes[-1])
            silver_usd_oz = float(silver_closes[-1])
            usdinr = float(usdinr_closes[-1])

            gold_inr_price = round((gold_usd_oz * usdinr) / 31.1035, 2)
            silver_inr_price = round((silver_usd_oz * usdinr) / 31.1035, 2)

            return {
                'gold_price_24k': gold_inr_price,
                'silver_price_999': silver_inr_price,
                'currency': 'INR',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    
    def _get_default_prices(self):
        """Return realistic fallback prices when API fails"""
        # Realistic fallback anchors to avoid large mismatch in cached mode.
        base_price = 15333.72
        silver_base_price = 171.50
        variance = random.uniform(-0.2, 0.2)
        silver_variance = random.uniform(-0.4, 0.4)
        
        return {
            'gold_price_24k': round(base_price * (1 + variance/100), 2),
            'silver_price_999': round(silver_base_price * (1 + silver_variance/100), 2),
            'currency': 'INR',
            'timestamp': datetime.now().isoformat(),
            'status': 'cached'
        }
    
    def get_crypto_prices(self):
        """Fetch Bitcoin, Ethereum, Dogecoin prices from TWELVEDATA (primary) or CoinGecko."""
        try:
            # Try TWELVEDATA first (primary source)
            if self.TWELVEDATA_api_key:
                btc_td = _fetch_TWELVEDATA_crypto_snapshot('BTC/USD')
                eth_td = _fetch_TWELVEDATA_crypto_snapshot('ETH/USD')
                doge_td = _fetch_TWELVEDATA_crypto_snapshot('DOGE/USD')
                
                if btc_td and eth_td and doge_td:
                    # Add source tag to each crypto
                    btc_td['source'] = 'twelvedata'
                    eth_td['source'] = 'twelvedata'
                    doge_td['source'] = 'twelvedata'
                    
                    return {
                        'bitcoin': btc_td,
                        'ethereum': eth_td,
                        'dogecoin': doge_td,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success',
                        'source': 'twelvedata'
                    }
            
            # Fallback to CoinGecko
            live = _fetch_coingecko_crypto_snapshot()
            btc_live = (live or {}).get('bitcoin')
            eth_live = (live or {}).get('ethereum')
            doge_live = (live or {}).get('dogecoin')

            if (
                _is_reasonable_crypto_snapshot('bitcoin', btc_live) and
                _is_reasonable_crypto_snapshot('ethereum', eth_live) and
                _is_reasonable_crypto_snapshot('dogecoin', doge_live)
            ):
                return {
                    'bitcoin': {
                        'price': btc_live['price'],
                        'change_24h': btc_live['change_24h'],
                        'currency': 'INR',
                        'source': 'coingecko'
                    },
                    'ethereum': {
                        'price': eth_live['price'],
                        'change_24h': eth_live['change_24h'],
                        'currency': 'INR',
                        'source': 'coingecko'
                    },
                    'dogecoin': {
                        'price': doge_live['price'],
                        'change_24h': doge_live['change_24h'],
                        'currency': 'INR',
                        'source': 'coingecko'
                    },
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success',
                    'source': 'coingecko'
                }

            # Fallback snapshot if live API is unavailable
            btc_base = 6296180.03
            eth_base = 255000
            doge_base = 8.2

            btc_price = btc_base * (1 + random.uniform(-0.002, 0.002))
            eth_price = eth_base * (1 + random.uniform(-0.006, 0.006))
            doge_price = doge_base * (1 + random.uniform(-0.012, 0.012))
            
            return {
                'bitcoin': {
                    'price': round(btc_price, 2),
                    'change_24h': round(random.uniform(2.4, 3.6), 2),
                    'currency': 'INR'
                },
                'ethereum': {
                    'price': round(eth_price, 2),
                    'change_24h': round(random.uniform(-2, 2), 2),
                    'currency': 'INR'
                },
                'dogecoin': {
                    'price': round(doge_price, 2),
                    'change_24h': round(random.uniform(-5, 5), 2),
                    'currency': 'INR'
                },
                'timestamp': datetime.now().isoformat(),
                'status': 'cached',
                'source': 'fallback'
            }
        
        except Exception as e:
            logger.error(f"Error fetching crypto prices: {str(e)}")
            return {
                'bitcoin': {'price': 6296180.03, 'change_24h': 3.08, 'currency': 'INR'},
                'ethereum': {'price': 255000, 'change_24h': -0.6, 'currency': 'INR'},
                'dogecoin': {'price': 8.2, 'change_24h': 0.9, 'currency': 'INR'},
                'timestamp': datetime.now().isoformat(),
                'status': 'cached',
                'source': 'fallback'
            }
    
    def get_stock_indices(self):
        """Fetch Indian & Global indices from TWELVEDATA (S&P 500) + Yahoo (Nifty/Sensex)."""
        try:
            # Fetch Nifty & Sensex from Yahoo (Indian indices)
            nifty_live = _fetch_yahoo_index_snapshot('nifty_50')
            sensex_live = _fetch_yahoo_index_snapshot('sensex')
            
            # Fetch S&P 500 from TWELVEDATA (more accurate for US indices)
            sp500_live = None
            if self.TWELVEDATA_api_key:
                sp500_td = _fetch_TWELVEDATA_daily_snapshot(['SPY'])
                if sp500_td:
                    sp500_live = sp500_td
            
            # Fallback to Yahoo if TWELVEDATA fails
            if not sp500_live:
                sp500_live = _fetch_yahoo_index_snapshot('sp500')

            if nifty_live and sensex_live and sp500_live:
                return {
                    'nifty_50': {
                        'price': nifty_live['price'],
                        'change_5d': nifty_live['change_period']
                    },
                    'sensex': {
                        'price': sensex_live['price'],
                        'change_5d': sensex_live['change_period']
                    },
                    'sp500': {
                        'price': sp500_live['price'],
                        'change_5d': sp500_live['change_period']
                    },
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                }

            nifty_base = 24450.45
            sensex_base = 80500
            sp500_base = 6740.02

            nifty_price = nifty_base * (1 + random.uniform(-0.003, 0.003))
            sensex_price = sensex_base * (1 + random.uniform(-0.003, 0.003))
            sp500_price = sp500_base * (1 + random.uniform(-0.003, 0.003))
            
            return {
                'nifty_50': {
                    'price': round(nifty_price, 2),
                    'change_5d': round(random.uniform(-1, 1), 2)
                },
                'sensex': {
                    'price': round(sensex_price, 2),
                    'change_5d': round(random.uniform(-1, 1), 2)
                },
                'sp500': {
                    'price': round(sp500_price, 2),
                    'change_5d': round(random.uniform(-1, 1), 2)
                },
                'timestamp': datetime.now().isoformat(),
                'status': 'cached'
            }
        
        except Exception as e:
            logger.error(f"Error fetching stock indices: {str(e)}")
            return {
                'nifty_50': {'price': 24450.45, 'change_5d': -1.27},
                'sensex': {'price': 80500, 'change_5d': -0.9},
                'sp500': {'price': 6740.02, 'change_5d': -0.64},
                'timestamp': datetime.now().isoformat(),
                'status': 'cached'
            }
    
    def get_market_summary(self):
        """Get comprehensive market summary"""
        return {
            'gold': self.get_gold_prices(),
            'crypto': self.get_crypto_prices(),
            'indices': self.get_stock_indices(),
            'timestamp': datetime.now().isoformat()
        }


class InvestmentAnalyzer:
    """Analyze market conditions and generate investment recommendations"""
    
    def __init__(self):
        self.market_collector = MarketDataCollector()
    
    def get_investment_recommendations(self, user_balance, spending_data):
        """Generate investment recommendations based on balance and market conditions"""
        try:
            market_data = self.market_collector.get_market_summary()
            
            recommendations = []
            
            # Check Bitcoin opportunity
            if user_balance > 10000:
                btc_change = market_data['crypto']['bitcoin']['change_24h']
                if btc_change < -2:  # Bitcoin down >2%
                    recommendations.append({
                        'type': 'crypto',
                        'asset': 'Bitcoin',
                        'signal': 'BUY',
                        'reason': f'Bitcoin is down {abs(btc_change):.2f}% - potential buying opportunity',
                        'min_amount': 5000,
                        'priority': 'high' if btc_change < -5 else 'medium'
                    })
            
            # Check Gold opportunity
            if user_balance > 5000:
                recommendations.append({
                    'type': 'precious',
                    'asset': 'Gold (24K)',
                    'signal': 'HOLD',
                    'reason': 'Gold remains a stable hedge against inflation',
                    'current_price': market_data['gold']['gold_price_24k'],
                    'priority': 'medium'
                })
            
            # Check Stock market
            nifty_change = market_data['indices']['nifty_50']['change_5d']
            if user_balance > 20000 and nifty_change < -1:
                recommendations.append({
                    'type': 'stock',
                    'asset': 'Nifty 50 SIP',
                    'signal': 'BUY',
                    'reason': f'Nifty 50 correcting {abs(nifty_change):.2f}% - good SIP entry point',
                    'min_sip': 1000,
                    'priority': 'medium'
                })
            
            # Emergency fund check
            total_monthly_expenses = sum(spending_data.get('monthly_expenses', [0])) if spending_data else 0
            emergency_fund_ratio = user_balance / total_monthly_expenses if total_monthly_expenses > 0 else 0
            
            if emergency_fund_ratio < 3:
                recommendations.append({
                    'type': 'savings',
                    'asset': 'Emergency Fund',
                    'signal': 'PRIORITY',
                    'reason': f'Build emergency fund to {3 * total_monthly_expenses:.0f} (3-6 months expenses)',
                    'priority': 'critical'
                })
            
            return recommendations if recommendations else self._get_default_recommendations()
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return self._get_default_recommendations()
    
    def _get_default_recommendations(self):
        """Return default recommendations"""
        return [
            {
                'type': 'savings',
                'asset': 'Emergency Fund',
                'signal': 'PRIORITY',
                'reason': 'Build a 3-6 month emergency fund first',
                'priority': 'critical'
            },
            {
                'type': 'stock',
                'asset': 'SIP in Nifty 50',
                'signal': 'BUY',
                'reason': 'Regular SIP provides rupee cost averaging benefits',
                'priority': 'high'
            }
        ]


def get_market_data():
    """Convenience function to get all market data"""
    collector = MarketDataCollector()
    return collector.get_market_summary()


def get_investment_advice(user_balance, spending_data):
    """Convenience function to get investment advice"""
    analyzer = InvestmentAnalyzer()
    return analyzer.get_investment_recommendations(user_balance, spending_data)


# Stock Database with Indian Blue-Chip stocks
ALL_STOCKS = [
    # IT Sector
    {'symbol': 'TCS', 'name': 'Tata Consultancy Services', 'sector': 'IT', 'base_price': 3850},
    {'symbol': 'INFY', 'name': 'Infosys Limited', 'sector': 'IT', 'base_price': 1895},
    {'symbol': 'WIPRO', 'name': 'Wipro Limited', 'sector': 'IT', 'base_price': 425},
    {'symbol': 'HCL', 'name': 'HCL Technologies', 'sector': 'IT', 'base_price': 1560},
    {'symbol': 'TECHM', 'name': 'Tech Mahindra', 'sector': 'IT', 'base_price': 1245},
    {'symbol': 'LTTS', 'name': 'LT Technology Services', 'sector': 'IT', 'base_price': 4580},
    
    # Banking & Finance
    {'symbol': 'ICICIBANK', 'name': 'ICICI Bank', 'sector': 'Banking', 'base_price': 1095},
    {'symbol': 'HDFC', 'name': 'HDFC Bank', 'sector': 'Banking', 'base_price': 1685},
    {'symbol': 'AXISBANK', 'name': 'Axis Bank', 'sector': 'Banking', 'base_price': 950},
    {'symbol': 'KOTAKBANK', 'name': 'Kotak Mahindra Bank', 'sector': 'Banking', 'base_price': 1865},
    {'symbol': 'SBILIFE', 'name': 'SBI Life Insurance', 'sector': 'Finance', 'base_price': 1580},
    
    # Automotive
    {'symbol': 'MRF', 'name': 'MRF Limited', 'sector': 'Automotive', 'base_price': 138780},
    {'symbol': 'MARUTI', 'name': 'Maruti Suzuki India', 'sector': 'Automotive', 'base_price': 10850},
    {'symbol': 'TATAMOTORS', 'name': 'Tata Motors', 'sector': 'Automotive', 'base_price': 645},
    {'symbol': 'EICHERMOT', 'name': 'Eicher Motors', 'sector': 'Automotive', 'base_price': 4250},
    
    # Energy & Oil
    {'symbol': 'RELIANCE', 'name': 'Reliance Industries', 'sector': 'Energy', 'base_price': 3045},
    {'symbol': 'IOC', 'name': 'Indian Oil Corporation', 'sector': 'Energy', 'base_price': 105},
    {'symbol': 'NTPC', 'name': 'NTPC Limited', 'sector': 'Energy', 'base_price': 245},
    {'symbol': 'POWERGRID', 'name': 'Power Grid Corporation', 'sector': 'Energy', 'base_price': 280},
    
    # Consumer & FMCG
    {'symbol': 'ITC', 'name': 'ITC Limited', 'sector': 'FMCG', 'base_price': 460},
    {'symbol': 'LT', 'name': 'Larsen & Toubro', 'sector': 'Industrial', 'base_price': 2685},
    {'symbol': 'NESTLEIND', 'name': 'Nestle India', 'sector': 'FMCG', 'base_price': 23650},
    {'symbol': 'BRITANNIA', 'name': 'Britannia Industries', 'sector': 'FMCG', 'base_price': 5240},
    {'symbol': 'HINDUNILVR', 'name': 'Hindustan Unilever', 'sector': 'FMCG', 'base_price': 2450},
    
    # Pharmaceuticals
    {'symbol': 'SUNPHARMA', 'name': 'Sun Pharmaceutical', 'sector': 'Pharma', 'base_price': 1200},
    {'symbol': 'CIPLA', 'name': 'Cipla Limited', 'sector': 'Pharma', 'base_price': 1525},
    {'symbol': 'DRREDDY', 'name': 'Dr. Reddy\'s Laboratories', 'sector': 'Pharma', 'base_price': 6845},
    {'symbol': 'LUPIN', 'name': 'Lupin Limited', 'sector': 'Pharma', 'base_price': 885},
    
    # Real Estate & Construction
    {'symbol': 'DLF', 'name': 'DLF Limited', 'sector': 'Real Estate', 'base_price': 660},
    {'symbol': 'ADANIPORTS', 'name': 'Adani Ports', 'sector': 'Industrial', 'base_price': 895},
]

def _build_stock_quote(stock):
    """Build stock quote from live providers with fallback."""
    yahoo_candidates = _resolve_yahoo_stock_candidates(stock['symbol'])
    live = _fetch_yahoo_stock_snapshot(yahoo_candidates)
    if not live:
        TWELVEDATA_candidates = _resolve_TWELVEDATA_stock_candidates(stock['symbol'])
        live = _fetch_TWELVEDATA_daily_snapshot(TWELVEDATA_candidates)

    if live:
        stock_copy = stock.copy()
        stock_copy['current_price'] = live['price']
        stock_copy['change_24h'] = live['change_24h']
        stock_copy['change_5d'] = live['change_period']
        stock_copy['data_source'] = 'live'
    else:
        stock_copy = _build_fallback_stock_quote(stock)

    return _attach_supplemental_metrics(stock_copy)

def search_stocks(query, limit=10):
    """Search stocks by symbol or name"""
    query_lower = query.lower().strip()
    if not query_lower:
        return []
    
    matched = []
    for stock in ALL_STOCKS:
        if (query_lower in stock['symbol'].lower() or 
            query_lower in stock['name'].lower() or
            query_lower in stock['sector'].lower()):
            matched.append(stock)

    if not matched:
        return []

    matched = sorted(matched, key=lambda x: x['symbol'])[:limit]

    # Build quotes concurrently to reduce search latency.
    with ThreadPoolExecutor(max_workers=min(3, len(matched))) as executor:
        results = list(executor.map(_build_stock_quote, matched))

    return results

def get_stock_price(symbol):
    """Get current price for a specific stock"""
    symbol = symbol.upper()
    for stock in ALL_STOCKS:
        if stock['symbol'] == symbol:
            return _build_stock_quote(stock)
    return None

def get_all_sectors():
    """Get all unique sectors"""
    sectors = set()
    for stock in ALL_STOCKS:
        sectors.add(stock['sector'])
    return sorted(list(sectors))





