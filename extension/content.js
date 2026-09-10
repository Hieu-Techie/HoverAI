const API_TIMEOUT_MS = 4000;        // Đủ cho backend gọi Safe Browsing qua mạng chậm
const CONTENT_API_TIMEOUT_MS = 35000; // Backend fetch(10s) + Gemini(20s) + buffer

// Module 1, FR1.1: trạng thái và timeout để kích hoạt Alt + Hover ổn định.
let isAltPressed = false;           // Theo dõi trạng thái phím Alt.
let lastHoveredLink = null;         // Theo dõi link đang được hover.
let hoverDebounceTimer = null;      // Debounce để tránh gọi API liên tục.
let analysisSequence = 0;            // Bỏ qua kết quả cũ khi người dùng di chuyển nhanh.
const HOVER_DEBOUNCE_DELAY = 300;   // Chờ 300ms trước khi phân tích.

// Module 1, FR1.2: dữ liệu URL/text gửi sang Module 2 và Module 3.
let currentLinkData = {             // Lưu URL và text của link hiện tại
    href: null,
    text: null,
    domain: null
};

/**
 * Bóc tách và chuẩn hóa URL từ phần tử link.
 * @param {HTMLAnchorElement} linkElement - phần tử link cần xử lý
 * @returns {Object} gồm href, normalized và domain
 */
function extractAndNormalizeURL(linkElement) {
    // FR1.2: lấy href, xử lý URL tương đối và chỉ nhận HTTP(S).
    let href = linkElement.getAttribute('href') || '';
    
    // Xử lý URL tương đối.
    if (href.startsWith('/')) {
        href = window.location.origin + href;
    } else if (href.startsWith('#') || href === '') {
        return { href: '', normalized: '', domain: '', isValid: false };
    }
    
    try {
        const url = new URL(href, window.location.origin);
        if (!['http:', 'https:'].includes(url.protocol) || !url.hostname) {
            return { href: '', normalized: '', domain: '', isValid: false };
        }
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
 * Lấy anchor text (text hiển thị) từ phần tử link.
 * @param {HTMLAnchorElement} linkElement - phần tử link cần xử lý
 * @returns {String} anchor text
 */
function extractAnchorText(linkElement) {
    // FR1.2/FR2.2: lấy text hiển thị để detector so sánh với domain đích.
    return linkElement.textContent.trim().substring(0, 100);
}

// Module 1, FR1.3: kích thước và khoảng đệm giữ popup trong viewport.
const POPUP_WIDTH = 480;
const POPUP_HEIGHT = 400;
const PADDING = 12; // Khoảng cách an toàn từ edge

/**
 * Tính vị trí popup và tự lật trái/phải, trên/dưới khi cần.
 * @param {number} mouseClientX - tọa độ X của chuột trong viewport
 * @param {number} mouseClientY - tọa độ Y của chuột trong viewport
 * @returns {Object} left và top theo pixel
 */
function calculateSmartPosition(mouseClientX, mouseClientY) {
    // FR1.3: tính vị trí theo tọa độ chuột và lật popup khi gần cạnh màn hình.
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const offset = 15;
    const popupWidth = Math.min(POPUP_WIDTH, viewportWidth - (PADDING * 2));
    const popupHeight = Math.min(POPUP_HEIGHT, viewportHeight - (PADDING * 2));
    
    let left, top;
    
    // ========== Logic lật trái/phải ==========
    // Nếu popup sẽ tràn sang phải, đẩy sang trái
    if (mouseClientX + offset + popupWidth > viewportWidth) {
        left = Math.max(PADDING, mouseClientX - offset - popupWidth);
    } else {
        left = mouseClientX + offset;
    }
    
    // ========== Logic lật trên/dưới ==========
    // Nếu popup sẽ tràn xuống dưới, đẩy lên trên
    if (mouseClientY + offset + popupHeight > viewportHeight) {
        top = Math.max(PADDING, mouseClientY - offset - popupHeight);
    } else {
        top = mouseClientY + offset;
    }
    
    // Đảm bảo popup không tràn sang trái hoặc trên
    left = Math.max(PADDING, Math.min(left, viewportWidth - popupWidth - PADDING));
    top = Math.max(PADDING, Math.min(top, viewportHeight - popupHeight - PADDING));
    
    return { left, top };
}

// FR1.1: bắt đầu trạng thái kích hoạt khi người dùng nhấn Alt.
document.addEventListener('keydown', function(event) {
    if (event.key === 'Alt') {
        isAltPressed = true;
        // console.log('Alt key pressed');
    }
});

// FR1.1: kết thúc trạng thái kích hoạt khi người dùng nhả Alt.
document.addEventListener('keyup', function(event) {
    if (event.key === 'Alt') {
        isAltPressed = false;
        // console.log('Alt key released');
    }
});

// Module 1: tạo popup UI. History/Deep Scan/chat hiện là placeholder cho Module 3-5.
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
            <div id="hai-content-status" class="content-status" aria-live="polite"></div>
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

// Module 1: giữ tham chiếu tới các vùng UI để cập nhật trạng thái.
const popup = document.getElementById('hoverai-popup');
const statusIcon = document.getElementById('hai-status-icon');
const statusText = document.getElementById('hai-status-text');
const summaryBox = document.getElementById('hai-summary');
const contentStatus = document.getElementById('hai-content-status');
const deepScanBtn = document.getElementById('hai-deepscan-btn');
const historyBtn = document.getElementById('hai-history-btn');
const chatHistory = document.getElementById('hai-chat-history');
const chatInput = document.getElementById('hai-chat-input');
const sendBtn = document.getElementById('hai-send-btn');

function setLoadingState() {
    // FR1.1/FR2: reset popup trước khi bắt đầu request bảo mật mới.
    statusIcon.textContent = '⏳';
    statusText.textContent = 'Đang kiểm tra bảo mật...';
    statusText.className = 'status-loading';
    summaryBox.textContent = 'Đang kiểm tra URL và đối chiếu tên miền hiển thị...';
    contentStatus.textContent = 'Đang lấy nội dung trang đích...';
    contentStatus.className = 'content-status content-loading';
    deepScanBtn.style.display = 'none';
    chatHistory.replaceChildren();
    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;
}

async function fetchJson(path, body, timeoutMs = API_TIMEOUT_MS) {
    // Module 2/3: gửi yêu cầu qua service worker để tránh giới hạn CORS/loopback.
    return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
            reject(new Error('REQUEST_TIMEOUT'));
        }, timeoutMs);

        chrome.runtime.sendMessage({ type: 'hoverai-api-request', path, body }, (response) => {
            clearTimeout(timeoutId);
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }
            if (!response || !response.ok) {
                reject(new Error(response?.error || 'API_REQUEST_FAILED'));
                return;
            }
            resolve(response.data);
        });
    });
}

