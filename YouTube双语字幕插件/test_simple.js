// 简化测试版本
console.log('=== 开始加载简化版插件 ===');

// 等待页面加载完成
function waitForPageLoad() {
    if (document.readyState === 'complete') {
        initSimplePlugin();
    } else {
        window.addEventListener('load', initSimplePlugin);
    }
}

function initSimplePlugin() {
    console.log('页面加载完成，开始初始化插件...');
    
    // 检查是否在YouTube页面
    if (!window.location.hostname.includes('youtube.com')) {
        console.log('不在YouTube页面，退出');
        return;
    }
    
    // 创建简单的字幕容器
    const container = document.createElement('div');
    container.id = 'simple-subtitles';
    container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        width: 300px;
        height: 200px;
        background: #1a1a1a;
        color: white;
        border-radius: 8px;
        padding: 16px;
        z-index: 999999;
        font-family: Arial, sans-serif;
    `;
    
    container.innerHTML = `
        <div style="background: #ff0000; padding: 8px; margin: -16px -16px 16px -16px; border-radius: 8px 8px 0 0;">
            <strong>简化版字幕插件</strong>
            <button onclick="this.parentElement.parentElement.remove()" style="float: right; background: none; border: none; color: white; cursor: pointer;">✕</button>
        </div>
        <div id="subtitle-content">等待字幕...</div>
    `;
    
    document.body.appendChild(container);
    console.log('✅ 简化版插件容器已创建');
    
    // 开始检查字幕
    startSimpleMonitoring();
}

function startSimpleMonitoring() {
    console.log('开始监控字幕...');
    
    setInterval(() => {
        const subtitleElements = document.querySelectorAll('.ytp-caption-segment');
        const content = document.getElementById('subtitle-content');
        
        if (subtitleElements.length > 0 && content) {
            let text = '';
            subtitleElements.forEach(el => {
                text += el.textContent + ' ';
            });
            
            if (text.trim()) {
                content.innerHTML = `
                    <div style="margin-bottom: 10px;">
                        <strong>英文:</strong> ${text.trim()}
                    </div>
                    <div style="color: #ccc;">
                        <strong>中文:</strong> 翻译中...
                    </div>
                `;
                console.log('📝 检测到字幕:', text.trim());
            }
        }
    }, 1000);
}

// 启动
waitForPageLoad();
console.log('=== 简化版插件加载完成 ===');
