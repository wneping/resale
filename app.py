import base64
import hashlib
import html
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "market_glow.db"


def get_connection():
    # Streamlit 會反覆重跑腳本，這樣設定可避免 SQLite 執行緒限制造成錯誤。
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_database():
    # 專案首次啟動時自動建立資料表，方便直接部署使用。
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                account TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                seller_name TEXT NOT NULL,
                title TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT NOT NULL,
                image_base64 TEXT NOT NULL,
                image_mime TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (seller_id) REFERENCES users (id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                parent_comment_id INTEGER,
                FOREIGN KEY (listing_id) REFERENCES listings (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (parent_comment_id) REFERENCES comments (id)
            )
            """
        )

        # 舊資料庫若沒有 parent_comment_id 欄位，這裡會自動補上，避免既有資料失效。
        cursor.execute("PRAGMA table_info(comments)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "parent_comment_id" not in existing_columns:
            cursor.execute("ALTER TABLE comments ADD COLUMN parent_comment_id INTEGER")

        conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(username: str, account: str, password: str):
    created_at = datetime.now().isoformat()
    password_hash = hash_password(password)

    try:
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, account, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, account, password_hash, created_at),
            )
            conn.commit()
        return True, "註冊成功，現在可以登入。"
    except sqlite3.IntegrityError:
        return False, "這個帳號已經存在，請改用其他帳號。"


def authenticate_user(account: str, password: str):
    password_hash = hash_password(password)
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, account
            FROM users
            WHERE account = ? AND password_hash = ?
            """,
            (account, password_hash),
        )
        return cursor.fetchone()


def save_listing(
    seller_id: int,
    seller_name: str,
    title: str,
    price: int,
    description: str,
    image_file,
):
    image_bytes = image_file.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_mime = image_file.type or "image/png"
    created_at = datetime.now().isoformat()

    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO listings (
                seller_id, seller_name, title, price, description, image_base64, image_mime, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (seller_id, seller_name, title, price, description, image_base64, image_mime, created_at),
        )
        conn.commit()


def save_comment(
    listing_id: int,
    user_id: int,
    username: str,
    content: str,
    parent_comment_id: Optional[int] = None,
):
    created_at = datetime.now().isoformat()
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO comments (listing_id, user_id, username, content, created_at, parent_comment_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (listing_id, user_id, username, content, created_at, parent_comment_id),
        )
        conn.commit()


def delete_listing(listing_id: int, seller_id: int):
    # 只允許商品賣家刪除自己的商品，並同步刪掉相關留言，避免殘留無主資料。
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM listings
            WHERE id = ? AND seller_id = ?
            """,
            (listing_id, seller_id),
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            cursor.execute(
                """
                DELETE FROM comments
                WHERE listing_id = ?
                """,
                (listing_id,),
            )
        conn.commit()
    return deleted_count > 0


def delete_comment(comment_id: int, user_id: int):
    # 只允許本人刪除自己的留言；回覆也會一起刪除，避免留下孤兒訊息。
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM comments
            WHERE id = ? AND user_id = ?
            """,
            (comment_id, user_id),
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            cursor.execute(
                """
                DELETE FROM comments
                WHERE parent_comment_id = ?
                """,
                (comment_id,),
            )
        conn.commit()
    return deleted_count > 0


def get_all_listings():
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, seller_id, seller_name, title, price, description, image_base64, image_mime, created_at
            FROM listings
            ORDER BY datetime(created_at) DESC
            """
        )
        return cursor.fetchall()


def get_comments_by_listing_id(listing_id: int):
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, listing_id, user_id, username, content, created_at, parent_comment_id
            FROM comments
            WHERE listing_id = ?
            ORDER BY datetime(created_at) ASC, id ASC
            """,
            (listing_id,),
        )
        return cursor.fetchall()


def group_comments(comments):
    comment_map = {}
    root_comments = []

    for comment in comments:
        item = dict(comment)
        item["replies"] = []
        comment_map[item["id"]] = item

    for comment_id in comment_map:
        item = comment_map[comment_id]
        parent_id = item["parent_comment_id"]
        if parent_id and parent_id in comment_map:
            comment_map[parent_id]["replies"].append(item)
        else:
            root_comments.append(item)

    return root_comments


def get_statistics(listings):
    seller_ids = {listing["seller_id"] for listing in listings}
    latest_time = listings[0]["created_at"] if listings else None
    return {
        "total_listings": len(listings),
        "total_sellers": len(seller_ids),
        "latest_time": latest_time,
    }


