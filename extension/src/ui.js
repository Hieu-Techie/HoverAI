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

popup = document.getElementById('hoverai-popup');
statusIcon = document.getElementById('hai-status-icon');
statusText = document.getElementById('hai-status-text');
summaryBox = document.getElementById('hai-summary');
contentStatus = document.getElementById('hai-content-status');
deepScanBtn = document.getElementById('hai-deepscan-btn');
historyBtn = document.getElementById('hai-history-btn');
chatHistory = document.getElementById('hai-chat-history');
chatInput = document.getElementById('hai-chat-input');
sendBtn = document.getElementById('hai-send-btn');



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

function showContentResult(result) {
    // FR3.1/FR3.2/FR3.3: hiển thị kết quả tùy theo loại nội dung.
    contentStatus.className = 'content-status content-success';
    if (result.content_type === 'product') {
        showProductResult(result);
    } else if (result.content_type === 'video') {
        showVideoResult(result);
    } else {
        showArticleResult(result);
    }
}

function showArticleResult(result) {
    // FR3.1: hiển thị tiêu đề, tên site và summary bài viết.
    const siteName = getSiteName(result.url || currentLinkData?.href || '', result.metadata?.site_name || null);
    const title = result.title || `Nội dung từ ${siteName}`;
    contentStatus.textContent = result.summary
        ? `${title}\n\nTóm tắt:\n${result.summary}`
        : `${title}\n\nChưa có bản tóm tắt. Hãy cấu hình GEMINI_API_KEY để bật tính năng này.`;
}

/**
 * Chuyển hostname thành tên trang web thân thiện với người dùng.
 * Dùng site_name từ backend nếu có, fallback về mapping tên miền phổ biến.
 */
function getSiteName(url, backendSiteName) {
    if (backendSiteName) return backendSiteName;
    try {
        const hostname = new URL(url).hostname.replace(/^www\./, '');
        const KNOWN_SITES = {
            'shopee.vn': 'Shopee', 'shopee.com': 'Shopee',
            'lazada.vn': 'Lazada', 'lazada.com': 'Lazada',
            'tiki.vn': 'Tiki', 'sendo.vn': 'Sendo',
            'facebook.com': 'Facebook', 'fb.com': 'Facebook',
            'instagram.com': 'Instagram',
            'twitter.com': 'X (Twitter)', 'x.com': 'X (Twitter)',
            'linkedin.com': 'LinkedIn',
            'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
            'tiktok.com': 'TikTok',
            'wikipedia.org': 'Wikipedia',
            'vnexpress.net': 'VnExpress', 'dantri.com.vn': 'Dân Trí',
            'tuoitre.vn': 'Tuổi Trẻ', 'thanhnien.vn': 'Thanh Niên',
            'nhandan.vn': 'Nhân Dân', 'baomoi.com': 'Báo Mới',
            'amazon.com': 'Amazon', 'ebay.com': 'eBay',
            'google.com': 'Google', 'github.com': 'GitHub',
            'express.com.vn': 'Express', 'thegioididong.com': 'Thế Giới Di Động',
            'cellphones.com.vn': 'CellphoneS', 'fptshop.com.vn': 'FPT Shop',
        };
        if (KNOWN_SITES[hostname]) return KNOWN_SITES[hostname];
        // Fallback: viết hoa chữ cái đầu của tên miền
        const name = hostname.split('.')[0];
        return name.charAt(0).toUpperCase() + name.slice(1);
    } catch {
        return 'trang này';
    }
}

function showProductResult(result) {
    // FR3.2: hiển thị thông tin sản phẩm dạng card có cấu trúc.
    const meta = result.metadata || {};
    const name = result.title || 'Sản phẩm';
    const price = meta.price_display || meta.price || null;
    const rating = meta.rating_display || meta.rating || null;
    const brand = meta.brand || null;
    const note = meta.extraction_note || result.extraction_note || null;
    const siteName = getSiteName(result.url || currentLinkData?.href || '', meta.site_name);

    let lines = [`🛒 ${name}`];
    if (brand) lines.push(`Thương hiệu: ${brand}`);
    if (price) lines.push(`Giá: ${price}`);
    if (rating) lines.push(`Đánh giá: ${rating}`);

    if (note === 'SHOPEE_API') {
        // Dữ liệu thực từ Shopee API — không cần cảnh báo
    } else if (note === 'SPA_PARTIAL') {
        lines.push(`\n🔐 ${siteName} yêu cầu đăng nhập để xem nội dung.\nHãy mở trang và đăng nhập, sau đó nhấn icon HoverAI để phân tích đầy đủ.`);
    } else if (note === 'JINA_PARTIAL') {
        lines.push(`\nℹ️ Giá và đánh giá chưa lấy được từ ${siteName}.\nMở trang và nhấn icon HoverAI để xem đầy đủ.`);
    } else if (note === 'PRICE_NOT_AVAILABLE') {
        lines.push(`\nℹ️ Giá sản phẩm trên ${siteName} cần mở trang để xem chính xác.`);
    }

    if (result.summary) {
        lines.push(`\nPhân tích AI:\n${result.summary}`);
    } else if (note !== 'SPA_PARTIAL') {
        lines.push('\nChưa có phân tích AI. Hãy cấu hình GEMINI_API_KEY để bật tính năng này.');
    }
    contentStatus.textContent = lines.join('\n');
}

