// YouTube双语字幕插件
class YouTubeBilingualSubtitles {
    constructor() {
        this.subtitleHistory = [];
        this.translationCache = new Map();
        this.lastSubtitleText = '';
        this.mutationObserver = null;
        this.fallbackTimer = null;
        this.captureSubtitleDebounced = null;
        this.init();
    }
    
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        if (!window.location.hostname.includes('youtube.com')) return;
        
        this.createSubtitleContainer();
        this.startSubtitleMonitoring();
        console.log('YouTube双语字幕插件已启动');
    }
    
    createSubtitleContainer() {
        const container = document.createElement('div');
        container.id = 'youtube-bilingual-subtitles';
        container.className = 'youtube-bilingual-subtitles-container';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; width: 400px; max-height: 600px; background: #1a1a1a; border-radius: 8px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.8); z-index: 999999; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden;';
        
        container.innerHTML = `
            <div class="youtube-bilingual-subtitles-header">
                <div class="header-left">
                    <span class="header-title">YouTube双语字幕</span>
                </div>
                <div class="header-right">
                    <button id="minimize-window" class="header-btn" title="最小化">−</button>
                    <button id="toggle-subtitles" class="header-btn" title="显示/隐藏字幕">👁</button>
                    <button id="clear-subtitles" class="header-btn" title="清空字幕">🗑</button>
                    <button id="close-window" class="header-btn" title="关闭">✕</button>
                </div>
            </div>
            <div id="subtitles-content" class="subtitles-content"></div>
        `;
        
        document.body.appendChild(container);
        this.bindEvents();
    }
    
    bindEvents() {
        const subtitleWindow = document.getElementById('youtube-bilingual-subtitles');
        const header = subtitleWindow.querySelector('.youtube-bilingual-subtitles-header');
        
        // 最小化按钮
        const minimizeBtn = document.getElementById('minimize-window');
        minimizeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            subtitleWindow.classList.toggle('minimized');
            minimizeBtn.textContent = subtitleWindow.classList.contains('minimized') ? '□' : '−';
        });
        
        // 显示/隐藏字幕按钮
        const toggleBtn = document.getElementById('toggle-subtitles');
        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const content = document.getElementById('subtitles-content');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        });
        
        // 清空字幕按钮
        const clearBtn = document.getElementById('clear-subtitles');
        clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.clearSubtitles();
        });
        
        // 关闭按钮
        const closeBtn = document.getElementById('close-window');
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            subtitleWindow.style.display = 'none';
        });
        
        // 拖拽功能
        header.addEventListener('mousedown', (e) => {
            // 不拖拽按钮区域
            if (e.target.closest('.header-right')) return;
            
            let isDragging = true;
            let startX = e.clientX - subtitleWindow.offsetLeft;
            let startY = e.clientY - subtitleWindow.offsetTop;
            
            const onMouseMove = (e) => {
                if (!isDragging) return;
                
                const newX = e.clientX - startX;
                const newY = e.clientY - startY;
                
                // 限制在窗口范围内
                const maxX = window.innerWidth - subtitleWindow.offsetWidth;
                const maxY = window.innerHeight - subtitleWindow.offsetHeight;
                
                subtitleWindow.style.left = Math.max(0, Math.min(newX, maxX)) + 'px';
                subtitleWindow.style.top = Math.max(0, Math.min(newY, maxY)) + 'px';
            };
            
            const onMouseUp = () => {
                isDragging = false;
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }
    
    startSubtitleMonitoring() {
        // 基于 MutationObserver 的实时监听 + 去抖
        this.captureSubtitleDebounced = this.debounce(() => this.checkSubtitles(), 150);

        // 观察字幕容器及其子树的变化（不同布局下容器可能不同）
        const observeTargets = [
            document.querySelector('.ytp-caption-window-container'),
            document.querySelector('.ytp-caption-segment'),
            document.body
        ].filter(Boolean);

        try {
            this.mutationObserver = new MutationObserver(() => {
                this.captureSubtitleDebounced();
            });
            observeTargets.forEach(target => {
                this.mutationObserver.observe(target, {
                    childList: true,
                    characterData: true,
                    subtree: true
                });
            });
        } catch (e) {
            // 观察失败则完全依赖后备轮询
            console.warn('字幕DOM观察初始化失败，使用轮询后备:', e);
        }

        // 后备：短周期轮询，防止DOM结构差异导致漏检
        if (this.fallbackTimer) clearInterval(this.fallbackTimer);
        this.fallbackTimer = setInterval(() => this.captureSubtitleDebounced(), 400);
    }
    
    checkSubtitles() {
        const currentText = this.captureCurrentSubtitleText();
        if (currentText && currentText !== this.lastSubtitleText) {
            this.lastSubtitleText = currentText;
            this.processSubtitle(currentText);
        }
    }

    captureCurrentSubtitleText() {
        const subtitleElements = document.querySelectorAll('.ytp-caption-segment');
        let currentText = '';
        subtitleElements.forEach(element => {
            const text = (element.textContent || '').trim();
            if (text) {
                currentText += (currentText ? ' ' : '') + text;
            }
        });
        return currentText;
    }
    
    processSubtitle(text) {
        if (!text || text.length < 2) return;

        // 规范化文本（补标点等）
        const formattedText = this.formatSubtitleText(text);

        // 如果与最近一条英文相同，则忽略（防止高频抖动）
        const lastEntry = this.subtitleHistory[this.subtitleHistory.length - 1];
        if (lastEntry && lastEntry.english === formattedText) return;

        // 立即显示英文，占位中文
        const entry = {
            timestamp: this.getCurrentTimestamp(),
            english: formattedText,
            chinese: '翻译中…',
            id: Date.now()
        };
        this.subtitleHistory.push(entry);
        if (this.subtitleHistory.length > 15) {
            this.subtitleHistory = this.subtitleHistory.slice(-15);
        }
        this.updateSubtitleDisplay();

        // 命中缓存则立刻更新
        const cached = this.translationCache.get(formattedText);
        if (cached) {
            entry.chinese = cached;
            this.updateSubtitleDisplay();
            return;
        }

        // 异步翻译并回填
        this.translateText(formattedText).then(translation => {
            if (translation) {
                this.translationCache.set(formattedText, translation);
                entry.chinese = translation;
                this.updateSubtitleDisplay();
            }
        });
    }

    debounce(fn, delay) {
        let timer = null;
        return (...args) => {
            if (timer) clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }
    
    // 智能添加标点符号
    addPunctuation(text) {
        if (!text || text.length < 3) return text;
        
        let processedText = text.trim();
        
        // 如果已经有标点符号，直接返回
        if (processedText.match(/[.!?]$/)) {
            return processedText;
        }
        
        // 智能检测句子类型
        const lowerText = processedText.toLowerCase();
        
        // 1. 检测疑问句
        if (this.isQuestion(lowerText)) {
            processedText += '?';
        }
        // 2. 检测感叹句
        else if (this.isExclamation(lowerText)) {
            processedText += '!';
        }
        // 3. 检测祈使句
        else if (this.isImperative(lowerText)) {
            processedText += '.';
        }
        // 4. 其他情况添加句号
        else {
            processedText += '.';
        }
        
        return processedText;
    }
    
    // 检测是否为疑问句
    isQuestion(text) {
        // 疑问词开头
        const questionWords = ['what', 'when', 'where', 'who', 'why', 'how', 'which', 'whose', 'whom'];
        if (questionWords.some(word => text.startsWith(word + ' '))) {
            return true;
        }
        
        // 助动词开头
        const auxVerbs = ['do', 'does', 'did', 'is', 'are', 'was', 'were', 'have', 'has', 'had', 'can', 'could', 'will', 'would', 'should', 'may', 'might'];
        if (auxVerbs.some(verb => text.startsWith(verb + ' '))) {
            return true;
        }
        
        // 包含疑问词
        if (text.includes(' what ') || text.includes(' when ') || text.includes(' where ') || 
            text.includes(' who ') || text.includes(' why ') || text.includes(' how ')) {
            return true;
        }
        
        // 反问句模式
        if (text.includes(' right') || text.includes(' isn\'t it') || text.includes(' don\'t you')) {
            return true;
        }
        
        return false;
    }
    
    // 检测是否为感叹句
    isExclamation(text) {
        // 感叹词开头
        const exclamationWords = ['wow', 'amazing', 'incredible', 'fantastic', 'great', 'awesome', 'wonderful', 'terrible', 'horrible', 'oh', 'ah', 'oh my', 'my god'];
        if (exclamationWords.some(word => text.startsWith(word + ' ') || text === word)) {
            return true;
        }
        
        // 包含强烈情感词汇
        const emotionalWords = ['so', 'very', 'really', 'extremely', 'absolutely', 'completely', 'totally', 'amazing', 'incredible'];
        if (emotionalWords.some(word => text.includes(word + ' '))) {
            return true;
        }
        
        // 包含感叹号
        if (text.includes('!')) {
            return true;
        }
        
        // 重复字母表示强调
        if (text.match(/[a-z]{3,}/i) && text.match(/[a-z]{3,}/i)[0].length > 5) {
            return true;
        }
        
        return false;
    }
    
    // 检测是否为祈使句
    isImperative(text) {
        // 祈使句通常以动词开头
        const imperativeVerbs = ['go', 'come', 'stop', 'wait', 'look', 'listen', 'help', 'please', 'let\'s', 'don\'t'];
        if (imperativeVerbs.some(verb => text.startsWith(verb + ' '))) {
            return true;
        }
        
        // 包含祈使句特征
        if (text.includes(' please ') || text.includes(' let\'s ') || text.includes(' don\'t ')) {
            return true;
        }
        
        return false;
    }
    
    // 格式化字幕文本
    formatSubtitleText(text) {
        // 1. 添加标点符号
        let formattedText = this.addPunctuation(text);
        
        // 2. 处理特殊格式
        formattedText = formattedText
            .replace(/\s+/g, ' ')  // 多个空格合并为一个
            .replace(/\s+([,.!?])/g, '$1')  // 移除标点前的空格
            .trim();
        
        return formattedText;
    }
    
    updateSubtitleEntry(english, chinese) {
        const entry = {
            timestamp: this.getCurrentTimestamp(),
            english: english,
            chinese: chinese,
            id: Date.now()
        };
        
        this.subtitleHistory.push(entry);
        
        // 限制历史记录数量
        if (this.subtitleHistory.length > 15) {
            this.subtitleHistory = this.subtitleHistory.slice(-15);
        }
        
        this.updateSubtitleDisplay();
    }
    
    async translateText(text) {
        try {
            const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh&dt=t&q=${encodeURIComponent(text)}`;
            const response = await fetch(url);
            const data = await response.json();
            
            if (data && data[0] && data[0][0]) {
                return data[0][0][0];
            }
            return null;
        } catch (error) {
            console.error('翻译失败:', error);
            return null;
        }
    }
    
    getCurrentTimestamp() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }
    
    updateSubtitleDisplay() {
        const content = document.getElementById('subtitles-content');
        if (!content) return;
        
        // 简单显示所有字幕，不做复杂处理
        content.innerHTML = this.subtitleHistory
            .map(entry => `
                <div class="subtitle-entry">
                    <div class="subtitle-timestamp">${entry.timestamp}</div>
                    <div class="subtitle-english">${entry.english}</div>
                    <div class="subtitle-chinese">${entry.chinese}</div>
                </div>
            `)
            .join('');
        
        // 简单滚动到底部
        content.scrollTop = content.scrollHeight;
    }
    
    clearSubtitles() {
        this.subtitleHistory = [];
        this.updateSubtitleDisplay();
    }
}

// 启动插件
new YouTubeBilingualSubtitles();
