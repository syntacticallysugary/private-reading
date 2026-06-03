// ── Configuration ────────────────────────────────────────────────────────────

// Replace these values with your own deployment endpoints before deploying.
const CONFIG = {
  API_BASE_URL: '<YOUR_OCI_API_GATEWAY_URL>/v1',
  COGNITO_CLIENT_ID: '<YOUR_COGNITO_APP_CLIENT_ID>',
  COGNITO_ENDPOINT: 'https://cognito-idp.<YOUR_AWS_REGION>.amazonaws.com/',
  MAX_CHARS: 100000,
};

// ── Auth Logic (native USER_PASSWORD_AUTH) ────────────────────────────────────

async function login() {
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');
  const btn      = document.getElementById('login-btn');

  errEl.style.display = 'none';
  if (!email || !password) {
    errEl.textContent = 'Please enter your email and password.';
    errEl.style.display = '';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Signing in…';

  try {
    const resp = await fetch(CONFIG.COGNITO_ENDPOINT, {
      method: 'POST',
      headers: {
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        'Content-Type': 'application/x-amz-json-1.1',
      },
      body: JSON.stringify({
        AuthFlow: 'USER_PASSWORD_AUTH',
        ClientId: CONFIG.COGNITO_CLIENT_ID,
        AuthParameters: { USERNAME: email, PASSWORD: password },
      }),
    });

    const data = await resp.json();

    if (!resp.ok || data.__type) {
      const msg = data.message || data.__type || 'Sign-in failed.';
      errEl.textContent = msg;
      errEl.style.display = '';
      return;
    }

    const result = data.AuthenticationResult;
    localStorage.setItem('id_token', result.IdToken);
    localStorage.setItem('access_token', result.AccessToken);
    localStorage.setItem('refresh_token', result.RefreshToken);
    initApp();
  } catch (e) {
    errEl.textContent = 'Network error — please try again.';
    errEl.style.display = '';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
}

async function refreshSession() {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  try {
    const resp = await fetch(CONFIG.COGNITO_ENDPOINT, {
      method: 'POST',
      headers: {
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        'Content-Type': 'application/x-amz-json-1.1',
      },
      body: JSON.stringify({
        AuthFlow: 'REFRESH_TOKEN_AUTH',
        ClientId: CONFIG.COGNITO_CLIENT_ID,
        AuthParameters: { REFRESH_TOKEN: refresh },
      }),
    });
    const data = await resp.json();
    if (!resp.ok || data.__type) return false;
    const result = data.AuthenticationResult;
    localStorage.setItem('id_token', result.IdToken);
    localStorage.setItem('access_token', result.AccessToken);
    return true;
  } catch (_) { return false; }
}

function logout() {
  localStorage.removeItem('id_token');
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.reload();
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

// ── App Logic ────────────────────────────────────────────────────────────────

let _pollTimer = null;

function initApp() {
  // Wire Enter key on password field
  const pwField = document.getElementById('login-password');
  if (pwField) pwField.addEventListener('keydown', e => { if (e.key === 'Enter') login(); });

  const token = localStorage.getItem('id_token');
  if (token) {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('app-section').style.display = 'block';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      document.getElementById('username-display').textContent = payload.email || payload['cognito:username'] || 'User';
    } catch (_) {}
    checkCurrentJob();
  }
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

// ── Tabs ─────────────────────────────────────────────────────────────────────

function showTab(name) {
  document.getElementById('tab-convert').style.display = '';
  document.getElementById('tab-convert-btn').classList.add('active');
}

// ── Startup ──────────────────────────────────────────────────────────────────

initApp();
