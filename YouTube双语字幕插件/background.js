// YouTube双语字幕插件 - 后台脚本
chrome.runtime.onInstalled.addListener(function() {
    console.log('YouTube双语字幕插件已安装');
    
    // 设置默认配置
    chrome.storage.sync.set({
        enabled: true,
        autoTranslate: true,
        targetLanguage: 'zh',
        sourceLanguage: 'auto',
        showTimestamp: true,
        maxHistory: 100,
        position: { x: 'right', y: 'top' }
    });
});

// 监听来自content script的消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'getStatus') {
        // 获取插件状态
        chrome.storage.sync.get(['enabled'], function(result) {
            sendResponse({
                success: true,
                enabled: result.enabled !== false
            });
        });
        return true; // 保持消息通道开放
    }
    
    if (request.action === 'togglePlugin') {
        // 切换插件状态
        chrome.storage.sync.get(['enabled'], function(result) {
            const newState = !(result.enabled !== false);
            chrome.storage.sync.set({ enabled: newState }, function() {
                sendResponse({
                    success: true,
                    enabled: newState
                });
            });
        });
        return true;
    }
    
    if (request.action === 'updateSettings') {
        // 更新设置
        chrome.storage.sync.set(request.settings, function() {
            sendResponse({ success: true });
        });
        return true;
    }
});

// 监听标签页更新
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
    if (changeInfo.status === 'complete' && tab.url && tab.url.includes('youtube.com')) {
        // 在YouTube页面加载完成后，检查插件状态
        chrome.storage.sync.get(['enabled'], function(result) {
            if (result.enabled !== false) {
                // 插件已启用，注入content script
                chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    files: ['content.js']
                }).catch(function(error) {
                    console.log('Content script注入失败:', error);
                });
            }
        });
    }
});

// 监听标签页激活
chrome.tabs.onActivated.addListener(function(activeInfo) {
    chrome.tabs.get(activeInfo.tabId, function(tab) {
        if (tab.url && tab.url.includes('youtube.com')) {
            // 激活YouTube标签页时，发送状态更新消息
            chrome.tabs.sendMessage(activeInfo.tabId, {
                action: 'tabActivated'
            }).catch(function(error) {
                // 忽略错误（content script可能还没有加载）
            });
        }
    });
});

// 监听扩展图标点击
chrome.action.onClicked.addListener(function(tab) {
    if (tab.url && tab.url.includes('youtube.com')) {
        // 在YouTube页面点击扩展图标时，切换字幕显示
        chrome.tabs.sendMessage(tab.id, {
            action: 'toggleSubtitles'
        }).catch(function(error) {
            console.log('发送消息失败:', error);
        });
    }
});

// 处理键盘快捷键
chrome.commands.onCommand.addListener(function(command) {
    if (command === 'toggle-subtitles') {
        // 获取当前活动标签页
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            const currentTab = tabs[0];
            if (currentTab.url && currentTab.url.includes('youtube.com')) {
                chrome.tabs.sendMessage(currentTab.id, {
                    action: 'toggleSubtitles'
                }).catch(function(error) {
                    console.log('发送消息失败:', error);
                });
            }
        });
    }
});

// 错误处理
chrome.runtime.onSuspend.addListener(function() {
    console.log('YouTube双语字幕插件已暂停');
});

// 定期清理缓存
setInterval(function() {
    chrome.storage.local.get(['translationCache'], function(result) {
        if (result.translationCache) {
            const cache = result.translationCache;
            const now = Date.now();
            const maxAge = 24 * 60 * 60 * 1000; // 24小时
            
            // 清理过期的翻译缓存
            const cleanedCache = {};
            for (const [key, value] of Object.entries(cache)) {
                if (now - value.timestamp < maxAge) {
                    cleanedCache[key] = value;
                }
            }
            
            chrome.storage.local.set({ translationCache: cleanedCache });
        }
    });
}, 60 * 60 * 1000); // 每小时清理一次
