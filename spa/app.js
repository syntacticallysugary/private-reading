// ── Configuration ────────────────────────────────────────────────────────────

// Replace these values with your own deployment endpoints before deploying.
const CONFIG = {
  API_BASE_URL: '<YOUR_OCI_API_GATEWAY_URL>/v1',
  COGNITO_CLIENT_ID: '<READING_CLIENT_ID_FROM_SHARED_AUTH_TERRAFORM>',
  AUTH_DOMAIN: 'https://auth.syntacticallysugary.dev',
  REDIRECT_URI: 'https://reading.syntacticallysugary.dev/',
  MAX_CHARS: 100000,
};

// ── PKCE Utilities ─────────────────────────────────────────────────────────────

function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

async function generateCodeChallenge(verifier) {
  const data = new TextEncoder().encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// ── Auth Logic (OAuth 2.0 Authorization Code + PKCE) ─────────────────────────

async function redirectToLogin() {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  sessionStorage.setItem('pkce_verifier', verifier);

  const params = new URLSearchParams({
    client_id: CONFIG.COGNITO_CLIENT_ID,
    response_type: 'code',
    scope: 'openid email profile',
    redirect_uri: CONFIG.REDIRECT_URI,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });
  window.location.href = `${CONFIG.AUTH_DOMAIN}/oauth2/authorize?${params}`;
}

async function exchangeCodeForTokens(code, verifier) {
  const params = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: CONFIG.COGNITO_CLIENT_ID,
    code,
    redirect_uri: CONFIG.REDIRECT_URI,
    code_verifier: verifier,
  });
  const resp = await fetch(`${CONFIG.AUTH_DOMAIN}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  });
  if (!resp.ok) throw new Error('Token exchange failed');
  return resp.json();
}

async function refreshSession() {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  try {
    const params = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: CONFIG.COGNITO_CLIENT_ID,
      refresh_token: refresh,
    });
    const resp = await fetch(`${CONFIG.AUTH_DOMAIN}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params,
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    localStorage.setItem('id_token', data.id_token);
    localStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
    return true;
  } catch (_) { return false; }
}

function logout() {
  localStorage.removeItem('id_token');
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  const params = new URLSearchParams({
    client_id: CONFIG.COGNITO_CLIENT_ID,
    logout_uri: CONFIG.REDIRECT_URI,
  });
  window.location.href = `${CONFIG.AUTH_DOMAIN}/logout?${params}`;
}

// ── App Logic ────────────────────────────────────────────────────────────────

let _pollTimer = null;

async function initApp() {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');

  if (code) {
    const verifier = sessionStorage.getItem('pkce_verifier');
    sessionStorage.removeItem('pkce_verifier');
    window.history.replaceState({}, '', window.location.pathname);
    try {
      const tokens = await exchangeCodeForTokens(code, verifier);
      localStorage.setItem('id_token', tokens.id_token);
      localStorage.setItem('access_token', tokens.access_token);
      if (tokens.refresh_token) localStorage.setItem('refresh_token', tokens.refresh_token);
    } catch (_) {
      const errEl = document.getElementById('login-error');
      errEl.textContent = 'Authentication failed — please try again.';
      errEl.style.display = '';
      return;
    }
  }

  const token = localStorage.getItem('id_token');
  if (!token) {
    return;
  }

  document.getElementById('login-section').style.display = 'none';
  document.getElementById('app-section').style.display = 'block';
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    document.getElementById('username-display').textContent = payload.email || payload['cognito:username'] || 'User';
  } catch (_) {}
  checkCurrentJob();
}

