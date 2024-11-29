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
        self.price_font = font.Font(size=18)
        self.setup_ui()
        self.monitoring = False
        self.driver = None
        self.monitor_thread = None
        # 存储上一次的价格数据
        self.last_prices = {}
        # 存储颜色恢复的计时器
        self.color_timers = {}
        logging.info("程序初始化完成")

    def setup_ui(self):
        # 设置护眼背景色
        BG_COLOR = '#E3EDCD'  # 淡绿色护眼色
        FRAME_BG = '#F0F4EA'  # 稍浅一点的护眼色，用于方格背景

        # 第一行：输入框和按钮
        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=10, padx=10, fill='x')
        
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.insert(0, "https://polymarket.com/markets/crypto/bitcoin")
        self.url_entry.pack(side='left', padx=5)
        
        # 使用 tk.Button 代替 ttk.Button 以支持颜色变化
        self.start_btn = tk.Button(
            input_frame, 
            text="开始监控",
            command=self.start_monitoring,
            bg=FRAME_BG,
            relief="raised",
            font=('Arial', 10)
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            input_frame,
            text="停止监控",
            command=self.stop_monitoring,
            bg=FRAME_BG,
            relief="raised",
            font=('Arial', 10)
        )
        self.stop_btn.pack(side='left', padx=5)
        
        # 第二行：标签
        ttk.Label(self.root, text="实时价格监控").pack(pady=10)
        
        # 第三行：价格显示网格
        self.grid_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.grid_frame.pack(padx=10, pady=10, expand=True, fill='both')
        
        # 创建4x10的网格布局
        self.price_labels = []
        for i in range(10):  # 10行
            row_labels = []
            for j in range(4):  # 4列
                cell_frame = tk.Frame(
                    self.grid_frame,
                    relief="solid",
                    borderwidth=1,
                    bg=FRAME_BG
                )
                cell_frame.grid(row=i, column=j, padx=5, pady=5, sticky="nsew")
                
                label = tk.Label(
                    cell_frame,
                    text="-",
                    font=self.price_font,
                    fg='#0066CC',  # 蓝色文字
                    bg=FRAME_BG,   # 方格背景色
                    anchor='center',
                    justify='center',
                    pady=10  # 增加上下间距
                )
                label.pack(expand=True, fill='both', padx=5, pady=5)
                row_labels.append(label)
                
                self.grid_frame.columnconfigure(j, weight=1)
            self.price_labels.append(row_labels)
            self.grid_frame.rowconfigure(i, weight=1)
        
        # 设置整个窗口的背景色
        self.root.configure(bg=BG_COLOR)

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
                
                market_links = market_container.find_elements(By.TAG_NAME, "a")
                logging.info(f"找到 {len(market_links)} 个链接")
                
                valid_links = []
                for link in market_links:
                    href = link.get_attribute('href')
                    if href and '#comments' not in href:
                        valid_links.append(href)
                        logging.debug(f"有效链接: {href}")
                
                logging.info(f"处理 {len(valid_links)} 个有效链接")
                
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
                            
                            # 更新最后的价格
                            self.last_prices[market_id] = (yes_price, no_price)
                            
                            # 构建显示文本，市场名称用黑色
                            display_text = f"{market_id}\n{yes_price}\n{no_price}"
                            
                            # 更新UI并设置颜色
                            self.root.after(0, self.update_price_label, idx, display_text, price_changed)
                            
                    except Exception as e:
                        logging.error(f"处理链接 {href} 时出错: {str(e)}")
                        continue
                
            except Exception as e:
                logging.error(f"监控过程中出错: {str(e)}")
                self.status_label.config(text=f"状态: 监控出错 - {str(e)}")
            
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
                if len(lines) == 3:
                    market_id, yes_price, no_price = lines
                    
                    # 创建带有不同颜色的文本，增加间距
                    if price_changed:
                        display_text = f"{market_id}\n\n"  # 增加空行作为间距
                        display_text += f"{yes_price}\n{no_price}"
                        label.config(text=display_text, fg='red')
                        
                        timer_key = f"{row}_{col}"
                        if timer_key in self.color_timers:
                            self.root.after_cancel(self.color_timers[timer_key])
                        
                        self.color_timers[timer_key] = self.root.after(
                            10000,
                            lambda: self.restore_color(row, col, display_text)
                        )
                    else:
                        # 如果价格没有变化，使用默认颜色
                        display_text = f"{market_id}\n\n{yes_price}\n{no_price}"  # 增加空行作为间距
                        label.config(text=display_text)
                        
                logging.debug(f"更新标签 [{row}][{col}]: {text}")
        except Exception as e:
            logging.error(f"更新标签出错: {str(e)}\n{traceback.format_exc()}")

    def restore_color(self, row, col, text):
        """恢复标签的默认颜色"""
        try:
            if row < len(self.price_labels) and col < len(self.price_labels[row]):
                label = self.price_labels[row][col]
                label.config(fg='#0066CC')  # 恢复为原来的蓝色
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

if __name__ == "__main__":
    try:
        app = MarketMonitor()
        app.run()
    except Exception as e:
        logging.critical(f"程序发生严重错误: {str(e)}\n{traceback.format_exc()}") 