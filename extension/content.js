// Kho dữ liệu giả lập (Mock Data)
const mockScenarios = [
    {
        icon: "✅",
        status: "Liên kết an toàn",
        statusClass: "status-safe",
        summary: "<b>Tóm tắt Bài báo:</b> Bài báo hướng dẫn chi tiết cách thiết lập dự án trí tuệ nhân tạo, bao gồm phần cứng và thuật toán.",
        aiGreeting: "Tôi đã đọc xong bài viết này. Bạn muốn hỏi gì thêm không?",
        aiReply: "Theo bài viết, hệ thống ưu tiên dùng thuật toán 'Thác nước' để tối ưu tốc độ.",
        hasDeepScan: false
    },
    {
        icon: "✅",
        status: "An toàn - Nguồn: YouTube",
        statusClass: "status-safe",
        summary: "<b>Tóm tắt nhanh (Dựa trên Tiêu đề):</b> Video dài 15 phút nói về 5 mẹo quản lý tài chính cá nhân.<br><i style='color:#f59e0b; font-size:12px;'>⚠️ Video này không có phụ đề sẵn.</i>",
        aiGreeting: "Video này không có phụ đề. Bạn có thể nhấn 'Deep Scan' để tôi nghe trực tiếp âm thanh nhé.",
        aiReply: "Bạn phải quét âm thanh trước tôi mới có thể trả lời chi tiết được.",
        hasDeepScan: true
    },
    {
        icon: "⚠️",
        status: "CẢNH BÁO: Phát hiện liên kết lừa đảo!",
        statusClass: "status-danger",
        summary: "<b style='color:red;'>Nội dung bị chặn:</b> Chữ hiển thị là báo Dân Trí, nhưng đích đến lại là Shopee Affiliate.",
        aiGreeting: "Cẩn thận! Link này chuyển hướng ngầm. Đừng nhấp vào.",
        aiReply: "Hệ thống chặn lại để bảo vệ bạn khỏi các rủi ro không mong muốn.",
        hasDeepScan: false
    }
];

let currentScenario = null;

// ============ FR1.1: Alt+Hover Event State Management ============
let isAltPressed = false;           // Theo dõi trạng thái Alt key
let lastHoveredLink = null;         // Theo dõi link đang hover
let hoverDebounceTimer = null;      // Debounce timer để tránh gọi API liên tục
const HOVER_DEBOUNCE_DELAY = 300;   // 300ms debounce

// ============ FR1.2: URL Extraction ============
let currentLinkData = {             // Lưu URL và text của link hiện tại
    href: null,
    text: null,
    domain: null
};

/**
 * Bóc tách và chuẩn hóa URL từ link element
 * @param {HTMLAnchorElement} linkElement - Link element
 * @returns {Object} { href, normalized, domain }
 */
function extractAndNormalizeURL(linkElement) {
    let href = linkElement.getAttribute('href') || '';
    
    // Xử lý relative URLs
    if (href.startsWith('/')) {
        href = window.location.origin + href;
    } else if (href.startsWith('#') || href === '') {
        return { href: '', normalized: '', domain: '', isValid: false };
    }
    
    try {
        const url = new URL(href, window.location.origin);
        const domain = url.hostname.replace('www.', '');
        return {
            href: url.href,
            normalized: url.href.split('?')[0], // Loại bỏ query params
            domain: domain,
            isValid: true
        };
    } catch (e) {
        return { href: '', normalized: '', domain: '', isValid: false };
    }
}

/**
 * Lấy anchor text (text hiển thị) từ link element
 * @param {HTMLAnchorElement} linkElement - Link element
 * @returns {String} Anchor text
 */
function extractAnchorText(linkElement) {
    return linkElement.textContent.trim().substring(0, 100);
}

// ============ FR1.3: Smart Positioning ============
const POPUP_WIDTH = 480;
const POPUP_HEIGHT = 400;
const PADDING = 12; // Khoảng cách an toàn từ edge

/**
 * Tính toán vị trí tối ưu cho popup (auto-flip left/right, top/bottom)
 * @param {number} mouseClientX - Mouse X position relative to viewport
 * @param {number} mouseClientY - Mouse Y position relative to viewport
 * @returns {Object} { left, top } in pixels
 */