async function checkCurrentJob() {
  if (!await ensureFreshToken()) return;
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/jobs/current`, {
      headers: getAuthHeader()
    });
    if (resp.status === 200) {
      const job = await resp.json();
      if (job.status === 'failed') return;
      handleJobUpdate(job);
      if (job.status === 'pending' || job.status === 'processing') {
        startPolling();
      }
    }
  } catch (e) {
    console.error('Error checking current job', e);
  }
}

function onTextInput() {
  const n = document.getElementById('text-input').value.length;
  const row = document.getElementById('char-row');
  const el  = document.getElementById('char-count');
  el.textContent = n.toLocaleString() + ' characters';
  row.className = 'char-row' + (n > CONFIG.MAX_CHARS ? ' over' : n > CONFIG.MAX_CHARS * 0.85 ? ' warn' : '');
  document.getElementById('submit-btn').disabled = n === 0 || n > CONFIG.MAX_CHARS;
}

async function submitText() {
  const text = document.getElementById('text-input').value;
  if (!text.trim()) return;
  if (!await ensureFreshToken()) return;

  setLoading(true);
  hide('audio-section');
  hide('error-section');

  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/jobs`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showError(err.error || `Server error (${resp.status})`);
      setLoading(false);
      return;
    }

    const { job_id } = await resp.json();
    showStatus('Queued…', job_id);
    startPolling();
  } catch (e) {
    showError('Network error: ' + e.message);
    setLoading(false);
  }
}

function startPolling() {
  if (_pollTimer) clearInterval(_pollTimer);
  _pollTimer = setInterval(poll, 3000);
}

async function poll() {
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/jobs/current`, {
      headers: getAuthHeader()
    });
    if (!resp.ok) return;
    const job = await resp.json();
    handleJobUpdate(job);
  } catch (_) {}
}

function handleJobUpdate(job) {
  document.getElementById('active-job-id').textContent = job.job_id;

  if (job.status === 'pending') {
    showStatus('Queued…', job.job_id);
    setProgress(0, 0);
  } else if (job.status === 'processing') {
    const done = job.chunks_done || 0;
    const total = job.chunks_total || 0;
    if (total > 0) {
      showStatus('Processing…', job.job_id);
      setProgress(done, total);
    } else {
      showStatus('Processing…', job.job_id);
      setProgress(0, 0);
    }
  } else if (job.status === 'complete') {
    clearInterval(_pollTimer);
    showAudio(job);
  } else if (job.status === 'failed') {
    clearInterval(_pollTimer);
    showError(job.error || 'Processing failed.');
    setLoading(false);
  }
}

function setProgress(done, total) {
  const wrap = document.getElementById('progress-bar-wrap');
  if (total === 0) {
    wrap.style.display = 'none';
    return;
  }
  wrap.style.display = '';
  const pct = Math.round((done / total) * 100);
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-label').textContent = `${done} of ${total} chunks`;
}

async function downloadAudio() {
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/jobs/current/url`, {
      headers: getAuthHeader()
    });
    if (!resp.ok) {
      const err = await resp.json();
      alert('Error getting download URL: ' + (err.error || resp.status));
      return;
    }
    const { url } = await resp.json();
    window.open(url, '_blank');
  } catch (e) {
    alert('Network error while getting download URL');
  }
}

function getAuthHeader() {
  const token = localStorage.getItem('id_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function isTokenExpired() {
  const token = localStorage.getItem('id_token');
  if (!token) return true;
  try {
    const { exp } = JSON.parse(atob(token.split('.')[1]));
    return Date.now() / 1000 > exp - 60;
  } catch (_) { return true; }
}

async function ensureFreshToken() {
  if (isTokenExpired()) {
    const ok = await refreshSession();
    if (!ok) { logout(); return false; }
  }
  return true;
}

function showStatus(msg, jobId) {
  hide('input-section');
  hide('audio-section');
  hide('error-section');
  show('status-section');
  document.getElementById('status-text').textContent = msg;
  if (jobId) document.getElementById('active-job-id').textContent = jobId;
}

function showAudio(job) {
  hide('status-section');
  hide('error-section');
  hide('input-section');
  show('audio-section');
}

function showError(msg) {
  hide('status-section');
  document.getElementById('error-text').textContent = msg;
  show('error-section');
}

function setLoading(yes) {
  document.getElementById('submit-btn').disabled = yes;
}

function resetUI() {
  if (_pollTimer) clearInterval(_pollTimer);
  hide('status-section');
  hide('audio-section');
  hide('error-section');
  show('input-section');
  document.getElementById('text-input').value = '';
  onTextInput();
}

function show(id) { document.getElementById(id).style.display = ''; }
function hide(id) { document.getElementById(id).style.display = 'none'; }

function showTab(name) {
  document.getElementById('tab-convert').style.display = '';
  document.getElementById('tab-convert-btn').classList.add('active');
}

// ── Startup ──────────────────────────────────────────────────────────────────

initApp();
