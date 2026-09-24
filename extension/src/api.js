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