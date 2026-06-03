// ── Configuration ────────────────────────────────────────────────────────────

const CONFIG = {
  API_BASE_URL: 'https://o35eybtgc6wg5jujhe5xeixioe.apigateway.us-chicago-1.oci.customer-oci.com/v1',
  COGNITO_CLIENT_ID: '7lkv9uvo8e8f47gepa7fg7rbb9',
  COGNITO_ENDPOINT: 'https://cognito-idp.us-east-1.amazonaws.com/',
  MAX_CHARS: 100000,
  VOICE_SAMPLE_BASE: 'https://objectstorage.us-chicago-1.oraclecloud.com/n/axwer8ojpvgx/b/private-reading-prod-web/o/voice_samples/',
};

const PRESET_VOICES = [
  { id: 'm-relaxed',      label: 'Relaxed Male',       desc: 'Low-key and unhurried' },
  { id: 'f-relaxed',      label: 'Relaxed Female',     desc: 'Low-key and unhurried' },
  { id: 'm-intimate',     label: 'Intimate Male',      desc: 'Warm and personal' },
  { id: 'f-intimate',     label: 'Intimate Female',    desc: 'Warm and personal' },
  { id: 'm-calm',         label: 'Calm Male',          desc: 'Steady and reassuring' },
  { id: 'f-calm',         label: 'Calm Female',        desc: 'Steady and reassuring' },
  { id: 'm-energetic',    label: 'Energetic Male',     desc: 'Dynamic and expressive' },
  { id: 'f-energetic',    label: 'Energetic Female',   desc: 'Dynamic and expressive' },
  { id: 'm-enthusiastic', label: 'Enthusiastic Male',  desc: 'Upbeat and warm' },
  { id: 'f-enthusiastic', label: 'Enthusiastic Female',desc: 'Upbeat and warm' },
];

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
  ['convert', 'voice'].forEach(t => {
    document.getElementById(`tab-${t}`).style.display = t === name ? '' : 'none';
    document.getElementById(`tab-${t}-btn`).classList.toggle('active', t === name);
  });
  if (name === 'voice') { loadVoicePicker(); loadVoiceStatus(); }
}

// ── Voice recording ───────────────────────────────────────────────────────────

const VOICE_TRANSCRIPT = 'The quick brown fox jumps over the lazy dog. She sells seashells by the seashore. I am recording my voice for text-to-speech.';

let _mediaRecorder = null;
let _recordedChunks = [];
let _recordedBlob = null;
let _previewAudio = null;

// ── Preset voice picker ───────────────────────────────────────────────────────

function loadVoicePicker() {
  const grid = document.getElementById('voice-picker-grid');
  const selected = localStorage.getItem('selected_voice_id');
  grid.innerHTML = PRESET_VOICES.map(v => `
    <div class="voice-card${v.id === selected ? ' selected' : ''}" id="vc-${v.id}" onclick="selectVoice('${v.id}')">
      <div class="voice-card-radio"></div>
      <div class="voice-card-info">
        <span class="voice-card-name">${v.label}</span>
        <span class="voice-card-desc">${v.desc}</span>
      </div>
      <button class="btn-preview" id="prev-${v.id}" onclick="previewVoice('${v.id}', event)">&#9654;</button>
    </div>`).join('');
}

function selectVoice(id) {
  const prev = localStorage.getItem('selected_voice_id');
  if (prev) {
    const old = document.getElementById(`vc-${prev}`);
    if (old) old.classList.remove('selected');
  }
  localStorage.setItem('selected_voice_id', id);
  const card = document.getElementById(`vc-${id}`);
  if (card) card.classList.add('selected');
}

function previewVoice(id, event) {
  event.stopPropagation();
  if (_previewAudio) { _previewAudio.pause(); _previewAudio = null; }
  document.querySelectorAll('.btn-preview.playing').forEach(b => b.classList.remove('playing'));
  const btn = document.getElementById(`prev-${id}`);
  const audio = new Audio(`${CONFIG.VOICE_SAMPLE_BASE}${id}.wav`);
  _previewAudio = audio;
  btn.classList.add('playing');
  audio.onended = () => { btn.classList.remove('playing'); _previewAudio = null; };
  audio.onerror = () => { btn.classList.remove('playing'); _previewAudio = null; };
  audio.play().catch(() => btn.classList.remove('playing'));
}

let _voicePollTimer = null;