function showContentError(error, securityResult = null) {
    // FR3.1/FR3.2: báo rõ lỗi trích xuất sau khi kết quả bảo mật đã được hiển thị.
    const reason = error.message || 'CONTENT_EXTRACTION_FAILED';
    contentStatus.className = 'content-status content-error';
    const siteName = getSiteName(currentLinkData?.href || '', null);

    if (reason === 'REQUEST_TIMEOUT') {
        contentStatus.textContent = `${siteName} phản hồi quá chậm (>35s).\nBạn có thể mở trang rồi nhấn icon HoverAI để phân tích trực tiếp.`;
        return;
    }

    if (reason.startsWith('PRODUCT_FETCH_FAILED')) {
        contentStatus.textContent = `${siteName} cần mở trang mới có thể xem thông tin sản phẩm.\nHãy nhấn vào link, sau đó nhấn icon HoverAI trên thanh công cụ.`;
        return;
    }

    const messages = {
        SOURCE_BOT_CHALLENGE: `${siteName} đang chặn truy cập tự động (Cloudflare/CAPTCHA).\nHãy mở trang trực tiếp rồi dùng icon HoverAI.`,
        SOURCE_CONTENT_EMPTY: `${siteName} yêu cầu đăng nhập hoặc cần JavaScript để tải nội dung.\nHãy mở trang, đăng nhập (nếu cần), rồi nhấn icon HoverAI.`,
        CONTENT_NOT_FOUND: `Không tìm thấy nội dung phù hợp trên ${siteName}.`,
        CONTENT_TYPE_VIDEO_UNSUPPORTED: `Đây là link video trên ${siteName}. Tính năng xử lý video sẽ ra mắt ở phiên bản tiếp theo.`,
        SOURCE_TIMEOUT: `${siteName} phản hồi quá chậm (>10s). Thử lại hoặc mở trang trực tiếp.`,
        SOURCE_UNAVAILABLE: `Không thể kết nối tới ${siteName}. Kiểm tra kết nối mạng hoặc thử lại sau.`,
        CONTENT_TIMEOUT: `Xử lý nội dung từ ${siteName} mất quá nhiều thời gian. Thử lại sau.`,
    };

    contentStatus.textContent = messages[reason] || `Không thể lấy nội dung từ ${siteName}: ${reason}`;

    const linkIsSafe = securityResult?.safety?.safe === true
        && securityResult?.phishing?.is_phishing === false;
    if (linkIsSafe && reason !== 'SOURCE_BOT_CHALLENGE') {
        contentStatus.textContent += `\n✅ Link đã xác minh an toàn. Mở trang ${siteName} rồi nhấn icon HoverAI để phân tích đầy đủ.`;
    }
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

function showVideoResult(result) {
    // FR3.3/FR3.4/FR3.5: hiển thị thông tin video từ mọi nền tảng, kèm cảnh báo clickbait nếu là dự đoán.
    const meta = result.metadata || {};
    const platform = meta.platform || 'Video';
    const title = result.title || `Video ${platform}`;
    const channel = meta.channel || null;
    const note = meta.extraction_note || null;
    const lang = meta.transcript_language || null;
    const isAuto = meta.is_auto_generated;
    // FR3.4: flag từ backend, true khi tóm tắt không dựa trên transcript thực
    const isPrediction = meta.is_prediction === true;

    // FR3.5: lưu URL video hiện tại để Deep Scan button dùng
    currentVideoUrl = result.url || null;

    let lines = [`🎬 ${title}`];
    if (channel) lines.push(`Kênh: ${channel}`);
    if (platform && platform !== 'Video') lines.push(`Nền tảng: ${platform}`);

    // Trạng thái transcript / nguồn nội dung
    if (note === 'TRANSCRIPT_DISABLED') {
        lines.push('\n⚠️ Video đã tắt phụ đề. Không thể lấy transcript.');
    } else if (note === 'TRANSCRIPT_NOT_FOUND') {
        lines.push('\n⚠️ Video không có phụ đề/transcript.');
    } else if (note === 'TRANSCRIPT_ERROR') {
        lines.push('\n⚠️ Lỗi khi lấy transcript. Hãy thử lại sau.');
    } else if (note === 'TRANSCRIPT_NOT_AVAILABLE') {
        lines.push('\nℹ️ Nền tảng này không hỗ trợ lấy transcript trực tiếp.');
    } else if (lang) {
        // YouTube với transcript thành công
        const langDisplay = lang.startsWith('vi') ? 'Tiếng Việt'
            : lang.startsWith('en') ? 'Tiếng Anh' : lang;
        const autoLabel = isAuto ? ' (tự động)' : '';
        lines.push(`Phụ đề: ${langDisplay}${autoLabel}`);
    }

    if (result.summary) {
        if (isPrediction) {
            // FR3.4: cảnh báo khi tóm tắt là dự đoán
            if (note === 'TRANSCRIPT_NOT_AVAILABLE' && result.text) {
                // Có description → tóm tắt từ mô tả (tạm ổn)
                lines.push('\n📋 Phân tích AI (từ mô tả video):');
                lines.push('(Dựa trên mô tả, không phải nội dung thực — có thể không đầy đủ)');
            } else {
                // Chỉ có tiêu đề → dự đoán, nguy cơ clickbait cao
                lines.push('\n⚠️ Phân tích AI (dự đoán từ tiêu đề):');
                lines.push('(Có thể chứa yếu tố giật gân — chỉ mang tính tham khảo)');
            }
        } else {
            lines.push('\nPhân tích AI:');
        }
        lines.push(result.summary);

        // FR3.4: gợi ý Deep Scan khi chưa có transcript
        if (isPrediction) {
            lines.push('\n🔍 Để phân tích chính xác hơn: hãy mở video, chờ tải xong rồi nhấn icon HoverAI.');
        }
    } else {
        // Không có summary
        const noTranscriptNoData = note === 'TRANSCRIPT_DISABLED' || note === 'TRANSCRIPT_NOT_FOUND';
        if (noTranscriptNoData) {
            lines.push('\nKhông thể tóm tắt AI vì video không có phụ đề.');
            lines.push('🔍 Gợi ý: Mở video và nhấn icon HoverAI để thử phân tích bằng âm thanh (Deep Scan).');
        } else {
            lines.push('\nChưa có phân tích AI. Hãy cấu hình GEMINI_API_KEY để bật tính năng này.');
        }
    }

    contentStatus.textContent = lines.join('\n');

    // FR3.5: hiển thị nút Deep Scan CHỈ khi không lấy được transcript thực
    // (tóm tắt là dự đoán hoặc không có phụ đề → Deep Scan có giá trị)
    const noRealTranscript = isPrediction
        || note === 'TRANSCRIPT_DISABLED'
        || note === 'TRANSCRIPT_NOT_FOUND'
        || note === 'TRANSCRIPT_ERROR'
        || note === 'TRANSCRIPT_NOT_AVAILABLE';

    if (currentVideoUrl && noRealTranscript) {
        deepScanBtn.style.display = 'block';
        deepScanBtn.disabled = false;
        deepScanBtn.textContent = '🔍 Deep Scan (Quét âm thanh nâng cao)';
    } else {
        deepScanBtn.style.display = 'none';
    }
}

function showCurrentPageResult(result) {
    // FR3.1/FR3.2/FR3.3/FR3.5: kết thúc luồng phân tích trang hiện tại và xóa trạng thái đang tải.
    const isProduct = result.content_type === 'product';
    const isVideo = result.content_type === 'video';
    statusIcon.textContent = isProduct ? '🛒' : isVideo ? '🎬' : '✅';
    statusText.textContent = isProduct
        ? 'Đã phân tích trang sản phẩm'
        : isVideo
            ? 'Đã phân tích video'
            : 'Đã phân tích trang hiện tại';
    statusText.className = 'status-safe';
    summaryBox.textContent = isProduct
        ? 'Đã lấy thông tin sản phẩm từ trang đang mở.'
        : isVideo
            ? 'Đã lấy thông tin video từ trang đang mở.'
            : 'Đã lấy nội dung trang đang mở.';

    // FR3.5: khi phân tích trang video hiện tại, dùng URL trang làm target Deep Scan
    if (isVideo) {
        currentVideoUrl = window.location.href;
    }

    showContentResult(result);
}

function showDeepScanResult(result) {
    const title = result.title_vi || result.title || 'Video';
    const lines = [];

    lines.push(`🎙️ Deep Scan: ${title}`);
    if (result.channel) lines.push(`Kênh: ${result.channel}`);
    if (result.duration) {
        const m = Math.floor(result.duration / 60);
        const s = result.duration % 60;
        lines.push(`Thời lượng: ${m}:${String(s).padStart(2, '0')}`);
    }

    if (result.summary) {
        lines.push(`\nTóm tắt:\n${result.summary}`);
    }

    if (result.key_points) {
        lines.push(`\nCác điểm chính (có mốc thời gian):\n${result.key_points}`);
    }

    if (!result.summary && !result.key_points) {
        lines.push('\nKhông có dữ liệu từ Gemini. Hãy thử lại.');
    }

    contentStatus.className = 'content-status content-success';
    contentStatus.textContent = lines.join('\n');

    // Ẩn nút sau khi xong
    deepScanBtn.style.display = 'none';
    deepScanBtn.disabled = false;
    deepScanBtn.textContent = '🔍 Deep Scan (Quét âm thanh nâng cao)';
}

