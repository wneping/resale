// shared.js 先提供資料存取與格式化工具，這個檔案只專注主頁互動邏輯。
const elements = {
  registerForm: document.querySelector("#registerForm"),
  loginForm: document.querySelector("#loginForm"),
  listingForm: document.querySelector("#listingForm"),
  authMessage: document.querySelector("#authMessage"),
  listingMessage: document.querySelector("#listingMessage"),
  loginStatus: document.querySelector("#loginStatus"),
  logoutButton: document.querySelector("#logoutButton"),
  imagePreview: document.querySelector("#imagePreview"),
  previewPlaceholder: document.querySelector("#previewPlaceholder"),
  productGrid: document.querySelector("#productGrid"),
  listingSubmit: document.querySelector("#listingSubmit"),
  tabButtons: document.querySelectorAll(".tab-button"),
  productCardTemplate: document.querySelector("#productCardTemplate"),
  listingImageInput: document.querySelector('input[name="image"]'),
  authModal: document.querySelector("#authModal"),
  openAuthModalButton: document.querySelector("#openAuthModalButton"),
  openAuthHeroButton: document.querySelector("#openAuthHeroButton"),
  closeAuthModalButton: document.querySelector("#closeAuthModalButton"),
};

function setMessage(targetElement, message, tone = "default") {
  targetElement.textContent = message;
  targetElement.style.color = tone === "success" ? "var(--success)" : "var(--muted)";
}

function switchTab(tabName) {
  elements.tabButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });

  elements.registerForm.classList.toggle("hidden", tabName !== "register");
  elements.loginForm.classList.toggle("hidden", tabName !== "login");
}

function openAuthModal(tabName = "login") {
  switchTab(tabName);
  elements.authModal.classList.remove("hidden");
}

function closeAuthModal() {
  elements.authModal.classList.add("hidden");
}

function updateAuthUI() {
  const currentUser = MarketGlowStore.getCurrentUser();

  if (currentUser) {
    elements.loginStatus.textContent = `目前登入：${currentUser.displayName}`;
    elements.logoutButton.classList.remove("hidden");
    elements.openAuthModalButton.classList.add("hidden");
    elements.listingSubmit.disabled = false;
    elements.listingSubmit.textContent = "刊登商品";
    setMessage(
      elements.listingMessage,
      `歡迎回來，${currentUser.displayName}，你現在可以刊登商品。`,
      "success"
    );
  } else {
    elements.loginStatus.textContent = "尚未登入";
    elements.logoutButton.classList.add("hidden");
    elements.openAuthModalButton.classList.remove("hidden");
    elements.listingSubmit.disabled = true;
    elements.listingSubmit.textContent = "登入後可刊登商品";
    setMessage(elements.listingMessage, "請先登入後再刊登商品。");
  }
}

function renderProducts() {
  const listings = MarketGlowStore.getListings();
  elements.productGrid.innerHTML = "";

  if (listings.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.textContent = "目前還沒有任何商品刊登，登入後就能成為第一位賣家。";
    elements.productGrid.appendChild(emptyState);
    return;
  }

  listings
    .slice()
    .reverse()
    .slice(0, 6)
    .forEach((listing) => {
      const card = elements.productCardTemplate.content.cloneNode(true);
      card.querySelector(".product-image").src = listing.imageData;
      card.querySelector(".seller-badge").textContent = listing.sellerName;
      card.querySelector(".price-tag").textContent = MarketGlowStore.formatCurrency(
        listing.price
      );
      card.querySelector(".product-title").textContent = listing.title;
      card.querySelector(".product-description").textContent = listing.description;
      card.querySelector(".product-time").textContent = `刊登時間：${MarketGlowStore.formatDate(
        listing.createdAt
      )}`;
      elements.productGrid.appendChild(card);
    });
}

function resetPreview() {
  elements.imagePreview.classList.add("hidden");
  elements.imagePreview.removeAttribute("src");
  elements.previewPlaceholder.classList.remove("hidden");
}

