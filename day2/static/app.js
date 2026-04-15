const state = {
  // 会話、ストリーミング、音声再生、表示モードの実行時状態をまとめて持つ。
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
  ttsAvailable: false,
  audioQueue: [],
  isAudioPlaying: false,
  currentAudioElement: null,
  currentTurnAudioEnabled: false,
  characterVisualMode: "initial",
  hasStartedConversation: false,
  isCharacterVisualExpanded: false,
};

const elements = {
  // DOM 参照を先に束ね、各関数で毎回 query しないようにする。
  serverStatus: document.getElementById("server-status"),
  modelName: document.getElementById("model-name"),
  layoutRoot: document.getElementById("layout-root"),
  characterPanel: document.getElementById("character-panel"),
  chatPanel: document.getElementById("chat-panel"),
  characterSelect: document.getElementById("character-select"),
  characterVisual: document.getElementById("character-visual"),
  chatVisualStage: document.getElementById("chat-visual-stage"),
  chatVisualClose: document.getElementById("chat-visual-close"),
  characterAvatarLabel: document.getElementById("character-avatar-label"),
  characterName: document.getElementById("character-name"),
  characterDescription: document.getElementById("character-description"),
  historyCountInput: document.getElementById("history-count-input"),
  audioEnabledToggle: document.getElementById("audio-enabled-toggle"),
  audioEnabledLabel: document.getElementById("audio-enabled-label"),
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
  // 初期表示に必要な順で、UI バインド、状態取得、通信確立、会話開始まで進める。
  bindEvents();
  await refreshHealth();
  await loadCharacters();
  await connectWebSocket();
  await startConversation(state.currentCharacterId);
}