async function extractTargetLinkContent(linkData) {
    // FR3.1: gửi đúng URL link đích qua service worker, không mở tab mới.
    return fetchJson('/api/extract-content', { url: linkData.href }, CONTENT_API_TIMEOUT_MS);
}

async function extractCurrentPageContent() {
    // FR3.1: lấy DOM của trang đang mở khi người dùng bấm icon extension.
    const html = document.documentElement.outerHTML;
    return fetchJson('/api/extract-content-from-html', {
        url: window.location.href,
        html,
        page_title: document.title
    }, CONTENT_API_TIMEOUT_MS);
}

function showContentResult(result) {
    // FR3.1/FR3.2: hiển thị kết quả tùy theo loại nội dung.
    contentStatus.className = 'content-status content-success';
    if (result.content_type === 'product') {
        showProductResult(result);
    } else {
        showArticleResult(result);
    }
}

function showArticleResult(result) {
    // FR3.1: hiển thị tiêu đề và summary bài viết trong content status.
    contentStatus.textContent = result.summary
        ? `${result.title || 'Nội dung trang đích'}\n\nTóm tắt:\n${result.summary}`
        : `${result.title || 'Nội dung trang đích'}\n\nChưa có bản tóm tắt. Hãy cấu hình GEMINI_API_KEY để bật tính năng này.`;
}

