// 调试脚本 - 在YouTube页面控制台运行
console.log('=== YouTube双语字幕插件调试 ===');

// 检查插件是否加载
if (window.YouTubeBilingualSubtitles) {
    console.log('✅ 插件类已加载');
} else {
    console.log('❌ 插件类未加载');
}

// 检查DOM元素
const container = document.getElementById('youtube-bilingual-subtitles');
if (container) {
    console.log('✅ 插件容器已创建');
    console.log('容器样式:', container.style.cssText);
} else {
    console.log('❌ 插件容器未创建');
}

// 检查字幕元素
const subtitleElements = document.querySelectorAll('.ytp-caption-segment');
console.log('📝 找到字幕元素数量:', subtitleElements.length);

if (subtitleElements.length > 0) {
    subtitleElements.forEach((el, index) => {
        console.log(`字幕 ${index + 1}:`, el.textContent);
    });
}

// 检查YouTube播放器状态
const player = document.querySelector('.html5-video-player');
if (player) {
    console.log('✅ YouTube播放器已找到');
} else {
    console.log('❌ YouTube播放器未找到');
}

// 手动创建插件实例
console.log('🔄 尝试手动创建插件...');
try {
    new YouTubeBilingualSubtitles();
    console.log('✅ 插件实例创建成功');
} catch (error) {
    console.error('❌ 插件实例创建失败:', error);
}

console.log('=== 调试完成 ===');
