// 將共用資料邏輯抽到這裡，主頁與探索頁都能重用，後續改 API 也比較集中。
const STORAGE_KEYS = {
  users: "marketGlowUsers",
  currentUser: "marketGlowCurrentUser",
  listings: "marketGlowListings",
};

function getStorageData(key, fallbackValue) {
  const rawValue = localStorage.getItem(key);

  try {
    return rawValue ? JSON.parse(rawValue) : fallbackValue;
  } catch (error) {
    console.warn(`讀取 ${key} 失敗，已改用預設值。`, error);
    return fallbackValue;
  }
}

function setStorageData(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

const MarketGlowStore = {
  getUsers() {
    return getStorageData(STORAGE_KEYS.users, []);
  },

  setUsers(users) {
    setStorageData(STORAGE_KEYS.users, users);
  },

  getCurrentUser() {
    return getStorageData(STORAGE_KEYS.currentUser, null);
  },

  setCurrentUser(user) {
    setStorageData(STORAGE_KEYS.currentUser, user);
  },

  clearCurrentUser() {
    localStorage.removeItem(STORAGE_KEYS.currentUser);
  },

  getListings() {
    return getStorageData(STORAGE_KEYS.listings, []);
  },

  setListings(listings) {
    setStorageData(STORAGE_KEYS.listings, listings);
  },

  formatCurrency(value) {
    return new Intl.NumberFormat("zh-TW", {
      style: "currency",
      currency: "TWD",
      maximumFractionDigits: 0,
    }).format(value);
  },

  formatDate(dateString) {
    return new Intl.DateTimeFormat("zh-TW", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(dateString));
  },

  readFileAsDataUrl(file) {
    // Promise 包裝 FileReader，之後在 async/await 中使用會更直觀。
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("圖片讀取失敗，請重新選擇檔案。"));
      reader.readAsDataURL(file);
    });
  },
};
