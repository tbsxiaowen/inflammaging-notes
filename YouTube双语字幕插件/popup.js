// 弹出窗口逻辑
document.addEventListener('DOMContentLoaded', function() {
    // 获取状态元素
    const pluginStatus = document.getElementById('plugin-status');
    const subtitleStatus = document.getElementById('subtitle-status');
    const translationStatus = document.getElementById('translation-status');
    
    // 获取按钮元素
    const togglePlugin = document.getElementById('toggle-plugin');
    const openSettings = document.getElementById('open-settings');
    
    // 检查当前标签页
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const currentTab = tabs[0];
        
        // 检查是否在YouTube页面
        if (currentTab.url && currentTab.url.includes('youtube.com')) {
            // 在YouTube页面
            pluginStatus.textContent = '已启用';
            pluginStatus.className = 'status-value online';
            
            subtitleStatus.textContent = '运行中';
            subtitleStatus.className = 'status-value online';
            
            translationStatus.textContent = 'Google翻译';
            translationStatus.className = 'status-value online';
            
            togglePlugin.textContent = '禁用插件';
            togglePlugin.className = 'btn btn-primary';
        } else {
            // 不在YouTube页面
            pluginStatus.textContent = '未启用';
            pluginStatus.className = 'status-value offline';
            
            subtitleStatus.textContent = '未运行';
            subtitleStatus.className = 'status-value offline';
            
            translationStatus.textContent = '不可用';
            translationStatus.className = 'status-value offline';
            
            togglePlugin.textContent = '启用插件';
            togglePlugin.className = 'btn btn-secondary';
            togglePlugin.disabled = true;
        }
    });
    
    // 切换插件状态
    togglePlugin.addEventListener('click', function() {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            const currentTab = tabs[0];
            
            if (currentTab.url && currentTab.url.includes('youtube.com')) {
                // 发送消息到content script
                chrome.tabs.sendMessage(currentTab.id, {
                    action: 'togglePlugin'
                }, function(response) {
                    if (response && response.success) {
                        // 更新按钮状态
                        if (togglePlugin.textContent === '禁用插件') {
                            togglePlugin.textContent = '启用插件';
                            togglePlugin.className = 'btn btn-secondary';
                            pluginStatus.textContent = '已禁用';
                            pluginStatus.className = 'status-value offline';
                        } else {
                            togglePlugin.textContent = '禁用插件';
                            togglePlugin.className = 'btn btn-primary';
                            pluginStatus.textContent = '已启用';
                            pluginStatus.className = 'status-value online';
                        }
                    }
                });
            }
        });
    });
    
    // 打开设置
    openSettings.addEventListener('click', function() {
        chrome.runtime.openOptionsPage();
    });
    
    // 监听来自content script的消息
    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
        if (request.action === 'updateStatus') {
            // 更新状态显示
            if (request.subtitleStatus) {
                subtitleStatus.textContent = request.subtitleStatus;
                subtitleStatus.className = request.subtitleStatus === '运行中' ? 
                    'status-value online' : 'status-value offline';
            }
            
            if (request.translationStatus) {
                translationStatus.textContent = request.translationStatus;
                translationStatus.className = request.translationStatus === 'Google翻译' ? 
                    'status-value online' : 'status-value offline';
            }
        }
    });
    
    // 定期检查状态
    setInterval(function() {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            const currentTab = tabs[0];
            
            if (currentTab.url && currentTab.url.includes('youtube.com')) {
                // 发送状态检查消息
                chrome.tabs.sendMessage(currentTab.id, {
                    action: 'getStatus'
                }, function(response) {
                    if (response && response.success) {
                        // 更新状态
                        if (response.subtitleStatus) {
                            subtitleStatus.textContent = response.subtitleStatus;
                            subtitleStatus.className = response.subtitleStatus === '运行中' ? 
                                'status-value online' : 'status-value offline';
                        }
                        
                        if (response.translationStatus) {
                            translationStatus.textContent = response.translationStatus;
                            translationStatus.className = response.translationStatus === 'Google翻译' ? 
                                'status-value online' : 'status-value offline';
                        }
                    }
                });
            }
        });
    }, 5000); // 每5秒检查一次
});
