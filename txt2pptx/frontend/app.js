/**
 * TXT2PPTX Frontend Application
 */

const API_BASE = '';

// ── UI Elements ──
const $ = (sel) => document.querySelector(sel);

const els = {
    textInput:       () => $('#textInput'),
    numSlides:       () => $('#numSlides'),
    style:           () => $('#style'),
    language:        () => $('#language'),
    apiKey:          () => $('#apiKey'),
    generateBtn:     () => $('#generateBtn'),
    progressSection: () => $('#progressSection'),
    progressTitle:   () => $('#progressTitle'),
    progressDetail:  () => $('#progressDetail'),
    progressFill:    () => $('#progressFill'),
    resultSection:   () => $('#resultSection'),
    resultInfo:      () => $('#resultInfo'),
    downloadBtn:     () => $('#downloadBtn'),
    outlineContent:  () => $('#outlineContent'),
    errorSection:    () => $('#errorSection'),
    errorMessage:    () => $('#errorMessage'),
};

// ── Layout Labels ──
const LAYOUT_LABELS = {
    title_slide:    '封面',
    section_header: '章節',
    bullets:        '條列',
    two_column:     '雙欄',
    image_left:     '左圖',
    image_right:    '右圖',
    key_stats:      '數據',
    comparison:     '對比',
    conclusion:     '結語',
};

// ── State ──
let isGenerating = false;

// ── Main Generate Function ──
async function generatePresentation() {
    const text = els.textInput().value.trim();
    if (!text) {
        els.textInput().focus();
        els.textInput().style.borderColor = '#EF4444';
        setTimeout(() => els.textInput().style.borderColor = '', 2000);
        return;
    }

    if (isGenerating) return;
    isGenerating = true;

    // Prepare request
    const request = {
        text: text,
        num_slides: parseInt(els.numSlides().value),
        style: els.style().value,
        language: els.language().value,
    };

    const apiKey = els.apiKey().value.trim();
    if (apiKey) {
        request.api_key = apiKey;
    }

    // Update UI
    showProgress();
    updateProgress(10, '正在分析文字內容...', 'AI 正在理解您的文字結構');

    try {
        // Simulate progress while waiting
        const progressInterval = simulateProgress();

        // Call API
        const response = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
        });

        clearInterval(progressInterval);

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: '未知錯誤' }));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            updateProgress(100, '生成完成！', '正在準備下載...');
            await sleep(500);
            showResult(data);
        } else {
            throw new Error(data.message || '生成失敗');
        }

    } catch (error) {
        showError(error.message);
    } finally {
        isGenerating = false;
    }
}

// ── Progress Simulation ──
function simulateProgress() {
    let progress = 10;
    const steps = [
        [25, '正在擴充內容...', 'AI 正在根據您的文字生成完整內容'],
        [45, '正在規劃簡報結構...', '分配內容到各個投影片'],
        [65, '正在設計版面佈局...', '選擇最適合的版面配置'],
        [80, '正在生成 PPTX...', '套用設計主題並渲染投影片'],
        [90, '正在最終檢查...', '確認排版與內容完整性'],
    ];
    let stepIdx = 0;

    return setInterval(() => {
        if (stepIdx < steps.length) {
            const [p, title, detail] = steps[stepIdx];
            if (progress < p) {
                progress += 2;
                updateProgress(progress, title, detail);
            } else {
                stepIdx++;
            }
        }
    }, 400);
}

// ── UI State Management ──
function showProgress() {
    els.progressSection().classList.remove('hidden');
    els.resultSection().classList.add('hidden');
    els.errorSection().classList.add('hidden');
    els.generateBtn().disabled = true;
    els.generateBtn().querySelector('.btn-text').textContent = '生成中...';
}

function updateProgress(percent, title, detail) {
    els.progressFill().style.width = `${percent}%`;
    if (title) els.progressTitle().textContent = title;
    if (detail) els.progressDetail().textContent = detail;
}

function showResult(data) {
    els.progressSection().classList.add('hidden');
    els.resultSection().classList.remove('hidden');

    // Download link
    els.downloadBtn().href = `${API_BASE}/api/download/${data.filename}`;
    els.downloadBtn().download = data.filename;

    // Info
    const numSlides = data.outline?.slides?.length || '?';
    els.resultInfo().textContent = `${data.outline?.title || '簡報'} — ${numSlides} 頁投影片`;

    // Outline preview
    renderOutline(data.outline);

    // Reset button
    els.generateBtn().disabled = false;
    els.generateBtn().querySelector('.btn-text').textContent = '生成簡報';
}

function showError(message) {
    els.progressSection().classList.add('hidden');
    els.errorSection().classList.remove('hidden');
    els.errorMessage().textContent = message;
    els.generateBtn().disabled = false;
    els.generateBtn().querySelector('.btn-text').textContent = '生成簡報';
}

function resetForm() {
    els.progressSection().classList.add('hidden');
    els.resultSection().classList.add('hidden');
    els.errorSection().classList.add('hidden');
    els.generateBtn().disabled = false;
    els.generateBtn().querySelector('.btn-text').textContent = '生成簡報';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Render Outline Preview ──
function renderOutline(outline) {
    if (!outline?.slides) return;

    const container = els.outlineContent();
    container.innerHTML = '';

    outline.slides.forEach((slide, idx) => {
        const item = document.createElement('div');
        item.className = 'outline-item';

        const layoutLabel = LAYOUT_LABELS[slide.layout] || slide.layout;

        item.innerHTML = `
            <span class="outline-num">${idx + 1}</span>
            <span class="outline-title">${escapeHtml(slide.title)}</span>
            <span class="outline-layout">${layoutLabel}</span>
        `;

        container.appendChild(item);
    });
}

// ── Utilities ──
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Keyboard shortcut ──
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        generatePresentation();
    }
});
