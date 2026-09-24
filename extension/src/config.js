const API_TIMEOUT_MS = 4000;
const CONTENT_API_TIMEOUT_MS = 35000;
const DEEPSCAN_TIMEOUT_MS = 200000; // FR3.5

let isAltPressed = false;
let lastHoveredLink = null;
let hoverDebounceTimer = null;
let analysisSequence = 0;
const HOVER_DEBOUNCE_DELAY = 300;

let currentLinkData = {
    href: null,
    text: null,
    domain: null
};

let currentVideoUrl = null; // FR3.5

let popup, contentStatus, statusIcon, statusText, summaryBox, chatHistory, chatInput, sendBtn, historyBtn, deepScanBtn;

// Module 1, FR1.3: kích thước và khoảng đệm giữ popup trong viewport.
const POPUP_WIDTH = 480;
const POPUP_HEIGHT = 400;
const PADDING = 12; // Khoảng cách an toàn từ edge