async function loadVoiceStatus() {
  hide('voice-active-banner');
  hide('voice-pending-banner');
  if (_voicePollTimer) { clearInterval(_voicePollTimer); _voicePollTimer = null; }
  if (!await ensureFreshToken()) return;
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/voice`, { headers: getAuthHeader() });
    if (resp.status === 404) return;
    if (!resp.ok) return;
    const { status } = await resp.json();
    if (status === 'active') {
      show('voice-active-banner');
      hide('voice-record-section');
    } else if (status === 'pending') {
      show('voice-pending-banner');
      _voicePollTimer = setInterval(_pollVoiceStatus, 4000);
    }
  } catch (_) {}
}

async function _pollVoiceStatus() {
  if (!await ensureFreshToken()) return;
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/voice`, { headers: getAuthHeader() });
    if (!resp.ok) return;
    const { status } = await resp.json();
    if (status === 'active') {
      clearInterval(_voicePollTimer);
      _voicePollTimer = null;
      hide('voice-pending-banner');
      show('voice-active-banner');
      hide('voice-record-section');
    }
  } catch (_) {}
}

async function toggleRecording() {
  if (_mediaRecorder && _mediaRecorder.state === 'recording') {
    _mediaRecorder.stop();
    return;
  }
  hide('voice-upload-row');
  hide('voice-error');
  _recordedChunks = [];
  _recordedBlob = null;
  document.getElementById('play-btn').disabled = true;

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    showVoiceError('Microphone access denied. Please allow microphone and try again.');
    return;
  }

  _mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
  _mediaRecorder.ondataavailable = e => { if (e.data.size > 0) _recordedChunks.push(e.data); };
  _mediaRecorder.onstop = () => {
    stream.getTracks().forEach(t => t.stop());
    _recordedBlob = new Blob(_recordedChunks, { type: 'audio/webm;codecs=opus' });
    document.getElementById('mic-btn').textContent = 'Record again';
    document.getElementById('mic-btn').classList.remove('recording');
    hide('recording-indicator');
    document.getElementById('play-btn').disabled = false;
    show('voice-upload-row');
  };
  _mediaRecorder.start();
  document.getElementById('mic-btn').textContent = 'Stop';
  document.getElementById('mic-btn').classList.add('recording');
  show('recording-indicator');
}

function playbackRecording() {
  if (!_recordedBlob) return;
  const btn = document.getElementById('play-btn');
  const url = URL.createObjectURL(_recordedBlob);
  const audio = new Audio(url);
  audio.onended = () => { URL.revokeObjectURL(url); btn.textContent = 'Play back'; };
  btn.textContent = 'Playing…';
  audio.play().catch(err => {
    URL.revokeObjectURL(url);
    btn.textContent = 'Play back';
    showVoiceError('Playback failed: ' + err.message);
  });
}

function discardRecording() {
  _recordedBlob = null;
  _recordedChunks = [];
  document.getElementById('mic-btn').textContent = 'Record';
  document.getElementById('mic-btn').classList.remove('recording');
  document.getElementById('play-btn').disabled = true;
  hide('voice-upload-row');
  hide('recording-indicator');
  document.getElementById('voice-file-input').value = '';
}

function loadAudioFile(input) {
  const file = input.files[0];
  if (!file) return;
  hide('voice-error');
  _recordedBlob = file;
  _recordedChunks = [];
  document.getElementById('play-btn').disabled = false;
  show('voice-upload-row');
}

async function uploadVoice() {
  if (!_recordedBlob) return;
  if (!await ensureFreshToken()) return;
  hide('voice-error');

  const uploadBtn = document.querySelector('#voice-upload-row .btn-primary');
  uploadBtn.disabled = true;
  uploadBtn.textContent = 'Uploading…';

  try {
    const arrayBuf = await _recordedBlob.arrayBuffer();
    const bytes = new Uint8Array(arrayBuf);
    let binary = '';
    bytes.forEach(b => binary += String.fromCharCode(b));
    const audio_b64 = btoa(binary);

    const resp = await fetch(`${CONFIG.API_BASE_URL}/voice`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio_b64, transcript: VOICE_TRANSCRIPT }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showVoiceError(err.error || `Upload failed (${resp.status})`);
      return;
    }

    discardRecording();
    show('voice-pending-banner');
    if (!_voicePollTimer) _voicePollTimer = setInterval(_pollVoiceStatus, 4000);
  } catch (e) {
    showVoiceError('Network error — ' + e.message);
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Use this voice';
  }
}

async function deleteVoice() {
  if (!await ensureFreshToken()) return;
  try {
    await fetch(`${CONFIG.API_BASE_URL}/voice`, { method: 'DELETE', headers: getAuthHeader() });
  } catch (_) {}
  hide('voice-active-banner');
  show('voice-record-section');
  discardRecording();
}

function showVoiceError(msg) {
  const el = document.getElementById('voice-error');
  el.textContent = msg;
  show('voice-error');
}

// ── Startup ──────────────────────────────────────────────────────────────────

initApp();