function calculateSmartPosition(mouseClientX, mouseClientY) {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const offset = 15;
    
    let left, top;
    
    // ========== Flip Left/Right Logic ==========
    // Nếu popup sẽ tràn sang phải, đẩy sang trái
    if (mouseClientX + offset + POPUP_WIDTH > viewportWidth) {
        left = Math.max(PADDING, mouseClientX - offset - POPUP_WIDTH);
    } else {
        left = mouseClientX + offset;
    }
    
    // ========== Flip Top/Bottom Logic ==========
    // Nếu popup sẽ tràn xuống dưới, đẩy lên trên
    if (mouseClientY + offset + POPUP_HEIGHT > viewportHeight) {
        top = Math.max(PADDING, mouseClientY - offset - POPUP_HEIGHT);
    } else {
        top = mouseClientY + offset;
    }
    
    // Đảm bảo popup không tràn sang trái hoặc trên
    left = Math.max(PADDING, Math.min(left, viewportWidth - POPUP_WIDTH - PADDING));
    top = Math.max(PADDING, Math.min(top, viewportHeight - POPUP_HEIGHT - PADDING));
    
    return { left, top };
}

// Lắng nghe Alt key press
document.addEventListener('keydown', function(event) {
    if (event.key === 'Alt') {
        isAltPressed = true;
        // console.log('Alt key pressed');
    }
});

// Lắng nghe Alt key release
document.addEventListener('keyup', function(event) {
    if (event.key === 'Alt') {
        isAltPressed = false;
        // console.log('Alt key released');
    }
});

// 1. Nhúng HTML của Popup (Thêm Lịch sử và Deep Scan)
const popupHTML = `
  <div id="hoverai-popup">
    <div class="hoverai-header">
      <div class="header-left">
        <span id="hai-status-icon">⏳</span> 
        <span id="hai-status-text" class="status-loading">Đang phân tích liên kết...</span>
      </div>
      <button id="hai-history-btn" title="Mở trang quản lý tri thức">Lịch sử ↗</button>
    </div>
    
    <div class="hoverai-summary">
      <div id="hai-summary"><i style="color: #94a3b8;">Hệ thống AI đang bóc tách nội dung...</i></div>
      <button id="hai-deepscan-btn" style="display: none;">🔍 Deep Scan (Quét âm thanh nâng cao)</button>
    </div>
    
    <div class="hoverai-chat-area">
      <div class="chat-history" id="hai-chat-history"></div>
      <div class="chat-input-box">
        <input type="text" id="hai-chat-input" placeholder="Hỏi thêm về link này..." disabled />
        <button id="hai-send-btn" disabled>Gửi</button>
      </div>
    </div>
  </div>
`;

document.body.insertAdjacentHTML('beforeend', popupHTML);

// 2. Các biến DOM
const popup = document.getElementById('hoverai-popup');
const statusIcon = document.getElementById('hai-status-icon');
const statusText = document.getElementById('hai-status-text');
const summaryBox = document.getElementById('hai-summary');
const deepScanBtn = document.getElementById('hai-deepscan-btn');
const historyBtn = document.getElementById('hai-history-btn');
const chatHistory = document.getElementById('hai-chat-history');
const chatInput = document.getElementById('hai-chat-input');
const sendBtn = document.getElementById('hai-send-btn');

let demoTimeout;

