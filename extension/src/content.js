document.addEventListener('keydown', function(event) {
    if (event.key === 'Alt') {
        isAltPressed = true;
        // console.log('Alt key pressed');
    }
});

document.addEventListener('keyup', function(event) {
    if (event.key === 'Alt') {
        isAltPressed = false;
        // console.log('Alt key released');
    }
});

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
                    statusIcon.textContent = 'ΓÜá∩╕Å';
                    statusText.textContent = isTimeout ? 'Kiểm tra bảo mật quá chậm' : 'Không thể kết nối backend';
                    statusText.className = 'status-loading';
                    summaryBox.textContent = isTimeout
                        ? 'Kiểm tra bảo mật mất quá nhiều thời gian. Mạng hoặc backend đang tải nặng. Thử lại sau vài giây.'
                        : 'Không thể kết nối tới backend. Hãy đảm bảo backend đang chạy tại http://127.0.0.1:8000.';
                });
        }, HOVER_DEBOUNCE_DELAY);
    }
});

document.addEventListener('mouseout', function(event) {
    let target = event.target.closest('a');
    if (target && lastHoveredLink === target) {
        lastHoveredLink = null;
        clearTimeout(hoverDebounceTimer);
    }
});

document.addEventListener('click', function(event) {
    if (!popup.contains(event.target)) {
        popup.style.display = 'none';
    }
});

window.addEventListener('blur', function() {
    isAltPressed = false;
});

chrome.runtime.onMessage.addListener(function(message) {
    if (message?.type === 'hoverai-analyze-current-page') {
        analyzeCurrentPage();
    }
});

sendBtn.addEventListener('click', handleChat);

chatInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleChat();
});

historyBtn.addEventListener('click', function() {
    alert("Tính năng này sẽ mở ra trang History Dashboard (Bảng điều khiển lịch sử tri thức) trong phiên bản hoàn chỉnh!");
});

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

deepScanBtn.addEventListener('click', function () {
    if (!currentVideoUrl) {
        contentStatus.textContent = 'Lỗi: không tìm thấy URL video.';
        return;
    }

    deepScanBtn.textContent = '⏳ Đang quét âm thanh... (~30-90s)';
    deepScanBtn.disabled = true;
    chatHistory.innerHTML += `<div class="chat-msg msg-user"><i>*Đã kích hoạt Deep Scan*</i></div>`;
    chatHistory.scrollTop = chatHistory.scrollHeight;
    contentStatus.className = 'content-status content-loading';
    contentStatus.textContent =
        'Đang tải audio và phân tích bằng Gemini...\n' +
        'Quá trình này mất khoảng 30–90 giây tùy độ dài video.';

    // FR3.5: dùng chrome.runtime.connect() (long-lived port) thay vì sendMessage/fetch() vì:
    // - sendMessage: message port đóng trước khi Deep Scan hoàn thành (30-90s)
    // - fetch() trực tiếp: TikTok/YouTube CSP chặn kết nối đến localhost
    // - connect(): port sống đến khi disconnect(), không bị timeout
    const port = chrome.runtime.connect({ name: 'hoverai-deepscan' });

    const timeoutId = setTimeout(() => {
        port.disconnect();
        contentStatus.className = 'content-status content-error';
        contentStatus.textContent = 'Deep Scan lỗi: Quá thời gian chờ. Video có thể quá dài hoặc kết nối chậm.';
        deepScanBtn.textContent = '🔍 Deep Scan (Quét âm thanh nâng cao)';
        deepScanBtn.disabled = false;
    }, DEEPSCAN_TIMEOUT_MS);

    port.onMessage.addListener(function(response) {
        clearTimeout(timeoutId);
        port.disconnect();

        if (response.ok) {
            showDeepScanResult(response.data);
            chatHistory.innerHTML += `<div class="chat-msg msg-ai">Tôi đã nghe xong video. Bây giờ bạn có thể hỏi tôi bất kỳ chi tiết nào nhé!</div>`;
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } else {
            contentStatus.className = 'content-status content-error';
            const msg = response.error || 'DEEPSCAN_ERROR';
            const friendly = {
                REQUEST_TIMEOUT: 'Quá thời gian chờ. Video có thể quá dài hoặc kết nối chậm.',
                AUDIO_DOWNLOAD_FAILED: 'Không thể tải audio từ video này.',
                AUDIO_FILE_TOO_LARGE: 'File audio quá lớn. Thử với video ngắn hơn (< 15 phút).',
                GEMINI_API_KEY_REQUIRED: 'Cần cấu hình GEMINI_API_KEY để dùng Deep Scan.',
                DEEPSCAN_TIMEOUT: 'Quá thời gian xử lý (max 3 phút).',
                FETCH_FAILED: 'Không thể kết nối đến backend. Hãy đảm bảo server đang chạy.',
            };
            contentStatus.textContent = `Deep Scan lỗi: ${friendly[msg] || msg}`;
            deepScanBtn.textContent = '🔍 Deep Scan (Quét âm thanh nâng cao)';
            deepScanBtn.disabled = false;
        }
    });

    port.onDisconnect.addListener(function() {
        // Port bị đóng ngoài ý muốn (service worker crash, extension reload...)
        clearTimeout(timeoutId);
        if (deepScanBtn.disabled) {
            contentStatus.className = 'content-status content-error';
            contentStatus.textContent = 'Deep Scan lỗi: Kết nối bị ngắt. Hãy thử lại.';
            deepScanBtn.textContent = '🔍 Deep Scan (Quét âm thanh nâng cao)';
            deepScanBtn.disabled = false;
        }
    });

    port.postMessage({ type: 'start-deepscan', url: currentVideoUrl });
});