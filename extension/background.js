const BACKEND_API_BASE = 'http://127.0.0.1:8000';

// Module 2/3: service worker gọi backend thay cho content script trong origin website.
// Cách này tránh Chrome chặn yêu cầu từ trang public tới địa chỉ loopback.
const ALLOWED_API_PATHS = new Set([
    '/api/check-url-safety',
    '/api/check-phishing',
    '/api/extract-content',
    '/api/extract-content-from-html'
]);

// Module 3, FR3.1: click icon để phân tích trang hiện tại đang mở.
chrome.action.onClicked.addListener((tab) => {
    if (tab.id === undefined) return;
    chrome.tabs.sendMessage(tab.id, {
        type: 'hoverai-analyze-current-page'
    }).catch(() => undefined);
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    // Chỉ chuyển tiếp các endpoint đã biết để service worker không thành proxy tùy ý.
    if (message?.type !== 'hoverai-api-request' || !ALLOWED_API_PATHS.has(message.path)) {
        return false;
    }

    fetch(`${BACKEND_API_BASE}${message.path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(message.body)
    })
        .then(async (response) => {
            const data = await response.json().catch(() => null);
            if (!response.ok) {
                sendResponse({
                    ok: false,
                    error: data?.detail || `HTTP_${response.status}`,
                    data
                });
                return;
            }
            sendResponse({ ok: true, data });
        })
        .catch((error) => {
            sendResponse({ ok: false, error: error.message || 'API_REQUEST_FAILED' });
        });

    return true;
});
