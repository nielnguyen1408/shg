# Chế độ tĩnh (như hiện tại, không chạy JS)
pip install requests beautifulsoup4 lxml pandas openpyxl
python sunhouse_crawler.py -i product.md -o sunhouse_products.xlsx

# Chế độ có JS (để bắt slider)
pip install playwright requests beautifulsoup4 lxml pandas openpyxl
playwright install chromium
python sunhouse_crawler.py -i product.md -o sunhouse_products.xlsx --js