function getWebSocketUrl() {
  // http/https に合わせて ws/wss を切り替える。
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws`;
}

function bindEvents() {
  // クリックや送信など、UI からの入口をここで束ねる。
  elements.characterVisual.addEventListener("click", () => {
    toggleCharacterVisualExpanded();
  });

  elements.chatVisualClose.addEventListener("click", (event) => {
    event.stopPropagation();
    closeCharacterVisualExpanded();
  });

  elements.characterSelect.addEventListener("change", async (event) => {
    resetAudioPlayback();
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
    resetAudioPlayback();
    await startConversation(state.currentCharacterId);
  });

  elements.clearConversationButton.addEventListener("click", async () => {
    resetAudioPlayback();
    await clearConversation();
  });

  elements.roleText.addEventListener("input", () => {
    syncCharacterPanel();
  });
}

function extractCharacterName(roleValue, fallbackName) {
  // 明示的な「名前: ...」指定を最優先で採用する。
  const nameLineMatch = roleValue.match(/(?:^|\n)\s*-?\s*名前\s*[:：]\s*(.+)/);
  if (nameLineMatch) {
    return nameLineMatch[1].trim().replace(/^「(.+)」$/, "$1");
  }

  // 既存の role 文面からも、簡易的にキャラ名を拾えるようにしておく。
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

  // role 編集に追従して表示名も即時更新し、見た目と設定のズレを減らす。
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
    // 既存接続が生きていれば、そのまま再利用する。
    return Promise.resolve();
  }

  if (state.socketReady) {
    // 接続中の Promise がある場合は二重接続せずそれを待つ。
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
      // イベント種別ごとの処理は別関数に寄せ、ここでは受信だけ担う。
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
        // ストリーム中断は失敗扱いにして、入力欄と表示状態を復旧する。
        showError("WebSocket接続が切断されました。");
        finalizeStreamingError();
      }
      resetAudioPlayback();
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
    state.ttsAvailable = Boolean(data.tts_available);
    elements.audioEnabledToggle.disabled = !state.ttsAvailable;
    elements.audioEnabledToggle.checked = state.ttsAvailable;
    // TTS 未接続時はトグル自体を無効化して text-only に固定する。
    elements.audioEnabledLabel.textContent = state.ttsAvailable ? "音声を再生する" : "TTS未接続";
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
  // 状態ごとにバッジの色と文言をまとめて切り替える。
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
    // まだ未選択なら、既定キャラを初回選択として採用する。
    const defaultCharacter = state.characters.find((item) => item.is_default) || state.characters[0];
    state.currentCharacterId = defaultCharacter.id;
  }

  // セレクトボックスは API 応答をもとに毎回作り直す。
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
  // 選択中 ID に対応するキャラ定義を 1 件だけ返す。
  return state.characters.find((item) => item.id === state.currentCharacterId) || null;
}

function renderCharacterPanel() {
  const character = getCurrentCharacter();
  if (!character) {
    return;
  }

  // 表示テキストと role 編集欄は、選択中キャラの定義で常に上書きする。
  elements.characterDescription.textContent = character.short_description;
  elements.roleText.value = character.role_text;

  // 小さな左パネルは、現在の visual mode に応じて画像か動画を差し替える。
  elements.characterVisual.innerHTML = "";
  const visual = getCharacterVisualForMode(character, state.characterVisualMode);
  if (visual.type === "image" && visual.path) {
    const image = document.createElement("img");
    image.src = visual.path;
    image.alt = `${character.display_name} の画像`;
    elements.characterVisual.appendChild(image);
  } else if (visual.type === "video" && visual.path) {
    const video = document.createElement("video");
    video.src = visual.path;
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
  // 左の小表示と右の拡大表示で、常に同じ見た目ソースを使う。
  renderExpandedCharacterVisual();
}

function getCharacterVisualForMode(character, mode) {
  // talking / waiting 専用素材があれば優先し、無ければ初期素材へ戻す。
  if (mode === "talking" && character.talking_visual_path) {
    return { type: "video", path: character.talking_visual_path };
  }

  if (mode === "waiting" && character.waiting_visual_path) {
    return { type: "video", path: character.waiting_visual_path };
  }

  return { type: character.visual_type, path: character.visual_path };
}

function setCharacterVisualMode(mode) {
  if (state.characterVisualMode === mode) {
    // 同じモードなら DOM を触らず、そのままにする。
    return;
  }
  state.characterVisualMode = mode;
  renderCharacterPanel();
}

function toggleCharacterVisualExpanded() {
  // 小表示クリックで、右パネル上部への拡大表示をトグルする。
  state.isCharacterVisualExpanded = !state.isCharacterVisualExpanded;
  renderExpandedCharacterVisual();
}

function closeCharacterVisualExpanded() {
  if (!state.isCharacterVisualExpanded) {
    // 既に閉じているなら何もしない。
    return;
  }
  state.isCharacterVisualExpanded = false;
  renderExpandedCharacterVisual();
}

function renderExpandedCharacterVisual() {
  const character = getCurrentCharacter();
  const stage = elements.chatVisualStage;
  if (!character || !stage) {
    return;
  }

  // 閉じるボタンは残したまま、差し替え対象のメディア要素だけ更新する。
  const existingMedia = stage.querySelector(".chat-visual-media");
  if (existingMedia) {
    existingMedia.remove();
  }
  elements.layoutRoot.classList.toggle("visual-expanded", state.isCharacterVisualExpanded);
  elements.chatPanel.classList.toggle("media-expanded", state.isCharacterVisualExpanded);
  // hidden クラスで通常時はステージ全体をレイアウトから外す。
  stage.classList.toggle("hidden", !state.isCharacterVisualExpanded);

  if (!state.isCharacterVisualExpanded) {
    return;
  }

  const visual = getCharacterVisualForMode(character, state.characterVisualMode);
  const media = document.createElement("div");
  media.className = "chat-visual-media";

  if (visual.type === "image" && visual.path) {
    // 画像素材は img でそのまま敷く。
    const image = document.createElement("img");
    image.src = visual.path;
    image.alt = `${character.display_name} の拡大画像`;
    media.appendChild(image);
    stage.appendChild(media);
    return;
  }

  if (visual.type === "video" && visual.path) {
    // 動画素材は無音ループで流し、装飾ではなく状態表示として使う。
    const video = document.createElement("video");
    video.src = visual.path;
    video.muted = true;
    video.autoplay = true;
    video.loop = true;
    video.playsInline = true;
    media.appendChild(video);
    stage.appendChild(media);
  }
}

function syncCharacterVisualMode() {
  // 音声ありのターンは実再生状態を優先し、音声なしのターンは文字ストリームで代用する。
  if (!state.hasStartedConversation) {
    setCharacterVisualMode("initial");
    return;
  }

  if (state.currentTurnAudioEnabled) {
    if (state.isAudioPlaying) {
      setCharacterVisualMode("talking");
      return;
    }
    setCharacterVisualMode("waiting");
    return;
  }

  if (state.isStreaming) {
    setCharacterVisualMode("talking");
    return;
  }

  setCharacterVisualMode("waiting");
}

async function startConversation(characterId) {
  // 新規会話作成時は、表示メッセージを API の初期状態へ丸ごと同期する。
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
  // 会話を作り直した直後は、まだそのターンの音声再生は始まっていない。
  state.currentTurnAudioEnabled = false;
  syncCharacterVisualMode();
  renderCharacterPanel();
  renderMessages();
}

async function clearConversation() {
  if (!state.currentConversationId) {
    return;
  }
  // クリア時も会話 ID は新しいものへ差し替わるので、サーバ応答で全面更新する。
  resetAudioPlayback();
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
  // 再描画時は一旦空にして、state.messages を正とする。
  elements.chatMessages.innerHTML = "";
  for (const message of state.messages) {
    elements.chatMessages.appendChild(createMessageElement(message));
  }
  scrollMessagesToBottom();
}

function createMessageElement(message) {
  // 役割ごとの CSS と、後続更新用の message_id を DOM に持たせる。
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
  // 新規メッセージは state と DOM に同時反映し、末尾へスクロールする。
  state.messages.push(message);
  elements.chatMessages.appendChild(createMessageElement(message));
  scrollMessagesToBottom();
}

function updateMessageContent(messageId, content, status = "pending") {
  // ストリーム中は既存吹き出しの本文だけ差し替え続ける。
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
  // TTS の実利用可否と、UI トグルの両方を見てそのターンの音声有無を決める。
  const audioEnabled = state.ttsAvailable && elements.audioEnabledToggle.checked;
  if (!message || state.isStreaming || !state.currentConversationId) {
    // 空送信、二重送信、会話未作成のいずれも送信しない。
    return;
  }

  hideError();
  resetAudioPlayback();
  // 新しいターン開始時に、前ターンの再生状態と描画キューを必ず初期化する。
  state.hasStartedConversation = true;
  state.isStreaming = true;
  state.currentTurnAudioEnabled = audioEnabled;
  state.renderQueue = [];
  state.streamEnded = false;
  state.currentAssistantMessageId = null;
  syncCharacterVisualMode();
  setComposerDisabled(true);

  const userMessage = {
    // ユーザー発話は即時反映し、assistant 側だけを後追いストリームで埋める。
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
        audio_enabled: audioEnabled,
      })
    );
  } catch (error) {
    showError(error.message || "通信中にエラーが発生しました。");
    finalizeStreamingError();
  }
}

function handleSocketEvent(event) {
  if (event.type === "start") {
    // assistant ターンの開始点。プレースホルダ吹き出しと音声キューを作り直す。
    state.audioQueue = [];
    state.currentTurnAudioEnabled = Boolean(event.audio_enabled);
    syncCharacterVisualMode();
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
    // 受信したテキストは即描画せずキューへ積み、一定テンポで流す。
    state.renderQueue.push(...Array.from(event.delta));
    if (!state.renderLoopRunning) {
      startRenderLoop();
    }
    return;
  }

  if (event.type === "audio") {
    // 音声イベントはテキスト描画と独立して順次再生する。
    queueAudioSegment(event);
    return;
  }

  if (event.type === "end") {
    // end を受けても描画が残っていれば、閉じ処理は finishStreamingIfReady に委ねる。
    state.streamEnded = true;
    finishStreamingIfReady();
    return;
  }

  if (event.type === "error") {
    if (event.fatal === false) {
      // TTS 側の軽微な失敗はログだけ残して会話自体は継続する。
      console.warn(event.stage || "stream", event.error || "音声処理エラー");
      return;
    }
    showError(event.error || "ストリーム処理でエラーが発生しました。");
    finalizeStreamingError();
  }
}

function queueAudioSegment(event) {
  // backend から届いた音声断片は到着順にキューへ積む。
  state.audioQueue.push(event);
  if (!state.isAudioPlaying) {
    playNextAudioSegment();
  }
}

function playNextAudioSegment() {
  // backend の文単位分割に合わせて、音声断片を 1 本ずつ順番再生する。
  const nextSegment = state.audioQueue.shift();
  if (!nextSegment) {
    state.isAudioPlaying = false;
    state.currentAudioElement = null;
    syncCharacterVisualMode();
    return;
  }

  state.isAudioPlaying = false;
  const audio = new Audio(`data:audio/${nextSegment.audio_format};base64,${nextSegment.audio_b64}`);
  state.currentAudioElement = audio;

  audio.addEventListener("play", () => {
    // talking 表示へ切り替えるタイミングは、実際に再生が始まった瞬間に合わせる。
    if (state.currentAudioElement === audio) {
      state.isAudioPlaying = true;
      syncCharacterVisualMode();
    }
  });

  audio.addEventListener("pause", () => {
    // ended 以外の pause は一時停止扱いとして visual mode を戻す。
    if (state.currentAudioElement === audio && !audio.ended) {
      state.isAudioPlaying = false;
      syncCharacterVisualMode();
    }
  });

  audio.addEventListener("ended", () => {
    // 1 本終わったら次の音声断片へ進む。
    if (state.currentAudioElement === audio) {
      state.isAudioPlaying = false;
      state.currentAudioElement = null;
    }
    playNextAudioSegment();
  });

  audio.addEventListener("error", () => {
    // 再生不能な断片はスキップし、後続断片の再生を止めない。
    if (state.currentAudioElement === audio) {
      state.isAudioPlaying = false;
      state.currentAudioElement = null;
    }
    playNextAudioSegment();
  });

  audio.play().catch(() => {
    // ブラウザ再生拒否時も、キューが詰まらないよう次へ進める。
    if (state.currentAudioElement === audio) {
      state.isAudioPlaying = false;
      state.currentAudioElement = null;
    }
    playNextAudioSegment();
  });
}

function resetAudioPlayback() {
  // 会話切替やエラー時に、再生中の音声と残キューをまとめて破棄する。
  state.audioQueue = [];
  state.isAudioPlaying = false;
  state.currentTurnAudioEnabled = false;
  if (state.currentAudioElement) {
    state.currentAudioElement.pause();
    state.currentAudioElement.currentTime = 0;
    state.currentAudioElement = null;
  }
}

function startRenderLoop() {
  // assistant テキストは一定間隔で描画し、人が読める速度に近づける。
  state.renderLoopRunning = true;

  const tick = () => {
    if (!state.currentAssistantMessageId) {
      // 途中でターンが閉じたら、描画ループも止める。
      state.renderLoopRunning = false;
      return;
    }

    const queueLength = state.renderQueue.length;
    if (queueLength > 0) {
      // backlog が増えたときは描画粒度を上げて、表示遅延を詰める。
      const step = queueLength > 60 ? 4 : queueLength > 20 ? 2 : 1;
      const chunk = state.renderQueue.splice(0, step).join("");
      const message = state.messages.find((item) => item.message_id === state.currentAssistantMessageId);
      if (message) {
        updateMessageContent(state.currentAssistantMessageId, message.content + chunk, "pending");
      }
      // 少し待って次の塊を描き、タイプ感を残す。
      window.setTimeout(tick, 20);
      return;
    }

    state.renderLoopRunning = false;
    finishStreamingIfReady();
  };

  tick();
}

function finishStreamingIfReady() {
  // backend の end と、手元の描画完了が両方そろった時点でターンを閉じる。
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
  syncCharacterVisualMode();
  setComposerDisabled(false);
}

function finalizeStreamingError() {
  // 失敗時も途中まで届いた本文は残しつつ、入力欄と内部状態だけ復旧する。
  resetAudioPlayback();
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
  syncCharacterVisualMode();
  setComposerDisabled(false);
}

function setComposerDisabled(disabled) {
  // 送信中は関連操作をまとめて止め、並行更新で状態が崩れないようにする。
  elements.messageInput.disabled = disabled;
  elements.sendButton.disabled = disabled;
  elements.newConversationButton.disabled = disabled;
  elements.clearConversationButton.disabled = disabled;
}

function showError(message) {
  // 直近のエラー 1 件だけをバナーに表示する。
  elements.errorBanner.textContent = message;
  elements.errorBanner.classList.remove("hidden");
}

function hideError() {
  // 新しい操作開始前に、前回エラー表示を消しておく。
  elements.errorBanner.textContent = "";
  elements.errorBanner.classList.add("hidden");
}

function scrollMessagesToBottom() {
  // 新着メッセージとストリーム更新のたびに末尾へ寄せる。
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

init().catch((error) => {
  showError(error.message || "初期化に失敗しました。");
});
