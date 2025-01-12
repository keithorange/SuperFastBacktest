import asyncio
import json
import os
import shutil
import time
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page
import pyautogui

TIMEFRAME_URLS = {
    '1s': '/TURBOWAVE/0',
    '5s': '/TURBOWAVE/1',
    '15s': '/TURBOWAVE/2',
    '30s': '/TURBOWAVE/3',
    '1m': '/TURBOWAVE/4',
    '5m': '/TURBOWAVE/5'
}

TIMEFRAME_POSITIONS = {
    '1s': (1760, 285),
    '5s': (1760, 308),
    '15s': (1760, 331),
    '30s': (1760, 358),
    '1m': (1760, 379),
    '5m': (1760, 428)
}

class MouseController:
    @staticmethod
    def move_and_click(x: int, y: int, double: bool = False) -> None:
        pyautogui.moveTo(x, y)
        time.sleep(0.1)
        
        if double:
            pyautogui.doubleClick(x=x, y=y)
            time.sleep(0.1)
        else:
            pyautogui.click(x=x, y=y)
        
        time.sleep(0.1)

    @staticmethod
    def drag_left(x: int, y: int, pixels: int = 30) -> None:
        pyautogui.moveTo(x, y)
        pyautogui.dragRel(-pixels, 0, duration=0.5, button='left')


class TurbowaveCandlesFetcher:
    def __init__(self, timeframe: str = '5s'):
        self.timeframe = timeframe
        self.url_pattern = TIMEFRAME_URLS[timeframe]
        self.latest_candles: Optional[List[Dict]] = None

    async def fetch_candles(self) -> Optional[List[Dict]]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Increase page load timeout to 60 seconds
            page.set_default_timeout(60000)
            page.on("response", self.handle_response)
            
            try:
                # More generous timeout for initial page load
                await page.goto('https://solcasino.io/trading/TURBOWAVE', timeout=60000)
                await page.bring_to_front()
                
                MouseController.drag_left(897, 46)

                # Try to close popup, but continue if it fails
                try:
                    await self.close_popup(page)
                except:
                    print("No popup found or failed to close - continuing anyway")
                
                try:
                    await self.select_timeframe(page)
                except:
                    print("Timeframe selection may have failed - continuing anyway")
                
                # Give more time for data to load
                await page.wait_for_timeout(1000)
                
                # If we haven't received data yet but no errors occurred, wait a bit longer
                if not self.latest_candles:
                    print("No data received yet - waiting additional time...")
                    await page.wait_for_timeout(4000)
                
            except Exception as e:
                print(f"Error during page operations: {e}")
                raise e
            finally:
                await browser.close()
            
            return self.latest_candles

    async def close_popup(self, page: Page) -> None:
        try:
            # Increase timeout for popup detection
            popup = await page.wait_for_selector('div[class*="tpTradingTipBigTitle"]', timeout=60000)
            if popup:
                close_btn = await page.query_selector('div[class*="tpPopFtBtn"]')
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(1000)  # Wait after closing
        except:
            # If popup handling fails, we'll just continue
            pass

    async def select_timeframe(self, page: Page) -> None:
        try:
            MouseController.move_and_click(1818, 235)
            await page.wait_for_timeout(400)  # Increased wait time
            
            x, y = TIMEFRAME_POSITIONS[self.timeframe]
            MouseController.move_and_click(x, y)
            await page.wait_for_timeout(400)  # Added wait after selection
        except:
            print("Timeframe selection error - continuing with default timeframe")

    async def handle_response(self, response):
        if self.url_pattern in response.url:
            try:
                data = await response.json()
                if data['code'] == 0 and data['data']['data']:
                    self.latest_candles = data['data']['data']
            except:
                pass

# class TurbowaveCandlesFetcher:
#     def __init__(self, timeframe: str = '5s'):
#         self.timeframe = timeframe
#         self.url_pattern = TIMEFRAME_URLS[timeframe]
#         self.latest_candles: Optional[List[Dict]] = None

#     async def fetch_candles(self) -> Optional[List[Dict]]:
#         async with async_playwright() as p:
#             browser = await p.chromium.launch(headless=False)
#             context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
#             page = await context.new_page()
            
#             page.on("response", self.handle_response)
            
#             await page.goto('https://solcasino.io/trading/TURBOWAVE')
#             await page.bring_to_front()
            
#             MouseController.drag_left(897, 46)

#             await self.close_popup(page)
#             await self.select_timeframe(page)
            
#             await page.wait_for_timeout(4000)
            
#             await browser.close()
            
#             return self.latest_candles

