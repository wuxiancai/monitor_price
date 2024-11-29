import os
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# 配置日志
logging.basicConfig(
    filename=f'monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MarketMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Polymarket 监控器")
        self.setup_ui()
        self.monitoring = False
        self.driver = None
        self.monitor_thread = None
        
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
        self.grid_frame = ttk.Frame(self.root)
        self.grid_frame.pack(padx=10, pady=10)
        
        self.price_labels = []
        for i in range(10):  # 10行
            row_labels = []
            for j in range(4):  # 4列
                label = ttk.Label(self.grid_frame, text="-", width=20, relief="solid")
                label.grid(row=i, column=j, padx=2, pady=2)
                row_labels.append(label)
            self.price_labels.append(row_labels)

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            
            # 使用本地下载的 ChromeDriver
            driver_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'drivers/chromedriver-mac-arm64/chromedriver'
            )
            
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            logging.error(f"Chrome driver 初始化失败: {str(e)}")
            self.status_label.config(text=f"状态: 驱动初始化失败 - {str(e)}")
            return False

    def monitor_prices(self):
        while self.monitoring:
            try:
                self.driver.get(self.url_entry.get())
                market_container = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "markets-grid-container"))
                )
                market_links = market_container.find_elements(By.TAG_NAME, "a")
                
                for idx, link in enumerate(market_links[:10]):
                    href = link.get_attribute('href')
                    self.driver.execute_script(f'window.open("{href}", "_blank");')
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    prices = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "c-bjtUDd-ijxkYfH-css"))
                    )
                    
                    if len(prices) >= 2:
                        yes_price = prices[0].text
                        no_price = prices[1].text
                        self.root.after(0, self.update_price_label, idx, 0, f"YES: {yes_price}")
                        self.root.after(0, self.update_price_label, idx, 1, f"NO: {no_price}")
                    
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    
            except Exception as e:
                logging.error(f"监控过程中出错: {str(e)}")
                self.status_label.config(text=f"状态: 监控出错 - {str(e)}")
            
            self.root.after(5000)  # 5秒更新一次
    
    def update_price_label(self, row, col, text):
        if row < len(self.price_labels) and col < len(self.price_labels[0]):
            self.price_labels[row][col].config(text=text)

    def start_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.status_label.config(text="状态: 正在启动监控...")
            if self.setup_driver():
                self.monitor_thread = threading.Thread(target=self.monitor_prices)
                self.monitor_thread.start()
                self.status_label.config(text="状态: 监控进行中")
            else:
                self.monitoring = False

    def stop_monitoring(self):
        self.monitoring = False
        if self.driver:
            self.driver.quit()
        self.status_label.config(text="状态: 已停止监控")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MarketMonitor()
    app.run() 