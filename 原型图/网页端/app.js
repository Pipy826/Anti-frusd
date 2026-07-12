const screens = document.querySelectorAll(".screen");
const modal = document.querySelector("#modeModal");
const chatTitle = document.querySelector("#chatTitle");
const messages = document.querySelector("#messages");
const input = document.querySelector("#replyInput");

const scenes = [
  "快递理赔诈骗",
  "AI冒充亲友借钱",
  "AI兼职刷单诈骗"
];

let currentScene = 0;

function showScreen(name) {
  screens.forEach(screen => screen.classList.toggle("is-active", screen.dataset.screen === name));
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
}

function openModal(sceneIndex) {
  currentScene = Number(sceneIndex);
  chatTitle.textContent = scenes[currentScene];
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
}

function selectedMode() {
  return document.querySelector("input[name='mode']:checked").value;
}

document.querySelectorAll("[data-scene]").forEach(button => {
  button.addEventListener("click", () => openModal(button.dataset.scene));
});

document.querySelectorAll("[data-go]").forEach(button => {
  button.addEventListener("click", () => showScreen(button.dataset.go));
});

document.querySelector("#closeModal").addEventListener("click", () => modal.classList.remove("is-open"));
document.querySelector("#cancelModal").addEventListener("click", () => modal.classList.remove("is-open"));
document.querySelector("#startMode").addEventListener("click", () => {
  const mode = selectedMode();
  if (mode === "phone") showScreen("incoming");
  else if (mode === "video") showScreen("video");
  else showScreen("chat");
});

document.querySelectorAll(".mode").forEach(label => {
  label.addEventListener("click", () => {
    document.querySelectorAll(".mode").forEach(item => item.classList.remove("active"));
    label.classList.add("active");
  });
});

document.querySelectorAll(".quick button").forEach(button => {
  button.addEventListener("click", () => {
    input.value = button.textContent;
    input.focus();
  });
});

document.querySelector("#composer").addEventListener("submit", event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  appendMessage(text, "me");
  input.value = "";
  window.setTimeout(() => appendMessage("建议您先提供身份证号和银行卡信息，这样理赔会更快到账。", "ai"), 480);
});

function appendMessage(text, type) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${type === "me" ? "me" : "ai"}`;
  const avatar = document.createElement("img");
  avatar.src = type === "me" ? "./assets/user.png" : "./assets/bot.png";
  avatar.alt = "";
  const bubble = document.createElement("p");
  bubble.textContent = text;
  if (type === "me") {
    wrap.append(bubble, avatar);
  } else {
    wrap.append(avatar, bubble);
  }
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
}