#     async def handle_response(self, response):
#         if self.url_pattern in response.url:
#             try:
#                 data = await response.json()
#                 if data['code'] == 0 and data['data']['data']:
#                     self.latest_candles = data['data']['data']
#             except:
#                 pass

#     async def close_popup(self, page: Page) -> None:
#         try:
#             popup = await page.wait_for_selector('div[class*="tpTradingTipBigTitle"]', timeout=50000)
#             if popup:
#                 close_btn = await page.query_selector('div[class*="tpPopFtBtn"]')
#                 await close_btn.click()
#         except:
#             pass

#     async def select_timeframe(self, page: Page) -> None:
#         MouseController.move_and_click(1818, 235)
#         await page.wait_for_timeout(1000)
        
#         x, y = TIMEFRAME_POSITIONS[self.timeframe]
#         MouseController.move_and_click(x, y)


from datetime import datetime, timedelta
from typing import List, Dict
import json
import json
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import mplfinance as mpf

class LocalCandlesManager:
    def __init__(self, filename: str = 'turbowave_candles.json', timeframe: str = '5s'):
        self.filename = filename
        self.timeframe = timeframe
        self.candles: List[Dict] = self.load_candles()

    def load_candles(self) -> List[Dict]:
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

        
    def save_candles(self) -> None:
        if os.path.exists(self.filename):
            backup_filename = f"{self.filename}_OLDTURBOWAVE"
            shutil.copy2(self.filename, backup_filename)
        with open(self.filename, 'w') as f:
            json.dump(self.candles, f, indent=2)

    def update_candles(self, new_candles: List[Dict]) -> None:
        if not new_candles:
            return

        if not self.candles:
            self.candles = new_candles
        else:
            existing_timestamps = set(candle['time'] for candle in self.candles)
            for candle in new_candles:
                if candle['time'] not in existing_timestamps:
                    self.candles.append(candle)

        self.candles.sort(key=lambda x: x['time'])
        self.check_for_gaps()
        self.save_candles()
        self.graph()

    def check_for_gaps(self) -> None:
        expected_diff = self.get_expected_time_diff()
        for i in range(1, len(self.candles)):
            time1 = datetime.strptime(self.candles[i-1]['time'], '%Y-%m-%d %H:%M:%S')
            time2 = datetime.strptime(self.candles[i]['time'], '%Y-%m-%d %H:%M:%S')
            time_diff = time2 - time1
            if time_diff > expected_diff:
                print(f"\tWARNING: Gap detected between candles at index {i-1} and {i}. "
                                 f"Time difference: {time_diff}, Expected: {expected_diff} (Proceeding Anyway...)\n")

    def get_expected_time_diff(self) -> timedelta:
        timeframe_to_seconds = {
            '1s': 1, '5s': 5, '15s': 15, '30s': 30,
            '1m': 60, '5m': 300
        }
        seconds = timeframe_to_seconds.get(self.timeframe, 5)  # Default to 5s if timeframe not recognized
        return timedelta(seconds=seconds)

    def graph(self) -> None:
        df = pd.DataFrame(self.candles)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close']]

        fig_width, fig_height = 20, 8
        dpi = 300

        mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)

        mpf.plot(df, type='candle', style=s,
                title='TURBOWAVE Candles',
                ylabel='Price',
                figsize=(fig_width, fig_height),
                tight_layout=True,
                scale_padding={'left': 0.1, 'right': 1, 'top': 0.8, 'bottom': 0.8},
                savefig=dict(fname='turbowave_candles.png', dpi=dpi, bbox_inches='tight'),
                warn_too_much_data=len(df) + 1)  # Disable the warning

        print("Enhanced graph saved as turbowave_candles.png")


class TurbowaveManager:
    def __init__(self, update_interval: int = 60 * 30, timeframe: str = '5s'):
        self.update_interval = update_interval
        self.timeframe = timeframe
        self.local_manager = LocalCandlesManager(timeframe=timeframe)

    async def run(self) -> None:
        while True:
            try:
                fetcher = TurbowaveCandlesFetcher(self.timeframe)
                new_candles = await fetcher.fetch_candles()
                if new_candles:
                    self.local_manager.update_candles(new_candles)
                    print("🏆 Data captured and saved!")
                else:
                    print("❌ No data captured")
            except Exception as e:
                print(f"Error occurred: {e}")
            
            print(f"\n\tWaiting {self.update_interval} seconds before next update...")
            await asyncio.sleep(self.update_interval)

if __name__ == "__main__":
    manager = TurbowaveManager()
    asyncio.run(manager.run())
