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
    // FR3.1/FR3.2: Cố gắng lấy HTML qua browser-fetch (có cookie, bypass SPA)
    // trước, rồi gửi HTML đó lên backend. Nếu browser-fetch thất bại (CORS,
    // bot-check thực sự), fallback về backend tự tải URL.
    return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => reject(new Error('REQUEST_TIMEOUT')), CONTENT_API_TIMEOUT_MS);

        // Bước 1: yêu cầu Service Worker tải HTML trang đích với cookie người dùng
        chrome.runtime.sendMessage({ type: 'fetch-page-html', url: linkData.href }, (htmlResponse) => {
            if (chrome.runtime.lastError || !htmlResponse?.ok || !htmlResponse?.html) {
                // Browser-fetch thất bại → fallback: backend tự tải URL
                chrome.runtime.sendMessage(
                    { type: 'hoverai-api-request', path: '/api/extract-content', body: { url: linkData.href } },
                    (apiResponse) => {
                        clearTimeout(timeoutId);
                        if (chrome.runtime.lastError || !apiResponse?.ok) {
                            reject(new Error(apiResponse?.error || 'API_REQUEST_FAILED'));
                        } else {
                            resolve(apiResponse.data);
                        }
                    }
                );
                return;
            }

            // Bước 2: gửi HTML đã lấy được lên /api/extract-content-from-html
            const finalUrl = htmlResponse.finalUrl || linkData.href;
            chrome.runtime.sendMessage(
                {
                    type: 'hoverai-api-request',
                    path: '/api/extract-content-from-html',
                    body: { url: finalUrl, html: htmlResponse.html, page_title: '' }
                },
                (apiResponse) => {
                    clearTimeout(timeoutId);
                    if (chrome.runtime.lastError || !apiResponse?.ok) {
                        reject(new Error(apiResponse?.error || 'API_REQUEST_FAILED'));
                    } else {
                        resolve(apiResponse.data);
                    }
                }
            );
        });
    });
}

/**
 * Trích shopId và itemId từ URL Shopee.
 * Pattern: /ten-san-pham-i.<shopId>.<itemId>
 * Trả về { shopId, itemId } hoặc null nếu không khớp.
 */
function parseShopeeIds(url) {
    const m = url.match(/-i\.(\d+)\.(\d+)/);
    if (!m) return null;
    return { shopId: m[1], itemId: m[2] };
}

/**
 * Gọi Shopee internal API qua Service Worker (credentials: 'include' — dùng cookie).
 * Trả về object sản phẩm { name, price, rating, image_url, ... } hoặc null nếu thất bại.
 */
function fetchShopeeProduct(url) {
    return new Promise((resolve) => {
        const ids = parseShopeeIds(url);
        if (!ids) { resolve(null); return; }

        chrome.runtime.sendMessage(
            { type: 'fetch-shopee-product', shopId: ids.shopId, itemId: ids.itemId },
            (response) => {
                if (chrome.runtime.lastError || !response?.ok || !response?.data?.data?.item) {
                    resolve(null);
                    return;
                }
                const item = response.data.data.item;
                const rawPrice = item.price ?? item.price_min ?? null;
                const price = rawPrice !== null ? (rawPrice / 100000).toLocaleString('vi-VN') + '₫' : null;
                const rating = item.item_rating?.rating_star
                    ? item.item_rating.rating_star.toFixed(1) + '/5'
                    : null;
                resolve({
                    name: item.name || null,
                    price_display: price,
                    rating_display: rating,
                    image_url: item.image ? `https://down-vn.img.susercontent.com/file/${item.image}` : null,
                    brand: item.brand || null,
                    description: (item.description || '').slice(0, 300) || null,
                });
            }
        );
    });
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