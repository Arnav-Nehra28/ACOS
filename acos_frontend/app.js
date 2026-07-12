/* ═══════════════════════════════════════════════════════════════
   ACOS — Frontend Application (No Auth)
   Vanilla JS · SSE streaming · Thread management
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const API = window.location.origin;
  const STARTERS = [
    { label: 'Web Research', prompt: 'latest breakthroughs in agentic AI orchestration in the last 7 days' },
    { label: 'Local RAG', prompt: 'local: summarize the uploaded project documents and list the key architecture decisions' },
    { label: 'Knowledge Graph', prompt: 'local: how are FastAPI, Streamlit, ChromaDB, and PostgreSQL connected in this system?' },
    { label: 'Math Agent', prompt: 'calculate the monthly cost if 12,500 requests cost 0.002 dollars each' },
  ];

  const state = {
    threadId: '',
    threads: [],
    messages: [],
    streaming: false,
  };

  const $ = (sel) => document.querySelector(sel);
  const chatMessages = $('#chat-messages');
  const chatInput = $('#chat-input');
  const sendBtn = $('#send-btn');
  const modelSelect = $('#model-select');
  const threadList = $('#thread-list');
  const headerTitle = $('#chat-header-title');
  const toastEl = $('#toast');

  function uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function renderMarkdown(raw) {
    if (typeof marked !== 'undefined') {
      marked.setOptions({ breaks: true, gfm: true });
      return marked.parse(raw || '');
    }
    return escapeHtml(raw || '').replace(/\n/g, '<br>');
  }

  function showToast(msg, duration = 2500) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), duration);
  }

  async function apiFetch(path, opts = {}) {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`${res.status}: ${text}`);
    }
    return res;
  }

  function populateModels() {
    modelSelect.innerHTML = '';
    const models = [
      { label: 'GPT-4o-mini', value: 'gpt-4o-mini' },
      { label: 'Llama 3.3 70B (Groq)', value: 'llama-3.3-70b' },
    ];
    models.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m.value;
      opt.textContent = m.label;
      modelSelect.appendChild(opt);
    });
  }

  async function loadThreads() {
    try {
      const res = await apiFetch('/store/threads?limit=30');
      const data = await res.json();
      state.threads = data.threads || [];
    } catch {
      state.threads = [];
    }
    renderThreadList();
  }

  function renderThreadList() {
    threadList.innerHTML = '';
    if (state.threads.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'thread-empty';
      empty.textContent = 'No conversations yet';
      threadList.appendChild(empty);
      return;
    }
    state.threads.forEach((t) => {
      const item = document.createElement('div');
      item.className = 'thread-item' + (t.thread_id === state.threadId ? ' active' : '');
      const preview = (t.last_message_preview || 'Empty thread').replace(/\n/g, ' ').slice(0, 50);
      const when = (t.last_message_at || '').replace('T', ' ').slice(0, 16);
      item.innerHTML = `
        <div class="thread-preview">${escapeHtml(preview)}</div>
        <div class="thread-meta">${escapeHtml(when)} · ${t.message_count || 0} msgs</div>
      `;
      item.addEventListener('click', () => switchThread(t.thread_id));
      threadList.appendChild(item);
    });
  }

  async function switchThread(threadId) {
    if (state.streaming) return;
    state.threadId = threadId;
    state.messages = [];

    try {
      const res = await apiFetch(`/store/${threadId}?limit=200`);
      const data = await res.json();
      const rows = data.messages || [];
      for (let i = rows.length - 1; i >= 0; i--) {
        const r = rows[i];
        const role = (r.role || '').trim();
        const content = (r.content || '').trim();
        if (!content || !['human', 'ai'].includes(role)) continue;
        state.messages.push({ type: role, content, run_id: r.run_id || null });
      }
    } catch { /* start empty */ }

    renderThreadList();
    renderChat();
  }

  function newChat() {
    if (state.streaming) return;
    state.threadId = uuid();
    state.messages = [];
    renderThreadList();
    renderChat();
  }

  function renderChat() {
    chatMessages.innerHTML = '';

    if (state.messages.length === 0) {
      renderWelcome();
      headerTitle.textContent = 'New Conversation';
      return;
    }

    headerTitle.textContent = state.messages[0].content.slice(0, 45) + (state.messages[0].content.length > 45 ? '…' : '');

    state.messages.forEach((msg, idx) => {
      appendMessageEl(msg, idx === state.messages.length - 1 && msg.type === 'ai');
    });

    scrollToBottom();
  }

  function renderWelcome() {
    const wrap = document.createElement('div');
    wrap.className = 'welcome';
    wrap.innerHTML = `
      <h1>Agent Workspace</h1>
      <p>Route tasks securely across safety, retrieval, web search, math, and knowledge graph agents.</p>
      <div class="starters" id="starter-grid"></div>
    `;
    chatMessages.appendChild(wrap);

    const grid = wrap.querySelector('#starter-grid');
    STARTERS.forEach((s) => {
      const card = document.createElement('div');
      card.className = 'starter';
      card.innerHTML = `
        <div class="starter-label">${escapeHtml(s.label)}</div>
        <div class="starter-text">${escapeHtml(s.prompt)}</div>
      `;
      card.addEventListener('click', () => sendMessage(s.prompt));
      grid.appendChild(card);
    });
  }

  function appendMessageEl(msg, isLatestAi = false) {
    const row = document.createElement('div');
    row.className = 'msg-row';

    const isHuman = msg.type === 'human';
    const avatar = isHuman ? 'ME' : 'A';
    const roleClass = isHuman ? 'human' : 'ai';
    const sender = isHuman ? 'You' : 'ACOS';

    const msgDiv = document.createElement('div');
    msgDiv.className = 'msg';
    msgDiv.innerHTML = `
      <div class="msg-icon ${roleClass}">${avatar}</div>
      <div class="msg-body">
        <div class="msg-sender">${sender}</div>
        <div class="msg-text">${renderMarkdown(msg.content)}</div>
      </div>
    `;
    row.appendChild(msgDiv);

    if (!isHuman && msg.run_id && isLatestAi) {
      const fb = document.createElement('div');
      fb.className = 'msg-fb';
      fb.innerHTML = `
        <button class="fb-btn" data-score="1" title="Good">👍</button>
        <button class="fb-btn" data-score="0" title="Poor">👎</button>
      `;
      fb.querySelectorAll('.fb-btn').forEach((btn) => {
        btn.addEventListener('click', () => sendFeedback(msg.run_id, parseFloat(btn.dataset.score), btn));
      });
      msgDiv.querySelector('.msg-body').appendChild(fb);
    }

    if (!isHuman && msg.content && msg.content.includes('Human approval required before web-answer generation.')) {
      const match = msg.content.match(/Query:\s*(.+?)(?:\s+Recency target:|$)/is);
      if (match) {
        const query = match[1].trim();
        const hitl = document.createElement('div');
        hitl.className = 'hitl-card';
        hitl.innerHTML = `
          <div class="hitl-title">Approval Needed</div>
          <div class="hitl-query">Agent wants to search for: <strong>${escapeHtml(query)}</strong></div>
          <div class="hitl-btns">
            <button class="hitl-btn yes">Approve</button>
            <button class="hitl-btn no">Reject</button>
          </div>
        `;
        hitl.querySelector('.yes').addEventListener('click', () => { hitl.remove(); sendMessage('approve'); });
        hitl.querySelector('.no').addEventListener('click', () => { hitl.remove(); sendMessage('reject'); });
        msgDiv.querySelector('.msg-body').appendChild(hitl);
      }
    }

    chatMessages.appendChild(row);
    return msgDiv;
  }

  function scrollToBottom() {
    requestAnimationFrame(() => { chatMessages.scrollTop = chatMessages.scrollHeight; });
  }

  async function sendMessage(text) {
    if (state.streaming || !text.trim()) return;
    const message = text.trim();

    state.messages.push({ type: 'human', content: message });
    renderChat();
    scrollToBottom();

    state.streaming = true;
    sendBtn.disabled = true;
    chatInput.value = '';
    autoResize();

    const aiMsg = { type: 'ai', content: '', run_id: null };
    state.messages.push(aiMsg);
    
    const aiRow = document.createElement('div');
    aiRow.className = 'msg-row';
    const aiDiv = document.createElement('div');
    aiDiv.className = 'msg';
    aiDiv.innerHTML = `
      <div class="msg-icon ai">A</div>
      <div class="msg-body">
        <div class="msg-sender">ACOS</div>
        <div class="msg-text typing"><div class="dots"><span></span><span></span><span></span></div></div>
      </div>
    `;
    aiRow.appendChild(aiDiv);
    chatMessages.appendChild(aiRow);
    scrollToBottom();

    const contentEl = aiDiv.querySelector('.msg-text');
    let fullContent = '';

    try {
      const response = await fetch(`${API}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          model: modelSelect.value,
          thread_id: state.threadId,
          stream_tokens: true,
        }),
      });

      if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;
          const data = trimmed.slice(6);
          if (data === '[DONE]') continue;

          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'token') {
              fullContent += parsed.content;
              contentEl.innerHTML = renderMarkdown(fullContent);
              contentEl.classList.add('typing');
              scrollToBottom();
            } else if (parsed.type === 'message') {
              const cm = parsed.content;
              if (cm.type === 'ai' && cm.content) {
                fullContent = cm.content;
                if (cm.run_id) aiMsg.run_id = cm.run_id;
              }
            } else if (parsed.type === 'error') {
              fullContent += `\n\n**Error:** ${parsed.content}`;
            }
          } catch { /* skip */ }
        }
      }

      aiMsg.content = fullContent;
      contentEl.classList.remove('typing');
      contentEl.innerHTML = renderMarkdown(fullContent);
      renderChat();

    } catch (err) {
      aiMsg.content = `Error: ${err.message}`;
      contentEl.classList.remove('typing');
      contentEl.innerHTML = `<span style="color:var(--red)">Failed: ${escapeHtml(err.message)}</span>`;
    }

    state.streaming = false;
    sendBtn.disabled = !chatInput.value.trim();
    scrollToBottom();
    loadThreads().catch(() => {});
  }

  async function sendFeedback(runId, score, btnEl) {
    try {
      await apiFetch('/feedback', {
        method: 'POST',
        body: JSON.stringify({ run_id: runId, key: 'human-feedback', score }),
      });
      btnEl.classList.add('on');
      showToast('Feedback recorded');
    } catch {
      showToast('Failed to record');
    }
  }

  function autoResize() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
  }

  function initInput() {
    chatInput.addEventListener('input', () => {
      autoResize();
      sendBtn.disabled = !chatInput.value.trim() || state.streaming;
    });
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (chatInput.value.trim() && !state.streaming) sendMessage(chatInput.value);
      }
    });
    sendBtn.addEventListener('click', () => {
      if (chatInput.value.trim() && !state.streaming) sendMessage(chatInput.value);
    });
  }

  function init() {
    populateModels();
    initInput();
    $('#new-chat-btn').addEventListener('click', newChat);
    
    // Auto-start in new thread
    state.threadId = uuid();
    renderChat();
    loadThreads();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
