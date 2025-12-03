(() => {
  "use strict";

  // DOM Elements
  const usernameInput = document.getElementById("username");
  const tokenInput = document.getElementById("token");
  const promptInput = document.getElementById("prompt");
  const widthInput = document.getElementById("width");
  const heightInput = document.getElementById("height");
  const generateBtn = document.getElementById("generateBtn");
  const statusEl = document.getElementById("status");
  const historyList = document.getElementById("historyList");
  const themeToggle = document.getElementById("themeToggle");
  const currentImageEl = document.getElementById("currentImage");
  const modal = document.getElementById("modal");
  const modalImg = document.getElementById("modalImg");
  const modalInfo = document.getElementById("modalInfo");
  const modalClose = document.getElementById("modalClose");

  // Constants
  const MAX_SIZE = 2048;
  const MIN_SIZE = 64;
  const USERNAME_PATTERN = /^[A-Za-z0-9_-]{1,32}$/;
  const STORAGE_KEYS = {
    username: "zimage_username",
    token: "zimage_token",
    theme: "zimage_theme",
  };

  // Initialize
  function init() {
    loadSavedState();
    bindEvents();
    // Only fetch history if token and username exist
    if (localStorage.getItem(STORAGE_KEYS.token) && localStorage.getItem(STORAGE_KEYS.username)) {
      fetchHistory();
    }
  }

  function loadSavedState() {
    // Load username
    const savedUsername = localStorage.getItem(STORAGE_KEYS.username);
    if (savedUsername) {
      usernameInput.value = savedUsername;
    }

    // Load token
    const savedToken = localStorage.getItem(STORAGE_KEYS.token);
    if (savedToken) {
      tokenInput.value = savedToken;
    }

    // Load theme
    const savedTheme = localStorage.getItem(STORAGE_KEYS.theme) || "light";
    setTheme(savedTheme);
  }

  function bindEvents() {
    generateBtn.addEventListener("click", handleGenerate);
    themeToggle.addEventListener("click", toggleTheme);
    modalClose.addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });

    // Save username on change
    usernameInput.addEventListener("change", () => {
      const value = usernameInput.value.trim();
      if (value && USERNAME_PATTERN.test(value)) {
        localStorage.setItem(STORAGE_KEYS.username, value);
        fetchHistory();
      }
    });

    // Save token on change
    tokenInput.addEventListener("change", () => {
      localStorage.setItem(STORAGE_KEYS.token, tokenInput.value.trim());
      fetchHistory();
    });

    // Keyboard shortcut: Ctrl+Enter to generate
    promptInput.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.key === "Enter") {
        handleGenerate();
      }
    });
  }

  // Theme
  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    themeToggle.textContent = theme === "dark" ? "[亮色]" : "[暗色]";
    localStorage.setItem(STORAGE_KEYS.theme, theme);
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    setTheme(current === "dark" ? "light" : "dark");
  }

  // Status
  function setStatus(msg, isError = false) {
    statusEl.textContent = msg;
    statusEl.classList.toggle("error", isError);
  }

  // Auth header with username
  function getAuthHeaders() {
    const token = tokenInput.value.trim();
    const username = usernameInput.value.trim();
    const headers = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (username) {
      headers["X-Username"] = username;
    }
    return headers;
  }

  // Validation
  function validateInputs() {
    const username = usernameInput.value.trim();
    if (!username) {
      setStatus("请输入用户名", true);
      usernameInput.focus();
      return false;
    }

    if (!USERNAME_PATTERN.test(username)) {
      setStatus("用户名仅支持字母、数字、下划线、短横线", true);
      usernameInput.focus();
      return false;
    }

    const token = tokenInput.value.trim();
    if (!token) {
      setStatus("请输入登录口令", true);
      tokenInput.focus();
      return false;
    }

    const prompt = promptInput.value.trim();
    if (!prompt) {
      setStatus("请输入提示词", true);
      promptInput.focus();
      return false;
    }

    const width = parseInt(widthInput.value, 10);
    const height = parseInt(heightInput.value, 10);

    if (isNaN(width) || width < MIN_SIZE || width > MAX_SIZE) {
      setStatus(`宽度需在 ${MIN_SIZE}-${MAX_SIZE} 之间`, true);
      widthInput.focus();
      return false;
    }

    if (isNaN(height) || height < MIN_SIZE || height > MAX_SIZE) {
      setStatus(`高度需在 ${MIN_SIZE}-${MAX_SIZE} 之间`, true);
      heightInput.focus();
      return false;
    }

    return { prompt, width, height };
  }

  // Generate Image
  async function handleGenerate() {
    const inputs = validateInputs();
    if (!inputs) return;

    // Save username and token
    localStorage.setItem(STORAGE_KEYS.username, usernameInput.value.trim());
    localStorage.setItem(STORAGE_KEYS.token, tokenInput.value.trim());

    generateBtn.disabled = true;
    setStatus("正在生成...");
    currentImageEl.innerHTML = "";

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(inputs),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `请求失败 (${response.status})`);
      }

      const data = await response.json();
      setStatus("生成完成!");

      // Show current image
      if (data.image) {
        showCurrentImage(data.image, inputs.prompt, inputs.width, inputs.height);
      }

      // Refresh history
      await fetchHistory();
    } catch (error) {
      setStatus(`生成失败: ${error.message}`, true);
    } finally {
      generateBtn.disabled = false;
    }
  }

  // Display current generated image
  function showCurrentImage(imageUrl, prompt, width, height) {
    const img = document.createElement("img");
    img.src = imageUrl;
    img.alt = prompt;
    img.onclick = () => openModal(imageUrl, prompt, width, height);
    currentImageEl.innerHTML = "";
    currentImageEl.appendChild(img);
  }

  // History
  async function fetchHistory() {
    const username = usernameInput.value.trim();
    const token = tokenInput.value.trim();

    if (!username || !token) {
      historyList.innerHTML = '<div class="meta">请输入用户名和口令查看历史</div>';
      return;
    }

    try {
      const response = await fetch("/api/history", {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          historyList.innerHTML = '<div class="meta">口令错误</div>';
          return;
        }
        if (response.status === 400) {
          historyList.innerHTML = '<div class="meta">请输入有效用户名</div>';
          return;
        }
        throw new Error("获取历史失败");
      }

      const data = await response.json();
      renderHistory(data.history || []);
    } catch (error) {
      console.error("History fetch error:", error);
    }
  }

  function renderHistory(items) {
    historyList.innerHTML = "";

    if (!items.length) {
      historyList.innerHTML = '<div class="meta">暂无生图历史</div>';
      return;
    }

    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "card";
      card.onclick = () => openModal(item.image, item.prompt, item.width, item.height);

      const img = document.createElement("img");
      img.src = item.image;
      img.alt = item.prompt || "生成图片";
      img.loading = "lazy";

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `${item.width}x${item.height}`;

      const filename = document.createElement("div");
      filename.className = "filename";
      // Extract filename from path
      const name = item.image.split("/").pop();
      filename.textContent = name || "";

      card.appendChild(img);
      card.appendChild(meta);
      card.appendChild(filename);
      historyList.appendChild(card);
    });
  }

  // Modal
  function openModal(imageUrl, prompt, width, height) {
    modalImg.src = imageUrl;
    modalInfo.textContent = `${width}x${height} | ${prompt.slice(0, 100)}${prompt.length > 100 ? "..." : ""}`;
    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.classList.add("hidden");
    document.body.style.overflow = "";
  }

  // Escape key to close modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) {
      closeModal();
    }
  });

  // Start
  init();
})();
