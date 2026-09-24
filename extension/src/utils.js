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

function extractAnchorText(linkElement) {
    // FR1.2/FR2.2: lấy text hiển thị để detector so sánh với domain đích.
    return linkElement.textContent.trim().substring(0, 100);
}

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