function showProductResult(result) {
    // FR3.2: hiển thị thông tin sản phẩm dạng card có cấu trúc.
    const meta = result.metadata || {};
    const name = result.title || 'Sản phẩm';
    const price = meta.price_display || meta.price || null;
    const rating = meta.rating_display || meta.rating || null;
    const brand = meta.brand || null;
    const note = meta.extraction_note || result.extraction_note || null;

    let lines = [`🛒 ${name}`];
    if (brand) lines.push(`Thương hiệu: ${brand}`);
    if (price) lines.push(`Giá: ${price}`);
    if (rating) lines.push(`Đánh giá: ${rating}`);

    // Ghi chú khi dữ liệu chưa đầy đủ (SPA không render bằng JS)
    if (note === 'SPA_PARTIAL') {
        lines.push('\n⚠️ Trang này dùng JavaScript để tải nội dung. Hãy mở trang và nhấn icon HoverAI để phân tích đầy đủ.');
    } else if (note === 'JINA_PARTIAL') {
        lines.push('\nℹ️ Giá và đánh giá chưa lấy được do trang dùng JavaScript. Mở trang và nhấn icon HoverAI để xem đầy đủ.');
    } else if (note === 'PRICE_NOT_AVAILABLE') {
        lines.push('\nℹ️ Giá sản phẩm không có trong HTML tĩnh. Mở trang để xem giá chính xác.');
    }

    if (result.summary) {
        lines.push(`\nPhân tích AI:\n${result.summary}`);
    } else if (note !== 'SPA_PARTIAL') {
        lines.push('\nChưa có phân tích AI. Hãy cấu hình GEMINI_API_KEY để bật tính năng này.');
    }
    contentStatus.textContent = lines.join('\n');
}

function showCurrentPageResult(result) {
    // FR3.1/FR3.2: kết thúc luồng phân tích trang hiện tại và xóa trạng thái đang tải.
    const isProduct = result.content_type === 'product';
    statusIcon.textContent = isProduct ? '🛒' : '✅';
    statusText.textContent = isProduct ? 'Đã phân tích trang sản phẩm' : 'Đã phân tích trang hiện tại';
    statusText.className = 'status-safe';
    summaryBox.textContent = isProduct
        ? 'Đã lấy thông tin sản phẩm từ trang đang mở.'
        : 'Đã lấy nội dung trang đang mở.';
    showContentResult(result);
}

function showContentError(error, securityResult = null) {
    // FR3.1/FR3.2: báo rõ lỗi trích xuất sau khi kết quả bảo mật đã được hiển thị.
    const reason = error.message || 'CONTENT_EXTRACTION_FAILED';
    contentStatus.className = 'content-status content-error';

    // Timeout của extension (REQUEST_TIMEOUT) — trang đích hoặc backend quá chậm.
    if (reason === 'REQUEST_TIMEOUT') {
        contentStatus.textContent = 'Trang đích phản hồi quá chậm (>35s). Bạn có thể mở trang rồi nhấn icon HoverAI để phân tích trực tiếp.';
        return;
    }

    // PRODUCT_FETCH_FAILED — trang sản phẩm là SPA, cần mở trực tiếp.
    if (reason.startsWith('PRODUCT_FETCH_FAILED')) {
        contentStatus.textContent = 'Trang sản phẩm này cần JavaScript để tải nội dung. Hãy mở trang, sau đó nhấn icon HoverAI trên thanh công cụ để phân tích đầy đủ.';
        return;
    }

    const messages = {
        SOURCE_BOT_CHALLENGE: 'Website đang chặn bot hoặc yêu cầu xác minh (Cloudflare, CAPTCHA). Hãy mở trang trực tiếp rồi dùng icon HoverAI.',
        SOURCE_CONTENT_EMPTY: 'Website không trả về nội dung văn bản (có thể là SPA/JavaScript-only). Hãy mở trang rồi nhấn icon HoverAI để phân tích.',
        CONTENT_NOT_FOUND: 'Không tìm thấy nội dung bài viết phù hợp trên trang này.',
        CONTENT_TYPE_VIDEO_UNSUPPORTED: 'Đây là link video. Tính năng xử lý video sẽ ra mắt ở phiên bản tiếp theo.',
        SOURCE_TIMEOUT: 'Website đích phản hồi quá chậm (>10s). Thử lại hoặc mở trang trực tiếp.',
        SOURCE_UNAVAILABLE: 'Không thể kết nối tới website đích.',
        CONTENT_TIMEOUT: 'Quá thời gian chờ xử lý nội dung trên backend.'
    };

    contentStatus.textContent = messages[reason] || `Không thể lấy nội dung: ${reason}`;

    const linkIsSafe = securityResult?.safety?.safe === true
        && securityResult?.phishing?.is_phishing === false;
    if (linkIsSafe && reason !== 'SOURCE_BOT_CHALLENGE') {
        contentStatus.textContent += '\n✅ Link đã xác minh an toàn. Mở trang rồi nhấn icon HoverAI để phân tích nội dung đầy đủ.';
    }
}

