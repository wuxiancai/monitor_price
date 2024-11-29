#!/bin/bash

echo "清理旧的安装..."
# 删除旧的 ChromeDriver
rm -f /usr/local/bin/chromedriver
rm -f /opt/homebrew/bin/chromedriver

# 获取本地 Chrome 版本
CHROME_VERSION=$(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version | cut -d " " -f3)
echo "检测到 Chrome 版本: $CHROME_VERSION"

# 创建下载目录
mkdir -p drivers

# 下载对应版本的 ChromeDriver
echo "下载 ChromeDriver..."
CHROMEDRIVER_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/mac-arm64/chromedriver-mac-arm64.zip"
curl -L $CHROMEDRIVER_URL -o drivers/chromedriver.zip

# 解压 ChromeDriver
echo "解压 ChromeDriver..."
cd drivers
unzip -o chromedriver.zip
chmod +x chromedriver-mac-arm64/chromedriver

# 创建虚拟环境
echo "创建 Python 虚拟环境..."
cd ..
python3.9 -m venv venv
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip3 install selenium==4.9.1

echo "安装完成！" 