def format_currency(value: int) -> str:
    return f"NT$ {value:,}"


def format_datetime(value: Optional[str]) -> str:
    if not value:
        return "尚無資料"
    return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")


def build_image_data_url(image_base64: str, image_mime: str) -> str:
    return f"data:{image_mime};base64,{image_base64}"


def inject_custom_css():
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(246, 210, 183, 0.55), transparent 20%),
                radial-gradient(circle at top right, rgba(243, 195, 154, 0.42), transparent 20%),
                linear-gradient(180deg, #fff8f0 0%, #f6ede3 45%, #efe1d4 100%);
            color: #311f14;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1180px;
        }
        .hero-card {
            padding: 2rem;
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255,249,243,0.96), rgba(255,233,220,0.8));
            box-shadow: 0 22px 65px rgba(84, 53, 29, 0.14);
            border: 1px solid rgba(255,255,255,0.72);
        }
        .hero-title {
            font-size: 3rem;
            font-weight: 800;
            margin: 0.35rem 0 0.75rem 0;
        }
        .hero-subtitle {
            color: #745f51;
            line-height: 1.8;
            margin: 0;
        }
        .eyebrow {
            letter-spacing: 0.18em;
            text-transform: uppercase;
            font-size: 0.78rem;
            color: #8b452b;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem;
            margin-top: 1.4rem;
        }
        .stat-card {
            padding: 1.1rem 1rem;
            border-radius: 22px;
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(255,255,255,0.64);
        }
        .stat-label {
            color: #745f51;
            font-size: 0.92rem;
            margin-bottom: 0.4rem;
        }
        .stat-value {
            font-size: 1.2rem;
            font-weight: 800;
        }
        .card-shell {
            background: rgba(255,252,248,0.76);
            border: 1px solid rgba(255,255,255,0.7);
            border-radius: 26px;
            padding: 1.2rem;
            box-shadow: 0 16px 38px rgba(82,49,20,0.08);
        }
        .listing-card {
            background: rgba(255,251,247,0.97);
            border-radius: 24px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.74);
            box-shadow: 0 16px 38px rgba(82,49,20,0.1);
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .listing-meta {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 0.75rem;
        }
        .seller-badge {
            display: inline-block;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.86);
            color: #8b452b;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .price-tag {
            color: #265e45;
            font-weight: 800;
            font-size: 1.08rem;
        }
        .listing-title {
            font-size: 1.2rem;
            font-weight: 800;
            margin: 0.25rem 0 0.55rem 0;
        }
        .listing-description {
            color: #745f51;
            line-height: 1.8;
            margin: 0;
        }
        .listing-time {
            margin-top: 0.9rem;
            color: #745f51;
            font-size: 0.9rem;
        }
        .comment-box {
            background: rgba(255,255,255,0.78);
            border-radius: 18px;
            padding: 0.85rem 1rem;
            margin-top: 0.65rem;
            border: 1px solid rgba(255,255,255,0.72);
        }
        .reply-box {
            margin-left: 1.2rem;
            border-left: 3px solid rgba(204, 110, 73, 0.25);
            padding-left: 0.9rem;
        }
        .comment-user {
            color: #8b452b;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .comment-time {
            color: #745f51;
            font-size: 0.86rem;
            margin-top: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(listings):
    stats = get_statistics(listings)
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="eyebrow">MARKET GLOW</div>
            <div class="hero-title">二手商品的買賣平台</div>
            <p class="hero-subtitle">此網站只透過7-11賣貨便交易, 由賣家開下單資訊,拒絕詐騙
            </p>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">商品總數</div>
                    <div class="stat-value">{stats["total_listings"]}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">賣家數量</div>
                    <div class="stat-value">{stats["total_sellers"]}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">最新刊登</div>
                    <div class="stat-value">{format_datetime(stats["latest_time"])}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ensure_session_state():
    if "current_user" not in st.session_state:
        st.session_state.current_user = None


def render_auth_sidebar():
    st.sidebar.markdown("## 會員中心")
    current_user = st.session_state.current_user

    if current_user:
        st.sidebar.success(f"目前登入：{current_user['username']}")
        if st.sidebar.button("登出", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()
        return

    auth_mode = st.sidebar.radio("選擇操作", ["登入", "註冊"], horizontal=True)

    if auth_mode == "登入":
        with st.sidebar.form("login_form"):
            account = st.text_input("帳號")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("立即登入", use_container_width=True)

        if submitted:
            user = authenticate_user(account.strip(), password.strip())
            if user:
                st.session_state.current_user = dict(user)
                st.sidebar.success("登入成功。")
                st.rerun()
            else:
                st.sidebar.error("帳號或密碼錯誤，請重新確認。")
    else:
        with st.sidebar.form("register_form"):
            username = st.text_input("使用者名稱")
            account = st.text_input("帳號")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("建立帳號", use_container_width=True)

        if submitted:
            if len(password.strip()) < 6:
                st.sidebar.error("密碼至少需要 6 碼。")
            elif not username.strip() or not account.strip():
                st.sidebar.error("請完整填寫使用者名稱與帳號。")
            else:
                ok, message = create_user(username.strip(), account.strip(), password.strip())
                if ok:
                    st.sidebar.success(message)
                else:
                    st.sidebar.error(message)


def render_listing_form():
    st.markdown("### 刊登商品")
    st.caption("登入後即可上傳照片、輸入販售描述，送出後會同步顯示到探索區。")

    current_user = st.session_state.current_user
    if not current_user:
        st.info("請先在左側欄註冊或登入後再刊登商品。")
        return

    with st.form("listing_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("商品名稱", placeholder="例如：近全新藍牙耳機")
        with col2:
            price = st.number_input("價格", min_value=0, step=100, value=0)

        description = st.text_area(
            "販售描述",
            height=160,
            placeholder="請輸入商品狀況、配件內容、面交或寄送方式...",
        )
        image_file = st.file_uploader("商品照片", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("刊登商品", use_container_width=True)

    if submitted:
        if not title.strip() or not description.strip():
            st.error("請完整填寫商品名稱與販售描述。")
        elif image_file is None:
            st.error("請上傳商品圖片。")
        else:
            save_listing(
                seller_id=current_user["id"],
                seller_name=current_user["username"],
                title=title.strip(),
                price=int(price),
                description=description.strip(),
                image_file=image_file,
            )
            st.success("商品刊登成功，已更新到下方商品列表。")
            st.rerun()


def render_single_comment(comment, listing, current_user, scope, is_reply=False):
    safe_content = html.escape(comment["content"])
    safe_username = html.escape(comment["username"])
    safe_time = html.escape(format_datetime(comment["created_at"]))

    if is_reply:
        st.markdown('<div class="reply-box">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="comment-box">
            <div class="comment-user">{safe_username}</div>
            <div>{safe_content}</div>
            <div class="comment-time">{safe_time}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_columns = st.columns([1, 1, 4])

    if current_user and current_user["id"] == comment["user_id"]:
        if action_columns[0].button(
            "刪除留言", key=f"delete_comment_{scope}_{comment['id']}"
        ):
            if delete_comment(comment["id"], current_user["id"]):
                st.success("留言已刪除。")
                st.rerun()
            else:
                st.error("刪除失敗，請重新整理後再試。")

    # 只有商品賣家能回覆根留言，讓討論層級保持簡潔。
    is_seller = current_user and current_user["id"] == listing["seller_id"]
    if is_seller and not is_reply:
        with action_columns[1].popover("賣家回覆"):
            with st.form(f"reply_form_{scope}_{comment['id']}", clear_on_submit=True):
                reply_content = st.text_area(
                    "回覆內容",
                    height=100,
                    placeholder="請輸入回覆內容...",
                    key=f"reply_content_{scope}_{comment['id']}",
                )
                reply_submitted = st.form_submit_button("送出回覆", use_container_width=True)

            if reply_submitted:
                if not reply_content.strip():
                    st.warning("回覆內容不能空白。")
                else:
                    save_comment(
                        listing_id=listing["id"],
                        user_id=current_user["id"],
                        username=current_user["username"],
                        content=reply_content.strip(),
                        parent_comment_id=comment["id"],
                    )
                    st.success("回覆已送出。")
                    st.rerun()

    if is_reply:
        st.markdown("</div>", unsafe_allow_html=True)


def render_comments_section(listing, scope):
    st.markdown("#### 留言區")
    current_user = st.session_state.current_user
    comments = group_comments(get_comments_by_listing_id(listing["id"]))

    if not comments:
        st.caption("目前還沒有留言，歡迎留下第一則訊息。")
    else:
        for comment in comments:
            render_single_comment(comment, listing, current_user, scope, is_reply=False)
            for reply in comment["replies"]:
                render_single_comment(reply, listing, current_user, scope, is_reply=True)

    if not current_user:
        st.info("登入後才能留言。")
        return

    with st.form(f"comment_form_{scope}_{listing['id']}", clear_on_submit=True):
        content = st.text_area(
            "留下你的留言",
            height=110,
            placeholder="例如：請問還有附原廠盒嗎？",
            key=f"comment_input_{scope}_{listing['id']}",
        )
        submitted = st.form_submit_button("送出留言", use_container_width=True)

    if submitted:
        if not content.strip():
            st.warning("留言內容不能空白。")
        else:
            save_comment(
                listing_id=listing["id"],
                user_id=current_user["id"],
                username=current_user["username"],
                content=content.strip(),
            )
            st.success("留言已送出。")
            st.rerun()


def render_listing_card(listing, scope):
    current_user = st.session_state.current_user
    st.markdown('<div class="listing-card">', unsafe_allow_html=True)
    st.image(
        build_image_data_url(listing["image_base64"], listing["image_mime"]),
        use_container_width=True,
    )
    st.markdown(
        f"""
        <div class="listing-body">
            <div class="listing-meta">
                <span class="seller-badge">賣家：{html.escape(listing["seller_name"])}</span>
                <span class="price-tag">{format_currency(listing["price"])}</span>
            </div>
            <div class="listing-title">{html.escape(listing["title"])}</div>
            <p class="listing-description">{html.escape(listing["description"])}</p>
            <div class="listing-time">刊登時間：{format_datetime(listing["created_at"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if current_user and current_user["id"] == listing["seller_id"]:
        if st.button("刪除此商品", key=f"delete_listing_{scope}_{listing['id']}"):
            if delete_listing(listing["id"], current_user["id"]):
                st.success("商品已刪除，相關留言也已一併移除。")
                st.rerun()
            else:
                st.error("刪除失敗，請重新整理後再試。")

    # expander 可讓使用者在需要時再展開大圖與互動區，維持列表瀏覽的清爽感。
    with st.expander("放大圖片與查看留言", expanded=False):
        st.image(
            build_image_data_url(listing["image_base64"], listing["image_mime"]),
            caption=f"{listing['title']}｜大圖瀏覽",
            use_container_width=True,
        )
        render_comments_section(listing, scope)

    st.markdown("</div>", unsafe_allow_html=True)


def render_listing_cards(listings, scope):
    if not listings:
        st.info("目前還沒有任何商品刊登，登入後就能成為第一位賣家。")
        return

    columns = st.columns(2)
    for index, listing in enumerate(listings):
        with columns[index % 2]:
            render_listing_card(listing, scope)


def render_marketplace():
    listings = get_all_listings()
    render_hero(listings)
    st.write("")

    tab_publish, tab_browse = st.tabs(["刊登中心", "探索全部商品"])

    with tab_publish:
        st.markdown('<div class="card-shell">', unsafe_allow_html=True)
        render_listing_form()
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
        st.markdown("### 最新商品")
        render_listing_cards(listings[:6], "latest")

    with tab_browse:
        st.markdown("### 全站商品探索")
        st.caption("可以依關鍵字搜尋商品名稱、描述或賣家名稱，並切換排序方式。")

        search_col, sort_col = st.columns([2, 1])
        with search_col:
            keyword = st.text_input("搜尋", placeholder="搜尋商品名稱、描述或賣家", key="search")
        with sort_col:
            sort_mode = st.selectbox("排序", ["最新刊登", "價格高到低", "價格低到高"])

        filtered_listings = []
        lowered_keyword = keyword.strip().lower()
        for listing in listings:
            haystack = f"{listing['title']} {listing['description']} {listing['seller_name']}".lower()
            if lowered_keyword in haystack:
                filtered_listings.append(listing)

        if sort_mode == "價格高到低":
            filtered_listings.sort(key=lambda item: item["price"], reverse=True)
        elif sort_mode == "價格低到高":
            filtered_listings.sort(key=lambda item: item["price"])

        st.info(f"目前顯示 {len(filtered_listings)} 筆商品。")
        render_listing_cards(filtered_listings, "browse")


def main():
    st.set_page_config(
        page_title="閒逛好去處",
        page_icon="🛍️",
        layout="wide",
    )
    init_database()
    ensure_session_state()
    inject_custom_css()
    render_auth_sidebar()
    render_marketplace()


if __name__ == "__main__":
    main()
