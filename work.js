addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // 模拟 env 对象 - 配置你的后端服务
  const env = {
    API_TOKEN: typeof API_TOKEN !== "undefined" ? API_TOKEN : "sk-test",
    // 后端服务地址，支持本项目部署的服务
    BACKEND_URL: typeof BACKEND_URL !== "undefined" ? BACKEND_URL : ""
  };

  // 1. 安全校验
  if (url.pathname.startsWith("/api/")) {
    const origin = request.headers.get("Origin");
    const referer = request.headers.get("Referer");
    const myHost = url.origin;
    const isSafe = (origin && origin === myHost) || (referer && referer.startsWith(myHost));
    if (origin && !isSafe) {
      return new Response(JSON.stringify({ error: "Access Denied" }), { status: 403 });
    }
  }

  // 2. 获取链接 API
  if (url.pathname === "/api/get-link" && request.method === "POST") {
    try {
      const reqBody = await request.json();
      let targetUrl, requestBody, requestHeaders;
      
      // 判断使用哪个后端
      if (env.BACKEND_URL) {
        // 使用本项目部署的后端服务
        targetUrl = `${env.BACKEND_URL}/get-sora-link`;
        requestBody = JSON.stringify({ 
          url: reqBody.url, 
          token: env.API_TOKEN 
        });
        requestHeaders = {
          "Content-Type": "application/json",
          "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        };
      } else {
        // 回退到原始服务
        targetUrl = "https://sy.lmmllm.com/get-sora-link";
        requestBody = JSON.stringify({ 
          url: reqBody.url, 
          token: env.API_TOKEN 
        });
        requestHeaders = {
          "Content-Type": "application/json",
          "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Referer": "https://sy.lmmllm.com"
        };
      }
      
      const targetResponse = await fetch(targetUrl, {
        method: "POST",
        headers: requestHeaders,
        body: requestBody
      });
      
      if (!targetResponse.ok) throw new Error(`API Error: ${targetResponse.status}`);
      const data = await targetResponse.json();
      return new Response(JSON.stringify(data), { 
        headers: { "Content-Type": "application/json" } 
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), { status: 200 });
    }
  }

  // 3. 视频流代理
  if (url.pathname === "/api/proxy-video") {
    const videoUrl = url.searchParams.get("url");
    if (videoUrl) {
      const videoRes = await fetch(videoUrl);
      const newHeaders = new Headers(videoRes.headers);
      newHeaders.set("Access-Control-Allow-Origin", "*");
      return new Response(videoRes.body, { headers: newHeaders });
    }
  }

  // 4. 前端页面
  return new Response(renderHTML(env), {
    headers: { "Content-Type": "text/html;charset=UTF-8" }
  });
}

