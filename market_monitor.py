import os
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, font
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import traceback
import requests  # 添加到文件开头的导入部分

# 创建日志目录
log_dir = 'LOGS'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logging.basicConfig(
    filename=os.path.join(log_dir, f'monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
    level=logging.ERROR,  # 只记录 ERROR 级别以上的日志
    # level=logging.DEBUG,  # 改为 DEBUG 级别以获取更多信息
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MarketMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Polymarket 监控器")
        # 创建两种不同大小的字体
        self.market_font = font.Font(family='Tahoma', size=24)  # 市场名称字体
        self.price_font = font.Font(family='Arial', size=28)   # 价格字体大10号
        
        # 定义颜色为类属性
        self.BG_COLOR = '#E3EDCD'  # 淡绿色护眼色
        self.FRAME_BG = '#F0F4EA'  # 稍浅一点的护眼色，用于方格背景
        
        self.price_update_interval = 1000  # 每秒更新一次价格
        self.setup_ui()
        self.monitoring = False
        self.driver = None
        self.monitor_thread = None
        self.last_prices = {}
        self.color_timers = {}
        logging.info("程序初始化完成")
        # 启动币安价格更新线程
        self.binance_thread = threading.Thread(target=self.binance_price)
        self.binance_thread.daemon = True  # 设置为守护线程
        self.binance_thread.start()

    def setup_ui(self):
        # 第一行：输入框和按钮
        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=10, padx=10, fill='x')
        
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.insert(0, "https://polymarket.com/markets/crypto/bitcoin")
        self.url_entry.pack(side='left', padx=5)
        
        self.start_btn = tk.Button(
            input_frame, 
            text="开始监控",
            command=self.start_monitoring,
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 16)
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            input_frame,
            text="停止监控",
            command=self.stop_monitoring,
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 16)
        )
        self.stop_btn.pack(side='left', padx=5)
        
        # 添加快捷按钮
        self.solana_btn = tk.Button(
            input_frame,
            text="Solana",
            command=lambda: self.update_url('solana'),
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 16)
        )
        self.solana_btn.pack(side='left', padx=5)
        
        self.bitcoin_btn = tk.Button(
            input_frame,
            text="Bitcoin",
            command=lambda: self.update_url('bitcoin'),
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 16)
        )
        self.bitcoin_btn.pack(side='left', padx=5)
        
        self.ethereum_btn = tk.Button(
            input_frame,
            text="Ethereum",
            command=lambda: self.update_url('ethereum'),
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 16)
        )
        self.ethereum_btn.pack(side='left', padx=5)
        
        # 第二行：标签
        label_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        label_frame.pack(pady=10, fill='x', padx=15)
        
        # 创建三个并排的容器
        left_frame = tk.Frame(label_frame, bg=self.BG_COLOR)
        left_frame.pack(side='left', fill='x', expand=True)
        
        # 中间的日期时间容器
        center_frame = tk.Frame(label_frame, bg=self.BG_COLOR)
        center_frame.pack(side='left', fill='x', padx=20)
        
        # 日期和时间放在同一行
        datetime_frame = tk.Frame(center_frame, bg=self.BG_COLOR)
        datetime_frame.pack(side='top')
        
        self.date_label = tk.Label(
            datetime_frame,
            text="",
            bg=self.BG_COLOR,
            font=('Arial', 22, 'bold'),
            fg='#2E7D32'
        )
        self.date_label.pack(side='left', padx=10)
        
        self.time_label = tk.Label(
            datetime_frame,
            text="",
            bg=self.BG_COLOR,
            font=('Arial', 22, 'bold'),
            fg='#2E7D32' #绿色
        )
        self.time_label.pack(side='left', padx=10)
        
        # 启动时间更新
        self.update_datetime()
        
        right_frame = tk.Frame(label_frame, bg=self.BG_COLOR)
        right_frame.pack(side='right', fill='x')

        # 左侧：实时价格监控
        price_label = tk.Label(
            left_frame, 
            text="", 
            bg=self.BG_COLOR,
            font=('Arial', 16, 'bold'),
            fg='#0066CC'
        )
        price_label.pack(side='left')
        
        self.crypto_label = tk.Label(
            left_frame,
            text="Bitcoin",
            bg=self.BG_COLOR,
            font=('Arial', 28, 'bold'),
            fg='#0066CC' # 蓝色
        )
        self.crypto_label.pack(side='left')

        # 右侧：币安价格
        binance_frame = tk.Frame(right_frame, bg=self.BG_COLOR)
        binance_frame.pack(side='right', padx=20)

        # 创建币安价格标签
        self.binance_labels = {}
        for crypto in ['BTC', 'ETH', 'SOL']:
            label = tk.Label(
                binance_frame,
                text=f"{crypto}: $0",
                bg=self.BG_COLOR,
                font=('Arial', 22, 'bold'),
                fg='#0066CC' # 蓝色
            )
            label.pack(side='left', padx=10)
            self.binance_labels[crypto] = label

        # 第三行：价格显示网格
        self.grid_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.grid_frame.pack(padx=10, pady=10, expand=True, fill='both')
        
        # 初始化价格标签列表
        self.price_labels = []
        
        # 初始化时更新标签
        self.update_crypto_label()

    def create_grid(self, num_links):
        """根据链接数量创建网格"""
        # 清除现有的网格
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        
        # 计算需要的行数（向上取整）
        num_rows = (num_links + 3) // 4  # 4是列数
        
        # 创建新的网格
        self.price_labels = []
        for i in range(num_rows):
            row_labels = []
            for j in range(4):  # 4列
                cell_frame = tk.Frame(
                    self.grid_frame,
                    relief="solid",
                    borderwidth=1,
                    bg=self.FRAME_BG
                )
                cell_frame.grid(row=i, column=j, padx=5, pady=5, sticky="nsew")
                
                label = tk.Label(
                    cell_frame,
                    text="-",
                    font=self.price_font,
                    fg='#0066CC',
                    bg=self.FRAME_BG,
                    anchor='center',
                    justify='center',
                    pady=10
                )
                label.pack(expand=True, fill='both', padx=5, pady=5)
                row_labels.append(label)
                
                self.grid_frame.columnconfigure(j, weight=1)
            self.price_labels.append(row_labels)
            self.grid_frame.rowconfigure(i, weight=1)

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.page_load_strategy = 'eager'
            
            driver_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'drivers/chromedriver-mac-arm64/chromedriver'
            )
            
            logging.info(f"使用 ChromeDriver 路径: {driver_path}")
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logging.info("ChromeDriver 初始化成功")
            return True
        except Exception as e:
            logging.error(f"ChromeDriver 初始化失败: {str(e)}\n{traceback.format_exc()}")
            self.status_label.config(text=f"状态: 驱动初始化失败 - {str(e)}")
            return False

    def monitor_prices(self):
        last_links_check_time = 0  # 记录上次检查链接的时间
        last_links_count = 0       # 记录上次的链接数量
        
        while self.monitoring:
            try:
                current_time = time.time()
                
                # 每10分钟检查一次链接
                if current_time - last_links_check_time >= 600:  # 600秒 = 10分钟
                    self.driver.get(self.url_entry.get())
                    time.sleep(2)
                    
                    market_container = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "markets-grid-container"))
                    )
                    
                    # 获取并过滤链接
                    market_links = market_container.find_elements(By.TAG_NAME, "a")
                    valid_links = []
                    for link in market_links:
                        href = link.get_attribute('href')
                        if href and '#comments' not in href:
                            valid_links.append(href)
                    
                    num_links = len(valid_links)
                    
                    # 检查链接数量是否变化
                    if num_links != last_links_count:
                        # 更新网格
                        self.root.after(0, self.create_grid, num_links)
                        time.sleep(0.5)
                        last_links_count = num_links
                    
                    # 更新链接映射
                    self.market_urls = {}
                    for idx, href in enumerate(valid_links):
                        self.market_urls[idx] = href
                    
                    # 更新检查时间
                    last_links_check_time = current_time
                
                # 获取价格（每5秒一次）
                for idx, href in enumerate(self.market_urls.values()):
                    try:
                        self.driver.get(href)
                        prices = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, ".c-bjtUDd.c-bjtUDd-ijxkYfH-css")
                            )
                        )
                        
                        if len(prices) >= 2:
                            market_id = href.rstrip('/').split('/')[-1]
                            market_id = market_id.replace('will-', '')
                            market_id = market_id.replace('bitcoin-', '')
                            market_id = market_id.replace('solana-', '')
                            market_id = market_id.replace('ethereum-', '')
                            
                            # 移除价格中的美分符号
                            yes_price = prices[0].text.replace('¢', '')
                            no_price = prices[1].text.replace('¢', '')
                            
                            price_changed = False
                            if market_id in self.last_prices:
                                last_yes, last_no = self.last_prices[market_id]
                                if last_yes != yes_price or last_no != no_price:
                                    price_changed = True
                            
                            self.last_prices[market_id] = (yes_price, no_price)
                            display_text = f"{market_id}\n\n{yes_price}\n{no_price}"
                            self.root.after(0, self.update_price_label, idx, display_text, price_changed)
                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                pass
            
            self.root.update()
            time.sleep(5)

    def update_price_label(self, idx, text, price_changed):
        try:
            row = idx // 4
            col = idx % 4
            if row < len(self.price_labels) and col < len(self.price_labels[row]):
                label = self.price_labels[row][col]
                
                # 分割文本
                lines = text.split('\n')
                if len(lines) == 4:
                    market_id = lines[0]
                    yes_price = lines[2]
                    no_price = lines[3]
                    
                    # 移除特定前缀
                    market_id = market_id.replace('bitcoin-', '')
                    market_id = market_id.replace('solana-', '')
                    market_id = market_id.replace('ethereum-', '')
                    market_id = market_id.replace('will-', '')
                    
                    # 使用保存的原始链接
                    market_url = self.market_urls.get(idx, '')
                    
                    # 创建两个标签：一个用于市场名称，一个用于价格
                    market_label = tk.Label(
                        label.master,
                        text=market_id,
                        font=self.market_font,
                        fg='#000000', #使用黑色
                        bg=self.FRAME_BG,
                        anchor='center',
                        justify='center',
                        cursor="hand2"
                    )
                    market_label.pack(side='top', pady=(5, 0))
                    
                    # 绑定点击事件，使用原始链接
                    if market_url:
                        market_label.bind('<Button-1>', lambda e, url=market_url: self.open_browser(url))
                    
                    # 价格标签
                    price_label = tk.Label(
                        label.master,
                        text=f"{yes_price}   {no_price}",
                        font=self.price_font,
                        fg='#0066CC' if not price_changed else 'red',
                        bg=self.FRAME_BG,
                        anchor='center',
                        justify='center'
                    )
                    price_label.pack(side='top', pady=(10, 5))
                    
                    # 删除原标签
                    label.destroy()
                    
                    # 保存新标签的引用
                    self.price_labels[row][col] = (market_label, price_label)
                    
                    # 设置颜色变化计时器
                    if price_changed:
                        timer_key = f"{row}_{col}"
                        if timer_key in self.color_timers:
                            self.root.after_cancel(self.color_timers[timer_key])
                        
                        self.color_timers[timer_key] = self.root.after(
                            15000,
                            lambda: self.restore_color(row, col, market_id, f"{yes_price}   {no_price}")
                        )
        except Exception as e:
            logging.error(f"更新标签��错: {str(e)}\n{traceback.format_exc()}")

    def restore_color(self, row, col, market_id, price_text):
        """恢复标签的默认颜色"""
        try:
            if row < len(self.price_labels) and col < len(self.price_labels[row]):
                market_label, price_label = self.price_labels[row][col]
                price_label.config(fg='#0066CC')  # 恢复价格为蓝色
                timer_key = f"{row}_{col}"
                if timer_key in self.color_timers:
                    del self.color_timers[timer_key]
        except Exception as e:
            logging.error(f"恢复颜色时出错: {str(e)}")

    def start_monitoring(self):
        if not self.monitoring:
            logging.info("开始监控...")
            self.monitoring = True
            # 将开始按钮变为红色
            self.start_btn.configure(fg='red')
            if self.setup_driver():
                self.monitor_thread = threading.Thread(target=self.monitor_prices)
                self.monitor_thread.start()
                logging.info("监控线程已启动")
            else:
                self.monitoring = False
                # 恢复按钮颜色
                self.start_btn.configure(fg='black')
                logging.error("监控启动失败")

    def stop_monitoring(self):
        logging.info("停止监控...")
        self.monitoring = False
        if self.driver:
            self.driver.quit()
        # 恢复开始按钮颜色
        self.start_btn.configure(fg='black')
        logging.info("监控已停止")
        if hasattr(self, 'binance_thread'):
            self.binance_thread = None

    def run(self):
        logging.info("启动主程序...")
        self.root.mainloop()

    def update_url(self, crypto_name):
        """更新URL中的加密货币名称"""
        current_url = self.url_entry.get()
        parts = current_url.rstrip('/').split('/')
        parts[-1] = crypto_name
        new_url = '/'.join(parts)
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, new_url)
        # 立即更新标签
        self.update_crypto_label()

    def update_crypto_label(self, event=None):
        """更新加密货币标签"""
        try:
            url = self.url_entry.get().rstrip('/')
            crypto_name = url.split('/')[-1].capitalize()  # 首字母大写
            self.crypto_label.config(text=crypto_name)
            logging.debug(f"更新加密货币标签为: {crypto_name}")
        except Exception as e:
            logging.error(f"更新加密货币标签出错: {str(e)}")

    def open_browser(self, url):
        """在默认浏览器中打开URL"""
        import webbrowser
        webbrowser.open(url)

    def binance_price(self):
        """实时更新币安价格"""
        while True:
            try:
                response = requests.get('https://api.binance.com/api/v3/ticker/price')
                if response.status_code == 200:
                    prices = {item['symbol']: item['price'] for item in response.json()}
                    
                    # 更新BTC价格
                    if 'BTCUSDT' in prices:
                        btc_price = float(prices['BTCUSDT'])
                        self.root.after(0, lambda: self.binance_labels['BTC'].config(
                            text=f"BTC: ${btc_price:,.0f}"
                        ))
                    
                    # 更新ETH价格
                    if 'ETHUSDT' in prices:
                        eth_price = float(prices['ETHUSDT'])
                        self.root.after(0, lambda: self.binance_labels['ETH'].config(
                            text=f"ETH: ${eth_price:,.0f}"
                        ))
                    
                    # 更新SOL价格
                    if 'SOLUSDT' in prices:
                        sol_price = float(prices['SOLUSDT'])
                        self.root.after(0, lambda: self.binance_labels['SOL'].config(
                            text=f"SOL: ${sol_price:.2f}"
                        ))
            except Exception as e:
                print(f"获取币安价格出错: {str(e)}")
            
            time.sleep(1)  # 每秒更新一次

    def update_datetime(self):
        """更新日期和时间显示"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        self.date_label.config(text=date_str)
        self.time_label.config(text=time_str)
        
        # 每秒更新一次
        self.root.after(1000, self.update_datetime)

if __name__ == "__main__":
    try:
        app = MarketMonitor()
        app.run()
    except Exception as e:
        logging.critical(f"程序发生严重错误: {str(e)}\n{traceback.format_exc()}") 