// 3. Xử lý sự kiện Alt + Di chuột & Smart Positioning
document.addEventListener('mouseover', function(event) {
    let target = event.target.closest('a'); 
    
    // Kiểm tra: có link, có href, và Alt đang được bấm
    if (target && target.href && isAltPressed) {
        // Nếu đã hover link khác, skip (tránh debounce liên tục)
        if (lastHoveredLink === target) return;
        lastHoveredLink = target;
        
        // Debounce: tránh gọi API nếu user di chuyển chuột quá nhanh
        clearTimeout(hoverDebounceTimer);
        
        hoverDebounceTimer = setTimeout(() => {
            clearTimeout(demoTimeout);
            
            // ========== FR1.2: Extract URL & Anchor Text ==========
            const urlData = extractAndNormalizeURL(target);
            const anchorText = extractAnchorText(target);
            
            // Lưu dữ liệu link hiện tại cho backend API call sau
            currentLinkData = {
                href: urlData.href,
                text: anchorText,
                domain: urlData.domain
            };
            
            // Nếu URL không hợp lệ, không show popup
            if (!urlData.isValid) return;
            
            // Reset giao diện
            statusIcon.textContent = "⏳";
            statusText.textContent = "Đang phân tích liên kết...";
            statusText.className = "status-loading";
            summaryBox.innerHTML = '<i style="color: #94a3b8;">Hệ thống AI đang bóc tách nội dung...</i>';
            deepScanBtn.style.display = 'none';
            chatHistory.innerHTML = '';
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;

            // ========== FR1.3: Smart Positioning ==========
            const position = calculateSmartPosition(event.clientX, event.clientY);
            popup.style.left = position.left + 'px';
            popup.style.top = position.top + 'px';
            popup.style.display = 'flex';

            currentScenario = mockScenarios[Math.floor(Math.random() * mockScenarios.length)];

            // Bắt đầu giả lập API
            demoTimeout = setTimeout(() => {
                statusIcon.textContent = currentScenario.icon;
                statusText.textContent = currentScenario.status;
                statusText.className = currentScenario.statusClass;
                summaryBox.innerHTML = currentScenario.summary;
                
                if(currentScenario.hasDeepScan) {
                    deepScanBtn.style.display = 'flex';
                }
                
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatHistory.innerHTML = `<div class="chat-msg msg-ai">${currentScenario.aiGreeting}</div>`;
            }, 1200); 
        }, HOVER_DEBOUNCE_DELAY);
    }
});

// Khi mouseout khỏi link, reset hover state
document.addEventListener('mouseout', function(event) {
    let target = event.target.closest('a');
    if (target && lastHoveredLink === target) {
        lastHoveredLink = null;
        clearTimeout(hoverDebounceTimer);
    }
});

// 4. Giả lập tính năng Deep Scan
deepScanBtn.addEventListener('click', function() {
    deepScanBtn.innerHTML = "⏳ Đang tải và phân tích Audio...";
    deepScanBtn.disabled = true;
    chatHistory.innerHTML += `<div class="chat-msg msg-user"><i>*Đã kích hoạt Deep Scan*</i></div>`;
    chatHistory.scrollTop = chatHistory.scrollHeight;

    setTimeout(() => {
        deepScanBtn.style.display = 'none'; // Quét xong thì ẩn đi
        summaryBox.innerHTML += "<br><br><b>Kết quả Deep Scan:</b> Ở phút 04:20, chủ kênh có nói rõ: 50% cho nhu cầu thiết yếu, 30% cho sở thích và 20% bắt buộc phải tiết kiệm hoặc đầu tư.";
        chatHistory.innerHTML += `<div class="chat-msg msg-ai">Tôi đã nghe xong video. Bây giờ bạn có thể hỏi tôi bất kỳ chi tiết nào nhé!</div>`;
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }, 2500); // Đợi 2.5 giây mô phỏng xử lý âm thanh
});

// 5. Nút Lịch sử mở trang giả lập
historyBtn.addEventListener('click', function() {
    alert("Tính năng này sẽ mở ra trang History Dashboard (Bảng điều khiển lịch sử tri thức) trong phiên bản hoàn chỉnh!");
});

// 6. Xử lý tính năng Chat
function handleChat() {
    let userText = chatInput.value.trim();
    if (!userText) return;

    chatHistory.innerHTML += `<div class="chat-msg msg-user">${userText}</div>`;
    chatInput.value = '';
    chatHistory.scrollTop = chatHistory.scrollHeight;

    setTimeout(() => {
        chatHistory.innerHTML += `<div class="chat-msg msg-ai">${currentScenario.aiReply}</div>`;
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }, 800);
}

sendBtn.addEventListener('click', handleChat);
chatInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleChat();
});

// 7. Đóng popup
document.addEventListener('click', function(event) {
    if (!popup.contains(event.target)) {
        popup.style.display = 'none';
    }
});