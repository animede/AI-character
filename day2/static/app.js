const state = {
  characters: [],
  currentCharacterId: null,
  currentConversationId: null,
  messages: [],
  serverStatus: "loading",
  modelName: "-",
  isStreaming: false,
  currentAssistantMessageId: null,
  renderQueue: [],
  streamEnded: false,
  renderLoopRunning: false,
  socket: null,
  socketReady: null,
};

const elements = {
  serverStatus: document.getElementById("server-status"),
  modelName: document.getElementById("model-name"),
  characterSelect: document.getElementById("character-select"),
  characterVisual: document.getElementById("character-visual"),
  characterAvatarLabel: document.getElementById("character-avatar-label"),
  characterName: document.getElementById("character-name"),
  characterDescription: document.getElementById("character-description"),
  historyCountInput: document.getElementById("history-count-input"),
  roleText: document.getElementById("role-text"),
  chatMessages: document.getElementById("chat-messages"),
  errorBanner: document.getElementById("error-banner"),
  composer: document.getElementById("composer"),
  messageInput: document.getElementById("message-input"),
  sendButton: document.getElementById("send-button"),
  newConversationButton: document.getElementById("new-conversation-button"),
  clearConversationButton: document.getElementById("clear-conversation-button"),
};

async function init() {
  bindEvents();
  await refreshHealth();
  await loadCharacters();
  await connectWebSocket();
  await startConversation(state.currentCharacterId);
}

function getWebSocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws`;
}

function bindEvents() {
  elements.characterSelect.addEventListener("change", async (event) => {
    state.currentCharacterId = event.target.value;
    renderCharacterPanel();
    await startConversation(state.currentCharacterId);
  });

  elements.composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    await sendMessage();
  });

  elements.messageInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await sendMessage();
    }
  });

  elements.newConversationButton.addEventListener("click", async () => {
    await startConversation(state.currentCharacterId);
  });

  elements.clearConversationButton.addEventListener("click", async () => {
    await clearConversation();
  });

  elements.roleText.addEventListener("input", () => {
    syncCharacterPanel();
  });
}

function extractCharacterName(roleValue, fallbackName) {
  const nameLineMatch = roleValue.match(/(?:^|\n)\s*-?\s*名前\s*[:：]\s*(.+)/);
  if (nameLineMatch) {
    return nameLineMatch[1].trim().replace(/^「(.+)」$/, "$1");
  }

  const sentenceMatch = roleValue.match(/あなたは.*?「(.+?)」です/);
  if (sentenceMatch) {
    return sentenceMatch[1].trim();
  }

  return fallbackName;
}

function syncCharacterPanel() {
  const character = getCurrentCharacter();
  if (!character) {
    return;
  }

  const name = extractCharacterName(elements.roleText.value, character.display_name);
  elements.characterName.textContent = name;
  elements.characterAvatarLabel.textContent = name.slice(0, 1);

  const image = elements.characterVisual.querySelector("img");
  if (image) {
    image.alt = `${name} の画像`;
  }
}

function connectWebSocket() {
  if (state.socket && state.socket.readyState === WebSocket.OPEN) {
    return Promise.resolve();
  }

  if (state.socketReady) {
    return state.socketReady;
  }

  state.socketReady = new Promise((resolve, reject) => {
    const socket = new WebSocket(getWebSocketUrl());
    let settled = false;

    socket.addEventListener("open", () => {
      state.socket = socket;
      settled = true;
      resolve();
    });

    socket.addEventListener("message", (event) => {
      handleSocketEvent(JSON.parse(event.data));
    });

    socket.addEventListener("error", () => {
      if (!settled) {
        settled = true;
        reject(new Error("WebSocket接続を開始できませんでした。"));
      }
    });

    socket.addEventListener("close", () => {
      if (state.socket === socket) {
        state.socket = null;
      }
      state.socketReady = null;

      if (!settled) {
        settled = true;
        reject(new Error("WebSocket接続を開始できませんでした。"));
        return;
      }

      if (state.isStreaming) {
        showError("WebSocket接続が切断されました。");
        finalizeStreamingError();
      }
    });
  });

  return state.socketReady;
}

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    state.serverStatus = data.llm_status === "ok" ? "ok" : "error";
    state.modelName = data.model || "-";
    if (!state.currentCharacterId) {
      state.currentCharacterId = data.default_character_id;
    }
    updateServerStatus();
  } catch (error) {
    state.serverStatus = "error";
    updateServerStatus();
    showError("バックエンドまたはLLMサーバに接続できません。");
  }
}

function updateServerStatus() {
  elements.serverStatus.className = "status-badge";
  if (state.serverStatus === "ok") {
    elements.serverStatus.classList.add("status-ok");
    elements.serverStatus.textContent = "LLM接続OK";
  } else if (state.serverStatus === "error") {
    elements.serverStatus.classList.add("status-error");
    elements.serverStatus.textContent = "LLM未接続";
  } else {
    elements.serverStatus.classList.add("status-loading");
    elements.serverStatus.textContent = "接続確認中";
  }
  elements.modelName.textContent = `model: ${state.modelName}`;
}

async function loadCharacters() {
  const response = await fetch("/api/characters");
  const data = await response.json();
  state.characters = data.characters || [];
  if (!state.currentCharacterId && state.characters.length > 0) {
    const defaultCharacter = state.characters.find((item) => item.is_default) || state.characters[0];
    state.currentCharacterId = defaultCharacter.id;
  }

  elements.characterSelect.innerHTML = "";
  for (const character of state.characters) {
    const option = document.createElement("option");
    option.value = character.id;
    option.textContent = character.display_name;
    if (character.id === state.currentCharacterId) {
      option.selected = true;
    }
    elements.characterSelect.appendChild(option);
  }
  renderCharacterPanel();
}

function getCurrentCharacter() {
  return state.characters.find((item) => item.id === state.currentCharacterId) || null;
}

function renderCharacterPanel() {
  const character = getCurrentCharacter();
  if (!character) {
    return;
  }

  elements.characterDescription.textContent = character.short_description;
  elements.roleText.value = character.role_text;

  elements.characterVisual.innerHTML = "";
  if (character.visual_type === "image" && character.visual_path) {
    const image = document.createElement("img");
    image.src = character.visual_path;
    image.alt = `${character.display_name} の画像`;
    elements.characterVisual.appendChild(image);
  } else if (character.visual_type === "video" && character.visual_path) {
    const video = document.createElement("video");
    video.src = character.visual_path;
    video.muted = true;
    video.autoplay = true;
    video.loop = true;
    video.playsInline = true;
    elements.characterVisual.appendChild(video);
  } else {
    const placeholder = document.createElement("span");
    placeholder.textContent = character.avatar_label;
    elements.characterVisual.appendChild(placeholder);
  }

  document.documentElement.style.setProperty("--accent", character.theme_color);
  document.documentElement.style.setProperty("--accent-deep", character.theme_color);
  document.documentElement.style.setProperty("--accent-cool", character.ui_accent_color);
  syncCharacterPanel();
}

async function startConversation(characterId) {
  hideError();
  const response = await fetch("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ character_id: characterId }),
  });
  const data = await response.json();
  state.currentConversationId = data.conversation_id;
  state.currentCharacterId = data.character.id;
  state.messages = data.messages.map((message) => ({ ...message, status: "done" }));
  elements.characterSelect.value = state.currentCharacterId;
  renderCharacterPanel();
  renderMessages();
}

async function clearConversation() {
  if (!state.currentConversationId) {
    return;
  }
  hideError();
  const response = await fetch(`/api/conversations/${state.currentConversationId}/clear`, {
    method: "POST",
  });
  const data = await response.json();
  state.currentConversationId = data.new_conversation_id;
  state.messages = data.messages.map((message) => ({ ...message, status: "done" }));
  renderMessages();
}

function renderMessages() {
  elements.chatMessages.innerHTML = "";
  for (const message of state.messages) {
    elements.chatMessages.appendChild(createMessageElement(message));
  }
  scrollMessagesToBottom();
}

function createMessageElement(message) {
  const row = document.createElement("div");
  row.className = `message-row ${message.role}`;
  row.dataset.messageId = message.message_id;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (message.status === "pending") {
    bubble.classList.add("pending");
  }
  bubble.textContent = message.content;

  row.appendChild(bubble);
  return row;
}

function appendMessage(message) {
  state.messages.push(message);
  elements.chatMessages.appendChild(createMessageElement(message));
  scrollMessagesToBottom();
}

function updateMessageContent(messageId, content, status = "pending") {
  const target = state.messages.find((item) => item.message_id === messageId);
  if (!target) {
    return;
  }
  target.content = content;
  target.status = status;
  const row = elements.chatMessages.querySelector(`[data-message-id="${messageId}"] .message-bubble`);
  if (!row) {
    return;
  }
  row.textContent = content;
  row.classList.toggle("pending", status === "pending");
  scrollMessagesToBottom();
}

async function sendMessage() {
  const message = elements.messageInput.value.trim();
  const roleText = elements.roleText.value.trim();
  const historyCount = Number(elements.historyCountInput.value || 10);
  if (!message || state.isStreaming || !state.currentConversationId) {
    return;
  }

  hideError();
  state.isStreaming = true;
  state.renderQueue = [];
  state.streamEnded = false;
  state.currentAssistantMessageId = null;
  setComposerDisabled(true);

  const userMessage = {
    message_id: `local_user_${Date.now()}`,
    role: "user",
    content: message,
    timestamp: new Date().toISOString(),
    status: "done",
  };
  appendMessage(userMessage);
  elements.messageInput.value = "";

  try {
    await connectWebSocket();
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket接続を利用できません。");
    }

    state.socket.send(
      JSON.stringify({
        action: "chat",
        conversation_id: state.currentConversationId,
        message,
        role: roleText,
        max_history: historyCount,
      })
    );
  } catch (error) {
    showError(error.message || "通信中にエラーが発生しました。");
    finalizeStreamingError();
  }
}

function handleSocketEvent(event) {
  if (event.type === "start") {
    const assistantMessage = {
      message_id: event.message_id,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      status: "pending",
    };
    state.currentAssistantMessageId = event.message_id;
    appendMessage(assistantMessage);
    return;
  }

  if (event.type === "delta") {
    state.renderQueue.push(...Array.from(event.delta));
    if (!state.renderLoopRunning) {
      startRenderLoop();
    }
    return;
  }

  if (event.type === "end") {
    state.streamEnded = true;
    finishStreamingIfReady();
    return;
  }

  if (event.type === "error") {
    showError(event.error || "ストリーム処理でエラーが発生しました。");
    finalizeStreamingError();
  }
}

function startRenderLoop() {
  state.renderLoopRunning = true;

  const tick = () => {
    if (!state.currentAssistantMessageId) {
      state.renderLoopRunning = false;
      return;
    }

    const queueLength = state.renderQueue.length;
    if (queueLength > 0) {
      const step = queueLength > 60 ? 4 : queueLength > 20 ? 2 : 1;
      const chunk = state.renderQueue.splice(0, step).join("");
      const message = state.messages.find((item) => item.message_id === state.currentAssistantMessageId);
      if (message) {
        updateMessageContent(state.currentAssistantMessageId, message.content + chunk, "pending");
      }
      window.setTimeout(tick, 20);
      return;
    }

    state.renderLoopRunning = false;
    finishStreamingIfReady();
  };

  tick();
}

function finishStreamingIfReady() {
  if (!state.streamEnded || state.renderQueue.length > 0 || state.renderLoopRunning || !state.currentAssistantMessageId) {
    return;
  }
  const message = state.messages.find((item) => item.message_id === state.currentAssistantMessageId);
  if (message) {
    updateMessageContent(message.message_id, message.content, "done");
  }
  state.isStreaming = false;
  state.currentAssistantMessageId = null;
  state.streamEnded = false;
  setComposerDisabled(false);
}

function finalizeStreamingError() {
  if (state.currentAssistantMessageId) {
    const message = state.messages.find((item) => item.message_id === state.currentAssistantMessageId);
    if (message) {
      updateMessageContent(message.message_id, message.content, "done");
    }
  }
  state.isStreaming = false;
  state.renderQueue = [];
  state.streamEnded = false;
  state.currentAssistantMessageId = null;
  state.renderLoopRunning = false;
  setComposerDisabled(false);
}

function setComposerDisabled(disabled) {
  elements.messageInput.disabled = disabled;
  elements.sendButton.disabled = disabled;
  elements.newConversationButton.disabled = disabled;
  elements.clearConversationButton.disabled = disabled;
}

function showError(message) {
  elements.errorBanner.textContent = message;
  elements.errorBanner.classList.remove("hidden");
}

function hideError() {
  elements.errorBanner.textContent = "";
  elements.errorBanner.classList.add("hidden");
}

function scrollMessagesToBottom() {
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

init().catch((error) => {
  showError(error.message || "初期化に失敗しました。");
});