async function handleRegister(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const displayName = formData.get("displayName").trim();
  const account = formData.get("account").trim();
  const password = formData.get("password").trim();

  const users = MarketGlowStore.getUsers();
  const accountExists = users.some((user) => user.account === account);

  if (accountExists) {
    setMessage(elements.authMessage, "這個帳號已存在，請改用其他帳號。");
    return;
  }

  const newUser = {
    id: crypto.randomUUID(),
    displayName,
    account,
    password,
  };

  users.push(newUser);
  MarketGlowStore.setUsers(users);
  MarketGlowStore.setCurrentUser(newUser);

  event.currentTarget.reset();
  setMessage(elements.authMessage, `註冊成功，${displayName} 已自動登入。`, "success");
  updateAuthUI();
  closeAuthModal();
}

function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const account = formData.get("account").trim();
  const password = formData.get("password").trim();

  const users = MarketGlowStore.getUsers();
  const matchedUser = users.find(
    (user) => user.account === account && user.password === password
  );

  if (!matchedUser) {
    setMessage(elements.authMessage, "帳號或密碼錯誤，請重新確認。");
    return;
  }

  MarketGlowStore.setCurrentUser(matchedUser);
  event.currentTarget.reset();
  setMessage(elements.authMessage, `登入成功，歡迎回來 ${matchedUser.displayName}。`, "success");
  updateAuthUI();
  closeAuthModal();
}

function handleLogout() {
  MarketGlowStore.clearCurrentUser();
  updateAuthUI();
  setMessage(elements.authMessage, "你已經登出。");
}

async function handleImagePreview(event) {
  const file = event.target.files?.[0];

  if (!file) {
    resetPreview();
    return;
  }

  try {
    const imageData = await MarketGlowStore.readFileAsDataUrl(file);
    elements.imagePreview.src = imageData;
    elements.imagePreview.classList.remove("hidden");
    elements.previewPlaceholder.classList.add("hidden");
  } catch (error) {
    setMessage(elements.listingMessage, error.message);
    resetPreview();
  }
}

async function handleListingSubmit(event) {
  event.preventDefault();

  const currentUser = MarketGlowStore.getCurrentUser();
  if (!currentUser) {
    openAuthModal("login");
    setMessage(elements.listingMessage, "請先登入後再刊登商品。");
    return;
  }

  const formData = new FormData(event.currentTarget);
  const imageFile = formData.get("image");

  if (!(imageFile instanceof File) || imageFile.size === 0) {
    setMessage(elements.listingMessage, "請選擇商品圖片。");
    return;
  }

  try {
    const imageData = await MarketGlowStore.readFileAsDataUrl(imageFile);
    const listings = MarketGlowStore.getListings();
    const newListing = {
      id: crypto.randomUUID(),
      title: formData.get("title").trim(),
      price: Number(formData.get("price")),
      description: formData.get("description").trim(),
      imageData,
      sellerId: currentUser.id,
      sellerName: currentUser.displayName,
      createdAt: new Date().toISOString(),
    };

    listings.push(newListing);
    MarketGlowStore.setListings(listings);
    event.currentTarget.reset();
    resetPreview();
    renderProducts();
    setMessage(elements.listingMessage, "商品刊登成功，已同步更新到探索頁。", "success");
  } catch (error) {
    setMessage(elements.listingMessage, error.message);
  }
}

function bindEvents() {
  elements.tabButtons.forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  elements.openAuthModalButton.addEventListener("click", () => openAuthModal("login"));
  elements.openAuthHeroButton.addEventListener("click", () => openAuthModal("register"));
  elements.closeAuthModalButton.addEventListener("click", closeAuthModal);
  elements.authModal.addEventListener("click", (event) => {
    // 點擊遮罩時關閉視窗，是常見的 modal 互動方式，使用者會更熟悉。
    if (event.target === elements.authModal) {
      closeAuthModal();
    }
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.authModal.classList.contains("hidden")) {
      closeAuthModal();
    }
  });

  elements.registerForm.addEventListener("submit", handleRegister);
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.logoutButton.addEventListener("click", handleLogout);
  elements.listingForm.addEventListener("submit", handleListingSubmit);
  elements.listingImageInput.addEventListener("change", handleImagePreview);
}

function init() {
  bindEvents();
  switchTab("register");
  updateAuthUI();
  renderProducts();
}

init();
