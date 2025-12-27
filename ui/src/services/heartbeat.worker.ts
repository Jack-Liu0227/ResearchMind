
// Web Worker for WebSocket Heartbeat
// 这个 Worker 运行在独立线程中，即使主线程（页面）被挂起或切换到后台，
// Worker 仍然可以继续运行（尽管也会受到浏览器节流影响，但比主线程好很多）。


let heartbeatInterval: any = null;
const INTERVAL = 15000; // 15秒心跳 (配合后端的15秒)


// 监听主线程消息
self.onmessage = (e: MessageEvent) => {
    const { type, interval } = e.data;

    if (type === 'start') {
        if (heartbeatInterval) clearInterval(heartbeatInterval);

        console.log('💓 Worker: Starting heartbeat');

        // 定时发送 tick 消息给主线程，提醒它发送 WebSocket Ping
        heartbeatInterval = setInterval(() => {
            self.postMessage({ type: 'tick' });
        }, interval || INTERVAL);

    } else if (type === 'stop') {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
        console.log('💓 Worker: Stopped heartbeat');
    }
};
