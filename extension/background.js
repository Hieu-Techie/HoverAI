const BACKEND_API_BASE = 'http://127.0.0.1:8000';

// Module 2/3: service worker gọi backend thay cho content script trong origin website.
// Cách này tránh Chrome chặn yêu cầu từ trang public tới địa chỉ loopback.
const ALLOWED_API_PATHS = new Set([
    '/api/check-url-safety',
    '/api/check-phishing',
    '/api/extract-content',
    '/api/extract-content-from-html'
]);

// Timeout cho browser-side fetch (ms) — đủ cho trang chậm.
const BROWSER_FETCH_TIMEOUT_MS = 8000;

// Module 3, FR3.1: click icon để phân tích trang hiện tại đang mở.
chrome.action.onClicked.addListener((tab) => {
    if (tab.id === undefined) return;
    chrome.tabs.sendMessage(tab.id, {
        type: 'hoverai-analyze-current-page'
    }).catch(() => undefined);
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    // -----------------------------------------------------------------------
    // Phương án 2: Shopee / Lazada internal JSON API
    // -----------------------------------------------------------------------
    if (message?.type === 'fetch-shopee-product') {
        const { shopId, itemId } = message;

        // Thử v4 trước (đầy đủ dữ liệu nhất), fallback v2 nếu cần login.
        const endpoints = [
            `https://shopee.vn/api/v4/item/get?itemid=${itemId}&shopid=${shopId}`,
            `https://shopee.vn/api/v2/item/get?itemid=${itemId}&shopid=${shopId}`,
        ];
        const SHOPEE_HEADERS = {
            'Accept': 'application/json',
            'Referer': 'https://shopee.vn/',
            'User-Agent': navigator.userAgent,
            'X-Requested-With': 'XMLHttpRequest',
        };

        const tryEndpoint = (url) => new Promise((resolve, reject) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), BROWSER_FETCH_TIMEOUT_MS);
            fetch(url, { credentials: 'include', headers: SHOPEE_HEADERS, signal: controller.signal })
                .then(async (res) => {
                    clearTimeout(timer);
                    if (!res.ok) { reject(new Error(`HTTP_${res.status}`)); return; }
                    const json = await res.json();
                    // Shopee trả 200 nhưng error code = need login
                    const errCode = json?.error || json?.data?.error;
                    if (errCode && errCode !== 0) { reject(new Error(`SHOPEE_ERR_${errCode}`)); return; }
                    if (!json?.data?.item) { reject(new Error('SHOPEE_DATA_EMPTY')); return; }
                    resolve(json);
                })
                .catch((err) => { clearTimeout(timer); reject(err); });
        });

        // Thử lần lượt các endpoint
        (async () => {
            for (const ep of endpoints) {
                try {
                    const json = await tryEndpoint(ep);
                    sendResponse({ ok: true, data: json });
                    return;
                } catch (_) { /* tiếp tục thử endpoint tiếp theo */ }
            }
            sendResponse({ ok: false, error: 'SHOPEE_ALL_ENDPOINTS_FAILED' });
        })();

        return true; // async response
    }

    // -----------------------------------------------------------------------
    // Phương án 1: Browser-side HTML fetch (dùng cookie + IP người dùng)
    // -----------------------------------------------------------------------
    if (message?.type === 'fetch-page-html') {
        const { url } = message;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), BROWSER_FETCH_TIMEOUT_MS);

        fetch(url, {
            credentials: 'include',           // gửi session cookies nếu user đã login
            headers: {
                'Accept': 'text/html,application/xhtml+xml,*/*;q=0.9',
                'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
                'User-Agent': navigator.userAgent,
            },
            signal: controller.signal
        })
            .then(async (res) => {
                clearTimeout(timer);
                if (!res.ok) { sendResponse({ ok: false, error: `HTTP_${res.status}` }); return; }
                const contentType = res.headers.get('Content-Type') || '';
                if (!contentType.includes('html')) {
                    sendResponse({ ok: false, error: 'NOT_HTML' });
                    return;
                }
                const buffer = await res.arrayBuffer();
                // Giới hạn 2MB để tránh message quá lớn
                if (buffer.byteLength > 2 * 1024 * 1024) {
                    sendResponse({ ok: false, error: 'HTML_TOO_LARGE' });
                    return;
                }
                const html = new TextDecoder('utf-8', { fatal: false }).decode(buffer);
                sendResponse({ ok: true, html, finalUrl: res.url });
            })
            .catch((err) => {
                clearTimeout(timer);
                sendResponse({ ok: false, error: err.name === 'AbortError' ? 'BROWSER_FETCH_TIMEOUT' : 'BROWSER_FETCH_FAILED' });
            });
        return true; // async response
    }

    // -----------------------------------------------------------------------
    // Proxy backend API (gọi localhost:8000 từ service worker)
    // -----------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// FR3.5 Deep Scan — long-lived port để tránh message port timeout (30-90s)
// Content script trên TikTok/YouTube bị CSP chặn fetch localhost trực tiếp,
// nên phải route qua service worker. Dùng onConnect thay onMessage vì
// sendMessage có timeout ngắn không đủ cho Deep Scan.
// ---------------------------------------------------------------------------
chrome.runtime.onConnect.addListener((port) => {
    if (port.name !== 'hoverai-deepscan') return;

    port.onMessage.addListener(async (message) => {
        if (message?.type !== 'start-deepscan' || !message.url) {
            port.postMessage({ ok: false, error: 'INVALID_REQUEST' });
            return;
        }

        // Lấy cookies của domain video (YouTube, Facebook, TikTok, v.v.) để bypass bot detection của yt-dlp
        // Extension có quyền đọc cookies của mọi domain (host_permissions: <all_urls>)
        let ytCookieHeader = '';
        try {
            const videoUrlObj = new URL(message.url);
            const hostname = videoUrlObj.hostname;
            const domainParts = hostname.split('.');
            const baseDomain = domainParts.length >= 2 ? '.' + domainParts.slice(-2).join('.') : hostname;

            const cookieDomains = new Set(['.youtube.com', '.google.com', baseDomain, '.' + hostname, hostname]);
            const allCookies = [];
            for (const domain of cookieDomains) {
                try {
                    const cookies = await chrome.cookies.getAll({ domain });
                    if (cookies) allCookies.push(...cookies);
                } catch (_) {}
            }
            // Loại bỏ cookie trùng tên
            const uniqueCookies = [];
            const seen = new Set();
            for (const c of allCookies) {
                if (!seen.has(c.name)) {
                    seen.add(c.name);
                    uniqueCookies.push(c);
                }
            }
            ytCookieHeader = uniqueCookies
                .map(c => `${c.name}=${c.value}`)
                .join('; ');
        } catch (_) {
            // Nếu không lấy được cookies → vẫn thử không có
        }

        try {
            const resp = await fetch(`${BACKEND_API_BASE}/api/deepscan-audio`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: message.url,
                    yt_cookie_header: ytCookieHeader || undefined,
                }),
            });
            const data = await resp.json().catch(() => null);
            if (!resp.ok) {
                port.postMessage({ ok: false, error: data?.detail || `HTTP_${resp.status}` });
            } else {
                port.postMessage({ ok: true, data });
            }
        } catch (err) {
            port.postMessage({ ok: false, error: err.message || 'FETCH_FAILED' });
        }
    });
});

