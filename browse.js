const browseElements = {
  loginStatus: document.querySelector("#exploreLoginStatus"),
  totalListingsCount: document.querySelector("#totalListingsCount"),
  totalSellersCount: document.querySelector("#totalSellersCount"),
  latestListingTime: document.querySelector("#latestListingTime"),
  searchInput: document.querySelector("#searchInput"),
  sortSelect: document.querySelector("#sortSelect"),
  exploreMessage: document.querySelector("#exploreMessage"),
  productGrid: document.querySelector("#exploreProductGrid"),
  productCardTemplate: document.querySelector("#exploreProductCardTemplate"),
};

function updateExploreHeader() {
  const currentUser = MarketGlowStore.getCurrentUser();
  browseElements.loginStatus.textContent = currentUser
    ? `目前登入：${currentUser.displayName}`
    : "未登入，也可瀏覽全部商品";
}

function getFilteredListings() {
  const searchText = browseElements.searchInput.value.trim().toLowerCase();
  const sortType = browseElements.sortSelect.value;

  let listings = MarketGlowStore.getListings().filter((listing) => {
    // 搜尋同時比對標題、描述與賣家名稱，讓探索頁更實用。
    const haystack = `${listing.title} ${listing.description} ${listing.sellerName}`.toLowerCase();
    return haystack.includes(searchText);
  });

  if (sortType === "priceHigh") {
    listings.sort((a, b) => b.price - a.price);
  } else if (sortType === "priceLow") {
    listings.sort((a, b) => a.price - b.price);
  } else {
    listings.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  }

  return listings;
}

function renderStatistics(listings) {
  const allListings = MarketGlowStore.getListings();
  const sellerCount = new Set(allListings.map((listing) => listing.sellerId)).size;
  const latestListing = allListings
    .slice()
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))[0];

  browseElements.totalListingsCount.textContent = String(allListings.length);
  browseElements.totalSellersCount.textContent = String(sellerCount);
  browseElements.latestListingTime.textContent = latestListing
    ? MarketGlowStore.formatDate(latestListing.createdAt)
    : "尚無資料";
  browseElements.exploreMessage.textContent =
    listings.length > 0
      ? `目前顯示 ${listings.length} 筆商品。你可以使用搜尋與排序快速瀏覽。`
      : "查無符合條件的商品，請試試其他關鍵字。";
}

function renderExploreProducts() {
  const listings = getFilteredListings();
  browseElements.productGrid.innerHTML = "";
  renderStatistics(listings);

  if (listings.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.textContent = "目前沒有符合條件的商品，稍後再回來看看，或回刊登中心新增商品。";
    browseElements.productGrid.appendChild(emptyState);
    return;
  }

  listings.forEach((listing) => {
    const card = browseElements.productCardTemplate.content.cloneNode(true);
    card.querySelector(".product-image").src = listing.imageData;
    card.querySelector(".seller-badge").textContent = `賣家：${listing.sellerName}`;
    card.querySelector(".price-tag").textContent = MarketGlowStore.formatCurrency(
      listing.price
    );
    card.querySelector(".product-title").textContent = listing.title;
    card.querySelector(".product-description").textContent = listing.description;
    card.querySelector(".product-time").textContent = `刊登時間：${MarketGlowStore.formatDate(
      listing.createdAt
    )}`;
    browseElements.productGrid.appendChild(card);
  });
}

function bindBrowseEvents() {
  browseElements.searchInput.addEventListener("input", renderExploreProducts);
  browseElements.sortSelect.addEventListener("change", renderExploreProducts);
}

function initBrowsePage() {
  updateExploreHeader();
  bindBrowseEvents();
  renderExploreProducts();
}

initBrowsePage();
