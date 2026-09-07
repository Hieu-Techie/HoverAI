const BACKEND_API_BASE = 'http://127.0.0.1:8000';
const ALLOWED_API_PATHS = new Set([
    '/api/check-url-safety',
    '/api/check-phishing'
]);

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
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
                sendResponse({ ok: false, error: `HTTP_${response.status}`, data });
                return;
            }
            sendResponse({ ok: true, data });
        })
        .catch((error) => {
            sendResponse({ ok: false, error: error.message || 'API_REQUEST_FAILED' });
        });

    return true;
});