function analyzeCurrentPage() {
    // Module 3, FR3.1: luồng riêng cho trang hiện tại, không dùng currentLinkData.
    setLoadingState();
    statusIcon.textContent = '📄';
    statusText.textContent = 'Đang phân tích trang hiện tại...';
    summaryBox.textContent = 'Đang lấy nội dung trang đang mở...';
    popup.style.left = Math.max(PADDING, (window.innerWidth - POPUP_WIDTH) / 2) + 'px';
    popup.style.top = Math.max(PADDING, (window.innerHeight - POPUP_HEIGHT) / 2) + 'px';
    popup.style.display = 'flex';

    const analysisId = ++analysisSequence;
    extractCurrentPageContent()
        .then((result) => {
            if (analysisId === analysisSequence) showCurrentPageResult(result);
        })
        .catch((error) => {
            if (analysisId === analysisSequence) showContentError(error);
        });
}

async function checkSecurity(linkData) {
    // FR2.1/FR2.2: chạy Safe Browsing và phishing check song song.
    const [safety, phishing] = await Promise.all([
        fetchJson('/api/check-url-safety', { url: linkData.href }),
        fetchJson('/api/check-phishing', {
            href_url: linkData.href,
            anchor_text: linkData.text
        })
    ]);
    return { safety, phishing };
}

function showSecurityResult(result) {
    // FR2.1/FR2.2: chuyển response backend thành trạng thái dễ đọc trong popup.
    const { safety, phishing } = result;
    const cannotVerify = ['API_KEY_MISSING', 'TIMEOUT', 'UNKNOWN_ERROR'].some(
        (errorType) => safety.threat_type === errorType
    ) || safety.threat_type.startsWith('API_ERROR_');

    if (phishing.is_phishing) {
        statusIcon.textContent = '⚠️';
        statusText.textContent = 'CẢNH BÁO: Phát hiện liên kết lừa đảo';
        statusText.className = 'status-danger';
        summaryBox.textContent = phishing.mismatch_warning;
        return;
    }

    if (cannotVerify) {
        statusIcon.textContent = '⚠️';
        statusText.textContent = 'Không thể xác minh an toàn';
        statusText.className = 'status-loading';
        summaryBox.textContent = `Không thể hoàn tất kiểm tra: ${safety.threat_type}. Hãy kiểm tra backend và API key.`;
        return;
    }

    statusIcon.textContent = safety.safe ? '✅' : '⚠️';
    statusText.textContent = safety.safe ? 'Liên kết an toàn' : 'CẢNH BÁO: URL nguy hiểm';
    statusText.className = safety.safe ? 'status-safe' : 'status-danger';
    summaryBox.textContent = safety.safe
        ? 'Safe Browsing không phát hiện mối đe dọa đã biết trên URL này.'
        : `Safe Browsing phát hiện mối đe dọa: ${safety.threat_type}.`;
}