function renderHTML(env) {
  const backendInfo = env.BACKEND_URL ? `连接: ${env.BACKEND_URL}` : "使用默认服务";
  
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sora 视频去水印批量下载工具 - Sora Studio Pro</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js"></script>
  <style>
    :root {
      --bg-body: #0a0a0c;
      --surface-1: #131316;
      --surface-2: #1c1c21;
      --border-color: #2d2d35;
      --primary: #5c6cff;
      --primary-hover: #4b5be0;
      --text-main: #ededed;
      --text-muted: #858595;
      --success: #2ecc71;
      --error: #e74c3c;
      --font-sans: 'Inter', system-ui, sans-serif;
      --accent-gradient: linear-gradient(90deg, #5c6cff 0%, #8f5cff 100%);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-body);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding-bottom: 120px;
    }
    .backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: radial-gradient(circle at 50% -20%, #1a1f3c 0%, #0a0a0c 60%);
      z-index: -1;
      pointer-events: none;
    }
    .layout {
      width: 100%;
      max-width: 1200px;
      padding: 40px 20px;
      display: flex;
      flex-direction: column;
      gap: 30px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 25px;
    }
    .brand-group h1 {
      font-size: 1.8rem;
      font-weight: 800;
      margin-bottom: 8px;
      letter-spacing: -0.5px;
    }
    .brand-group h1 span {
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .feature-badges {
      display: flex;
      gap: 10px;
      margin-top: 5px;
      flex-wrap: wrap;
    }
    .f-tag {
      font-size: 0.75rem;
      background: rgba(92, 108, 255, 0.1);
      color: #8ea0ff;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid rgba(92, 108, 255, 0.2);
      display: flex;
      align-items: center;
      gap: 4px;
      -webkit-text-fill-color: initial;
      -webkit-background-clip: border-box;
    }
    .f-tag.highlight {
      background: rgba(46, 204, 113, 0.1);
      color: #2ecc71;
      border-color: rgba(46, 204, 113, 0.2);
    }
    .f-tag.backend {
      background: rgba(255, 193, 7, 0.1);
      color: #ffc107;
      border-color: rgba(255, 193, 7, 0.2);
    }
    .github-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border-color);
      padding: 8px 16px;
      border-radius: 20px;
      color: var(--text-main);
      text-decoration: none;
      font-size: 0.9rem;
      transition: 0.3s;
      height: 40px;
    }
    .github-btn:hover {
      background: #fff;
      color: #000;
      transform: translateY(-2px);
    }
    .github-icon {
      width: 20px;
      height: 20px;
      fill: currentColor;
    }
    .textarea-wrapper {
      background: var(--surface-1);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      transition: all 0.2s;
      position: relative;
      overflow: hidden;
    }
    .textarea-wrapper:focus-within {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(92, 108, 255, 0.2);
    }
    .input-label {
      position: absolute;
      top: 15px;
      right: 15px;
      font-size: 0.75rem;
      color: var(--text-muted);
      background: #222;
      padding: 4px 8px;
      border-radius: 4px;
      border: 1px solid #333;
      pointer-events: none;
    }
    textarea {
      width: 100%;
      height: 250px;
      background: transparent;
      border: none;
      color: #fff;
      font-family: 'Menlo', monospace;
      font-size: 14px;
      line-height: 1.6;
      padding: 20px;
      resize: vertical;
      outline: none;
    }
    .controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 15px;
    }
    .hint {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .badge {
      background: #222;
      border: 1px solid #333;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.7rem;
      color: #aaa;
    }
    .btn-start {
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 12px 32px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      transition: 0.2s;
      box-shadow: 0 4px 12px rgba(92, 108, 255, 0.3);
    }
    .btn-start:hover {
      background: var(--primary-hover);
      transform: translateY(-1px);
    }
    .btn-start:disabled {
      opacity: 0.6;
      cursor: wait;
      transform: none;
    }
    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 24px;
      margin-top: 20px;
    }
    .card {
      background: var(--surface-2);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s;
    }
    .card:hover {
      border-color: #444;
    }
    .video-container {
      width: 100%;
      aspect-ratio: 16/9;
      background: #000;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }
    video {
      width: 100%;
      height: 100%;
    }
    .card-meta {
      padding: 15px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid var(--border-color);
      background: var(--surface-1);
    }
    .status-text {
      font-size: 0.75rem;
      color: var(--text-muted);
    }
    .no-wm-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(0,0,0,0.7);
      color: #2ecc71;
      font-size: 0.7rem;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(46, 204, 113, 0.4);
      backdrop-filter: blur(4px);
      pointer-events: none;
    }
    .batch-bar {
      position: fixed;
      bottom: 30px;
      left: 50%;
      transform: translateX(-50%) translateY(120px);
      background: rgba(19, 19, 22, 0.95);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      padding: 12px 25px;
      border-radius: 50px;
      display: flex;
      gap: 15px;
      align-items: center;
      box-shadow: 0 10px 40px rgba(0,0,0,0.6);
      z-index: 100;
      transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .batch-bar.show {
      transform: translateX(-50%) translateY(0);
    }
    .batch-info {
      color: #fff;
      font-size: 0.9rem;
      margin-right: 10px;
      border-right: 1px solid #333;
      padding-right: 20px;
    }
    .btn-action {
      background: transparent;
      color: #ccc;
      border: 1px solid #444;
      padding: 8px 18px;
      border-radius: 20px;
      cursor: pointer;
      font-size: 0.85rem;
      transition: 0.2s;
    }
    .btn-action:hover {
      background: #fff;
      color: #000;
    }
    .btn-zip {
      background: var(--text-main);
      color: #000;
      border: none;
      font-weight: 600;
    }
    .spinner {
      width: 24px;
      height: 24px;
      border: 2px solid rgba(255,255,255,0.1);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s infinite linear;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .footer-credit {
      margin-top: 50px;
      text-align: center;
      font-size: 0.8rem;
      color: #444;
    }
    .footer-credit a {
      color: #666;
      text-decoration: none;
    }
    .footer-credit a:hover {
      color: var(--primary);
    }
  </style>
</head>
<body>
  <div class="backdrop"></div>
  <div class="layout">
    <div class="header">
      <div class="brand-group">
        <h1>Sora Studio <span>Pro</span></h1>
        <div class="feature-badges">
          <span class="f-tag highlight">✨ 自动去水印</span>
          <span class="f-tag">🚀 批量解析</span>
          <span class="f-tag">📦 一键打包</span>
          <span class="f-tag backend">🔗 ${backendInfo}</span>
        </div>
      </div>
      <a href="https://github.com/genz27" target="_blank" class="github-btn">
        <svg class="github-icon" viewBox="0 0 24 24">
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
        <span>genz27</span>
      </a>
    </div>

    <div class="input-section">
      <div class="textarea-wrapper">
        <div class="input-label">Watermark Remover</div>
        <textarea id="urlInput" placeholder="在此粘贴视频链接 (自动去除水印 / 支持批量)
----------------------------------------
https://sora.chatgpt.com/p/s_example-1...
https://sora.chatgpt.com/p/s_example-2..."></textarea>
      </div>
      <div class="controls">
        <div class="hint" id="quotaHint">
          <span class="badge">TIP</span>
          <span>支持 sora.chatgpt.com 分享链接</span>
        </div>
        <button class="btn-start" id="processBtn" onclick="runBatch()">✨ 开始去水印解析</button>
      </div>
    </div>

    <div class="gallery" id="gallery"></div>

    <div class="footer-credit">
      Designed & Developed by <a href="https://github.com/genz27" target="_blank">@genz27</a>
      · Powered by Sora2API
    </div>
  </div>

  <div class="batch-bar" id="batchBar">
    <div class="batch-info" id="batchInfo">已就绪 0 个视频</div>
    <button class="btn-action" onclick="copyAllLinks()">📋 复制无水印链接</button>
    <button class="btn-action btn-zip" id="zipBtn" onclick="downloadAllZip()">📦 打包下载 (ZIP)</button>
  </div>

  <script>
    const urlInput = document.getElementById('urlInput');
    const gallery = document.getElementById('gallery');
    const processBtn = document.getElementById('processBtn');
    const batchBar = document.getElementById('batchBar');
    const batchInfo = document.getElementById('batchInfo');
    const zipBtn = document.getElementById('zipBtn');
    const quotaHint = document.getElementById('quotaHint');
    
    let successList = [];

    async function runBatch() {
      const t = urlInput.value;
      const urls = t.split(/[\\n]+/).map(u => u.trim()).filter(u => u.length > 0);
      
      if (urls.length === 0) return alert("请先粘贴链接");
      
      processBtn.disabled = true;
      processBtn.innerText = \`正在去除水印 \${urls.length} 个任务...\`;
      
      for (const u of urls) {
        const id = 'task-' + Math.random().toString(36).substr(2, 9);
        createCard(id, u);
        processUrl(u, id);
      }
      
      urlInput.value = '';
      setTimeout(() => {
        processBtn.disabled = false;
        processBtn.innerText = "✨ 开始去水印解析";
      }, 500);
    }

    function createCard(id, url) {
      const d = document.createElement('div');
      d.className = 'card';
      d.id = id;
      d.innerHTML = \`
        <div class="video-container">
          <div class="spinner"></div>
        </div>
        <div class="card-meta">
          <span class="status-text" style="max-width:200px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">\${url}</span>
          <span class="status-text">去水印中...</span>
        </div>
      \`;
      gallery.insertBefore(d, gallery.firstChild);
    }

    async function processUrl(url, id) {
      const c = document.getElementById(id);
      try {
        const r = await fetch('/api/get-link', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        
        if (r.status === 403) throw new Error("非法请求拒绝访问");
        
        const d = await r.json();
        
        if (d.download_link) {
          renderSuccess(c, d.download_link);
          successList.push({ originalUrl: url, downloadLink: d.download_link });
          updateBatchBar();
        } else {
          throw new Error(d.error || "无效链接");
        }
      } catch (e) {
        renderError(c, e.message);
      }
    }

    function renderSuccess(c, l) {
      c.innerHTML = \`
        <div class="video-container">
          <div class="no-wm-badge">✨ No Watermark</div>
          <video controls preload="metadata" playsinline>
            <source src="\${l}" type="video/mp4">
          </video>
        </div>
        <div class="card-meta">
          <span class="status-text" style="color:var(--success)">● 完成</span>
          <a href="\${l}" target="_blank" style="color:#fff;text-decoration:none;font-size:0.8rem;border:1px solid #444;padding:4px 8px;border-radius:4px;">下载</a>
        </div>
      \`;
    }

    function renderError(c, m) {
      c.querySelector('.video-container').innerHTML = \`<span style="color:var(--error);font-size:0.8rem;">❌ \${m}</span>\`;
      c.querySelector('.card-meta span:last-child').innerText = "失败";
    }

    function updateBatchBar() {
      if (successList.length > 0) {
        batchBar.classList.add('show');
        batchInfo.innerText = \`已就绪 \${successList.length} 个视频\`;
      }
    }

    function copyAllLinks() {
      const l = successList.map(i => i.downloadLink).join('\\n');
      navigator.clipboard.writeText(l).then(() => {
        const b = document.querySelector('.btn-action');
        const o = b.innerText;
        b.innerText = "✅ 已复制";
        setTimeout(() => b.innerText = o, 2000);
      });
    }

    async function downloadAllZip() {
      if (successList.length === 0) return;
      
      zipBtn.disabled = true;
      const o = zipBtn.innerText;
      const z = new JSZip();
      
      try {
        for (let i = 0; i < successList.length; i++) {
          const it = successList[i];
          zipBtn.innerText = \`下载中 \${i + 1}/\${successList.length}\`;
          try {
            const p = '/api/proxy-video?url=' + encodeURIComponent(it.downloadLink);
            const r = await fetch(p);
            if (!r.ok) throw new Error('Net Error');
            const b = await r.blob();
            z.file(\`Sora_NoWM_\${i + 1}_\${Date.now()}.mp4\`, b);
          } catch (e) {
            console.error('Download error:', e);
          }
        }
        
        zipBtn.innerText = "压缩中...";
        const c = await z.generateAsync({ type: "blob" });
        saveAs(c, "Sora_NoWM_Batch.zip");
        zipBtn.innerText = "✅ 完成";
        
        setTimeout(() => {
          zipBtn.disabled = false;
          zipBtn.innerText = o;
        }, 3000);
      } catch (e) {
        alert("打包出错");
        zipBtn.disabled = false;
        zipBtn.innerText = o;
      }
    }
  </script>
</body>
</html>`;
}
