# Market Glow 買賣平台

這個專案已整理成可直接上傳到 GitHub，並部署到 Streamlit Community Cloud 的版本。

## 目前功能

- 使用者註冊
- 使用帳號與密碼登入
- 刊登商品名稱、價格、描述
- 上傳商品照片
- 放大瀏覽商品圖片
- 在商品圖片下方留言
- 刪除自己的留言
- 賣家回覆留言
- 賣家刪除自己發布的商品
- 瀏覽全部使用者的販售資料
- 搜尋商品
- 依時間或價格排序商品

## 技術架構

- `app.py`
  - Streamlit 主程式
  - 已加入中文註解，方便你後續修改
- `market_glow.db`
  - 執行後自動建立的 SQLite 資料庫
- `requirements.txt`
  - Streamlit 部署依賴
- `.streamlit/config.toml`
  - Streamlit 主題設定

## 在 Visual Studio Code 執行

1. 用 Visual Studio Code 開啟資料夾 `marketplace-app`
2. 開啟終端機
3. 安裝套件：

```bash
pip install -r requirements.txt
```

4. 啟動 Streamlit：

```bash
streamlit run app.py
```

5. 瀏覽器會自動開啟，如果沒有自動開啟，請手動打開終端機顯示的本機網址，通常是：

```text
http://localhost:8501
```

## 上傳到 GitHub

在 `marketplace-app` 資料夾執行：

```bash
git init
git add .
git commit -m "Initial Streamlit marketplace app"
git branch -M main
git remote add origin 你的-github-repo-url
git push -u origin main
```

## 部署到 Streamlit Community Cloud

1. 先把這個專案上傳到 GitHub
2. 打開 [Streamlit Community Cloud](https://share.streamlit.io/)
3. 使用 GitHub 帳號登入
4. 選擇 `New app`
5. Repository 選你的 GitHub 專案
6. Branch 選 `main`
7. Main file path 填入：

```text
app.py
```

8. 按 `Deploy`

部署完成後，就會得到一個可直接開啟的網站網址。

## 重要提醒

- 這個版本使用 SQLite，適合展示、作業、作品集或小型測試專案
- 如果 Streamlit 雲端環境重建或重新部署，資料庫可能會重置
- 如果你要正式長期上線，建議後續改接 Supabase、Firebase 或 PostgreSQL

## 你之後最常會改的地方

- 想改畫面風格：修改 `app.py` 裡的 `inject_custom_css()`
- 想改註冊登入邏輯：修改 `create_user()` 與 `authenticate_user()`
- 想改商品儲存欄位：修改 `init_database()` 與 `save_listing()`
- 想改商品搜尋排序：修改 `render_marketplace()` 裡探索頁那段邏輯
