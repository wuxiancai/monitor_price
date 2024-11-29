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
        logging.info("程序初始化完成")

    def setup_ui(self):
        # 第一行：输入框和按钮
        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=10, padx=10, fill='x')
        
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.insert(0, "https://polymarket.com/markets/crypto/bitcoin")
        self.url_entry.pack(side='left', padx=5)
        
        self.start_btn = ttk.Button(input_frame, text="开始监控", command=self.start_monitoring)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(input_frame, text="停止监控", command=self.stop_monitoring)
        self.stop_btn.pack(side='left', padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(self.root, text="状态: 未开始监控")
        self.status_label.pack(pady=5)
        
        # 第二行：标签
        ttk.Label(self.root, text="实时价格监控").pack(pady=10)
        
        # 第三行：价格显示网格
        self.grid_frame = tk.Frame(self.root, bg='white')
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
                    bg='white'
                )
                cell_frame.grid(row=i, column=j, padx=5, pady=5, sticky="nsew")
                
                # 移除 wraplength，让文本自然展开
                label = tk.Label(
                    cell_frame,
                    text="-",
                    font=self.price_font,
                    fg='#0066CC',
                    bg='white',
                    anchor='center',
                    justify='center'
                )
                label.pack(expand=True, fill='both', padx=5, pady=5)
                row_labels.append(label)
                
                # 配置列的权重
                self.grid_frame.columnconfigure(j, weight=1)
            self.price_labels.append(row_labels)
            self.grid_frame.rowconfigure(i, weight=1)
        
        # 设置整个窗口的背景色为白色
        self.root.configure(bg='white')

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
                            # 处理市场ID，移除 "will-" 前缀
                            market_id = href.rstrip('/').split('/')[-1]
                            market_id = market_id.replace('will-', '')
                            
                            yes_price = prices[0].text
                            no_price = prices[1].text
                            display_text = f"{market_id}\n{yes_price}\n{no_price}" #这里不需要 YES 和 NO 了                            
                            logging.debug(f"市场 {market_id} 价格: YES={yes_price}, NO={no_price}")
                            self.root.after(0, self.update_price_label, idx, display_text)
                        
                    except Exception as e:
                        logging.error(f"处理链接 {href} 时出错: {str(e)}")
                        continue
                
            except Exception as e:
                logging.error(f"监控过程中出错: {str(e)}")
                self.status_label.config(text=f"状态: 监控出错 - {str(e)}")
            
            self.root.update()
            time.sleep(5)

    def update_price_label(self, idx, text):
        try:
            row = idx // 4
            col = idx % 4
            if row < len(self.price_labels) and col < len(self.price_labels[row]):
                self.price_labels[row][col].config(text=text)
                logging.debug(f"更新标签 [{row}][{col}]: {text}")
        except Exception as e:
            logging.error(f"更新标签出错: {str(e)}\n{traceback.format_exc()}")

    def start_monitoring(self):
        if not self.monitoring:
            logging.info("开始监控...")
            self.monitoring = True
            self.status_label.config(text="状态: 正在启动监控...")
            if self.setup_driver():
                self.monitor_thread = threading.Thread(target=self.monitor_prices)
                self.monitor_thread.start()
                self.status_label.config(text="状态: 监控进行中")
                logging.info("监控线程已启动")
            else:
                self.monitoring = False
                logging.error("监控启动失败")

    def stop_monitoring(self):
        logging.info("停止监控...")
        self.monitoring = False
        if self.driver:
            self.driver.quit()
        self.status_label.config(text="状态: 已停止监控")
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