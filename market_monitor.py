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

# 创建日志目录
log_dir = 'LOGS'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logging.basicConfig(
    filename=os.path.join(log_dir, f'monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
    level=logging.DEBUG,  # 改为 DEBUG 级别以获取更多信息
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MarketMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Polymarket 监控器")
        # 创建两种不同大小的字体
        self.market_font = font.Font(size=18)  # 市场名称字体
        self.price_font = font.Font(size=28)   # 价格字体大10号
        
        # 定义颜色为类属性
        self.BG_COLOR = '#E3EDCD'  # 淡绿色护眼色
        self.FRAME_BG = '#F0F4EA'  # 稍浅一点的护眼色，用于方格背景
        
        self.setup_ui()
        self.monitoring = False
        self.driver = None
        self.monitor_thread = None
        self.last_prices = {}
        self.color_timers = {}
        logging.info("程序初始化完成")

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
            font=('Arial', 10)
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            input_frame,
            text="停止监控",
            command=self.stop_monitoring,
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 10)
        )
        self.stop_btn.pack(side='left', padx=5)
        
        # 添加快捷按钮
        self.solana_btn = tk.Button(
            input_frame,
            text="Solana",
            command=lambda: self.update_url('solana'),
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 10)
        )
        self.solana_btn.pack(side='left', padx=5)
        
        self.bitcoin_btn = tk.Button(
            input_frame,
            text="Bitcoin",
            command=lambda: self.update_url('bitcoin'),
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 10)
        )
        self.bitcoin_btn.pack(side='left', padx=5)
        
        self.ethereum_btn = tk.Button(
            input_frame,
            text="Ethereum",
            command=lambda: self.update_url('ethereum'),
            bg=self.FRAME_BG,
            relief="raised",
            font=('Arial', 10)
        )
        self.ethereum_btn.pack(side='left', padx=5)
        
        # 第二行：标签
        # ttk.Label(self.root, text="实时价格监控").pack(pady=10)
        
        # 第三行：价格显示网格
        self.grid_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.grid_frame.pack(padx=10, pady=10, expand=True, fill='both')
        
        # 初始化价格标签列表
        self.price_labels = []

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
        while self.monitoring:
            try:
                logging.info("开始获取市场数据...")
                self.driver.get(self.url_entry.get())
                
                time.sleep(2)
                
                logging.info("等待市场容器加载...")
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
                logging.info(f"找到 {num_links} 个有效链接")
                
                # 只在第一次或链接数量变化时创建网格
                current_rows = len(self.price_labels)
                needed_rows = (num_links + 3) // 4
                if current_rows != needed_rows:
                    logging.info(f"需要调整网格大小: 从 {current_rows} 行到 {needed_rows} 行")
                    self.root.after(0, self.create_grid, num_links)
                    time.sleep(0.5)  # 等待网格创建完成
                
                # 处理每个有效链接
                for idx, href in enumerate(valid_links):
                    try:
                        logging.debug(f"处理链接 {idx + 1}: {href}")
                        self.driver.get(href)
                        
                        prices = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, ".c-bjtUDd.c-bjtUDd-ijxkYfH-css")
                            )
                        )
                        
                        if len(prices) >= 2:
                            market_id = href.rstrip('/').split('/')[-1]
                            market_id = market_id.replace('will-', '')
                            
                            yes_price = prices[0].text
                            no_price = prices[1].text
                            
                            # 检查价格是否变化
                            price_changed = False
                            if market_id in self.last_prices:
                                last_yes, last_no = self.last_prices[market_id]
                                if last_yes != yes_price or last_no != no_price:
                                    price_changed = True
                            
                            self.last_prices[market_id] = (yes_price, no_price)
                            display_text = f"{market_id}\n\n{yes_price}\n{no_price}"  # 保持间距一致
                            self.root.after(0, self.update_price_label, idx, display_text, price_changed)
                    
                    except Exception as e:
                        logging.error(f"处理链接 {href} 时出错: {str(e)}")
                        continue
            
            except Exception as e:
                logging.error(f"监控过程中出错: {str(e)}")
            
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
                if len(lines) == 4:  # 4行：市场名称、空行、YES价格、NO价格
                    market_id = lines[0]
                    yes_price = lines[2]
                    no_price = lines[3]
                    
                    # 移除特定前缀.这是为了去掉市场名称中的前缀。
                    market_id = market_id.replace('bitcoin-', '')
                    market_id = market_id.replace('solana-', '')
                    market_id = market_id.replace('ethereum-', '')
                    market_id = market_id.replace('will-', '')  # 保持原有的 will- 替换
                    
                    # 使用不同字体大小创建显示文本
                    display_text = f"{market_id}\n\n{yes_price}   {no_price}"
                    
                    # 配置标签
                    label.config(text=display_text)
                    
                    # 设置字体和颜色
                    if price_changed:
                        label.config(fg='red')
                        timer_key = f"{row}_{col}"
                        if timer_key in self.color_timers:
                            self.root.after_cancel(self.color_timers[timer_key])
                        # 15秒后恢复颜色
                        self.color_timers[timer_key] = self.root.after(
                            15000,
                            lambda: self.restore_color(row, col, display_text)
                        )
                    else:
                        label.config(fg='#0066CC')
                    
                    # 分别设置市场名称和价格的字体大小
                    label.config(font=self.market_font)  # 默认字体
                    
                    # 使用标签的 tag 功能设置不同部分的字体
                    label.config(font=self.price_font)  # 价格使用大字体
                    
                logging.debug(f"更新标签 [{row}][{col}]: {text}")
        except Exception as e:
            logging.error(f"更新标签出错: {str(e)}\n{traceback.format_exc()}")

    def restore_color(self, row, col, text):
        """恢复标签的默认颜色"""
        try:
            if row < len(self.price_labels) and col < len(self.price_labels[row]):
                label = self.price_labels[row][col]
                label.config(text=text, fg='#0066CC')  # 恢复为原来的蓝色
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

    def run(self):
        logging.info("启动主程序...")
        self.root.mainloop()

    def update_url(self, crypto_name):
        """更新URL中的加密货币名称"""
        current_url = self.url_entry.get()
        # 分割URL并替换最后一个部分
        parts = current_url.rstrip('/').split('/')
        parts[-1] = crypto_name
        new_url = '/'.join(parts)
        # 更新输入框
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, new_url)

if __name__ == "__main__":
    try:
        app = MarketMonitor()
        app.run()
    except Exception as e:
        logging.critical(f"程序发生严重错误: {str(e)}\n{traceback.format_exc()}") 