// FR1.1/FR1.3: bắt hover, debounce, định vị popup và khởi chạy phân tích.
document.addEventListener('mouseover', function(event) {
    let target = event.target.closest('a'); 
    
    // Kiểm tra có link, có href và phím Alt đang được giữ.
    if (target && target.href && isAltPressed) {
        // Nếu vẫn ở cùng link thì bỏ qua.
        if (lastHoveredLink === target) return;
        lastHoveredLink = target;
        
        // Debounce: tránh gọi API khi người dùng di chuyển chuột quá nhanh.
        clearTimeout(hoverDebounceTimer);
        
        hoverDebounceTimer = setTimeout(() => {
            // FR1.2: trích xuất URL và text trước khi gọi các API bảo mật.
            const urlData = extractAndNormalizeURL(target);
            const anchorText = extractAnchorText(target);
            
            // FR1.2: lưu dữ liệu link hiện tại cho FR2.2 và FR3.1.
            currentLinkData = {
                href: urlData.href,
                text: anchorText,
                domain: urlData.domain
            };
            
            // FR1.2: bỏ qua anchor, javascript: hoặc URL không hợp lệ.
            if (!urlData.isValid) return;
            
            // FR1.1: reset giao diện và bắt đầu trạng thái loading.
            setLoadingState();

            // FR1.3: đặt popup cạnh con trỏ nhưng không vượt viewport.
            const position = calculateSmartPosition(event.clientX, event.clientY);
            popup.style.left = position.left + 'px';
            popup.style.top = position.top + 'px';
            popup.style.display = 'flex';

            const analysisId = ++analysisSequence;
            checkSecurity(currentLinkData)
                .then((result) => {
                    if (analysisId === analysisSequence) {
                        showSecurityResult(result);
                        extractTargetLinkContent(currentLinkData)
                            .then((content) => {
                                if (analysisId === analysisSequence) {
                                    showContentResult(content);
                                }
                            })
                            .catch((error) => {
                                if (analysisId === analysisSequence) {
                                    showContentError(error, result);
                                }
                            });
                    }
                })
                .catch((err) => {
                    if (analysisId !== analysisSequence) return;
                    const isTimeout = err?.message === 'REQUEST_TIMEOUT';
                    statusIcon.textContent = '⚠️';
                    statusText.textContent = isTimeout ? 'Kiểm tra bảo mật quá chậm' : 'Không thể kết nối backend';
                    statusText.className = 'status-loading';
                    summaryBox.textContent = isTimeout
                        ? 'Kiểm tra bảo mật mất quá nhiều thời gian. Mạng hoặc backend đang tải nặng. Thử lại sau vài giây.'
                        : 'Không thể kết nối tới backend. Hãy đảm bảo backend đang chạy tại http://127.0.0.1:8000.';
                });
        }, HOVER_DEBOUNCE_DELAY);
    }
});

// FR1.1: reset trạng thái debounce khi con trỏ rời link.
document.addEventListener('mouseout', function(event) {
    let target = event.target.closest('a');
    if (target && lastHoveredLink === target) {
        lastHoveredLink = null;
        clearTimeout(hoverDebounceTimer);
    }
});

// Module 3, FR3.5: hiện vẫn là mock, chưa gọi yt-dlp/Gemini.
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

// Module 5, FR5.2: hiện là mock, options dashboard chưa được triển khai.
historyBtn.addEventListener('click', function() {
    alert("Tính năng này sẽ mở ra trang History Dashboard (Bảng điều khiển lịch sử tri thức) trong phiên bản hoàn chỉnh!");
});

// Module 4, FR4.3: hiện chỉ hiển thị tin nhắn local, chưa kết nối RAG/Gemini.
function handleChat() {
    let userText = chatInput.value.trim();
    if (!userText) return;

    const userMessage = document.createElement('div');
    userMessage.className = 'chat-msg msg-user';
    userMessage.textContent = userText;
    chatHistory.appendChild(userMessage);
    chatInput.value = '';
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

sendBtn.addEventListener('click', handleChat);
chatInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleChat();
});

// Module 1: đóng popup khi click ra ngoài.
document.addEventListener('click', function(event) {
    if (!popup.contains(event.target)) {
        popup.style.display = 'none';
    }
});

window.addEventListener('blur', function() {
    isAltPressed = false;
});

// Module 3, FR3.1: nhận lệnh từ action icon để phân tích trang hiện tại.
chrome.runtime.onMessage.addListener(function(message) {
    if (message?.type === 'hoverai-analyze-current-page') {
        analyzeCurrentPage();
    }
});