const API_BASE = ''; // same-origin

/** @type {Array<object>} */
let deck = [];
let currentIndex = 0;
let isSwiping = false;

const cardStack = document.getElementById('card-stack');
const emptyState = document.getElementById('empty-state');
const errorMessage = document.getElementById('error-message');
const profileName = document.getElementById('profile-name');
const profileBio = document.getElementById('profile-bio');
const profilePhotos = document.getElementById('profile-photos');
const profileWork = document.getElementById('profile-work');
const profileEducation = document.getElementById('profile-education');
const badgeLinkedin = document.getElementById('badge-linkedin');
const badgeTrustSource = document.getElementById('badge-trust-source');
const btnLike = document.getElementById('btn-like');
const btnPass = document.getElementById('btn-pass');

const verificationPanel = document.getElementById('verification-panel');
const btnToggleVerification = document.getElementById('btn-toggle-verification');
const verificationStatus = document.getElementById('verification-status');
const meBadgeLinkedin = document.getElementById('me-badge-linkedin');
const meBadgeTrustSource = document.getElementById('me-badge-trust-source');
const tabLinkedin = document.getElementById('tab-linkedin');
const tabTrust = document.getElementById('tab-trust');
const panelLinkedin = document.getElementById('panel-linkedin');
const panelTrust = document.getElementById('panel-trust');
const linkedinPhoto = document.getElementById('linkedin-photo');
const linkedinVideo = document.getElementById('linkedin-video');
const trustPhoto = document.getElementById('trust-photo');
const trustVideo = document.getElementById('trust-video');
const linkedinPreview = document.getElementById('linkedin-preview');
const trustPreview = document.getElementById('trust-preview');
const btnSubmitLinkedin = document.getElementById('btn-submit-linkedin');
const btnSubmitTrust = document.getElementById('btn-submit-trust');

/** @type {object | null} */
let currentUser = null;

function setVerificationStatus(message, type) {
  if (!verificationStatus) {
    return;
  }
  verificationStatus.textContent = message;
  verificationStatus.hidden = !message;
  verificationStatus.classList.remove('success', 'error');
  if (type) {
    verificationStatus.classList.add(type);
  }
}

function clearVerificationStatus() {
  setVerificationStatus('', null);
}

function updateMeBadges(profile) {
  if (meBadgeLinkedin) {
    setBadge(meBadgeLinkedin, 'LinkedIn', Boolean(profile.linkedin_verified));
  }
  if (meBadgeTrustSource) {
    setBadge(meBadgeTrustSource, 'Trust Source', Boolean(profile.trust_source_verified));
  }
}

async function fetchMe() {
  const response = await fetch(`${API_BASE}/api/me`);
  if (!response.ok) {
    throw new Error(`Failed to load current user (${response.status})`);
  }
  const profile = await response.json();
  currentUser = profile;
  updateMeBadges(profile);
  return profile;
}

function showVerificationTab(tab) {
  const isLinkedin = tab === 'linkedin';
  tabLinkedin.classList.toggle('active', isLinkedin);
  tabTrust.classList.toggle('active', !isLinkedin);
  tabLinkedin.setAttribute('aria-selected', String(isLinkedin));
  tabTrust.setAttribute('aria-selected', String(!isLinkedin));
  panelLinkedin.hidden = !isLinkedin;
  panelTrust.hidden = isLinkedin;
}

function toggleVerificationPanel() {
  const isHidden = verificationPanel.hidden;
  verificationPanel.hidden = !isHidden;
  if (!isHidden) {
    return;
  }
  clearVerificationStatus();
  fetchMe().catch((err) => {
    setVerificationStatus(err.message || 'Could not load your profile.', 'error');
  });
}

function renderMediaPreview(container, photoInput, videoInput) {
  container.innerHTML = '';
  const files = [];
  if (photoInput?.files?.[0]) {
    files.push(photoInput.files[0]);
  }
  if (videoInput?.files?.[0]) {
    files.push(videoInput.files[0]);
  }

  if (!files.length) {
    container.hidden = true;
    return;
  }

  container.hidden = false;

  for (const file of files) {
    const url = URL.createObjectURL(file);
    if (file.type.startsWith('video/')) {
      const video = document.createElement('video');
      video.src = url;
      video.controls = true;
      video.muted = true;
      container.appendChild(video);
    } else {
      const img = document.createElement('img');
      img.src = url;
      img.alt = 'Upload preview';
      container.appendChild(img);
    }
  }
}

async function uploadVerification(kind) {
  const isLinkedin = kind === 'linkedin';
  const photoInput = isLinkedin ? linkedinPhoto : trustPhoto;
  const videoInput = isLinkedin ? linkedinVideo : trustVideo;
  const submitBtn = isLinkedin ? btnSubmitLinkedin : btnSubmitTrust;

  const formData = new FormData();
  if (photoInput?.files?.[0]) {
    formData.append('photo', photoInput.files[0]);
  }
  if (videoInput?.files?.[0]) {
    formData.append('video', videoInput.files[0]);
  }

  if (!formData.has('photo') && !formData.has('video')) {
    setVerificationStatus('Please select a photo and/or video to upload.', 'error');
    return;
  }

  clearVerificationStatus();
  submitBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/verifications/${kind}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `Upload failed (${response.status})`);
    }

    const label = isLinkedin ? 'LinkedIn' : 'Trust Source';
    setVerificationStatus(`${label} verification submitted successfully.`, 'success');

    photoInput.value = '';
    videoInput.value = '';
    renderMediaPreview(isLinkedin ? linkedinPreview : trustPreview, photoInput, videoInput);

    await fetchMe();
  } catch (err) {
    setVerificationStatus(err.message || 'Upload failed.', 'error');
  } finally {
    submitBtn.disabled = false;
  }
}

function wireVerificationPanel() {
  btnToggleVerification?.addEventListener('click', toggleVerificationPanel);
  tabLinkedin?.addEventListener('click', () => showVerificationTab('linkedin'));
  tabTrust?.addEventListener('click', () => showVerificationTab('trust'));

  linkedinPhoto?.addEventListener('change', () => {
    renderMediaPreview(linkedinPreview, linkedinPhoto, linkedinVideo);
  });
  linkedinVideo?.addEventListener('change', () => {
    renderMediaPreview(linkedinPreview, linkedinPhoto, linkedinVideo);
  });
  trustPhoto?.addEventListener('change', () => {
    renderMediaPreview(trustPreview, trustPhoto, trustVideo);
  });
  trustVideo?.addEventListener('change', () => {
    renderMediaPreview(trustPreview, trustPhoto, trustVideo);
  });

  btnSubmitLinkedin?.addEventListener('click', () => uploadVerification('linkedin'));
  btnSubmitTrust?.addEventListener('click', () => uploadVerification('trust_source'));
}

function showError(message) {
  if (errorMessage) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
  } else {
    alert(message);
  }
}

function clearError() {
  if (errorMessage) {
    errorMessage.textContent = '';
    errorMessage.hidden = true;
  }
}

function formatWorkYears(startYear, endYear) {
  if (endYear == null) {
    return `${startYear}–Present`;
  }
  return `${startYear}–${endYear}`;
}

function formatWorkEntry(entry) {
  const years = formatWorkYears(entry.start_year, entry.end_year);
  return `${entry.title} at ${entry.company} (${years})`;
}

function formatEducationEntry(entry) {
  return `${entry.degree}, ${entry.school} (${entry.year})`;
}

function resolvePhotoUrls(profile) {
  if (Array.isArray(profile.photo_urls) && profile.photo_urls.length > 0) {
    return profile.photo_urls;
  }
  if (Array.isArray(profile.photos)) {
    return profile.photos.map((filename) => `/mock-photos/${filename}`);
  }
  return [];
}

function setBadge(element, label, verified) {
  element.textContent = verified ? `${label}: Verified` : `${label}: Not verified`;
  element.classList.toggle('badge-verified', verified);
  element.classList.toggle('badge-unverified', !verified);
}

function renderListItems(listElement, items, formatter, emptyText) {
  listElement.innerHTML = '';
  if (!items || items.length === 0) {
    const li = document.createElement('li');
    li.className = 'empty-item';
    li.textContent = emptyText;
    listElement.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement('li');
    li.textContent = formatter(item);
    listElement.appendChild(li);
  }
}

function renderPhotos(urls) {
  profilePhotos.innerHTML = '';

  if (!urls.length) {
    const placeholder = document.createElement('div');
    placeholder.className = 'photo-placeholder';
    placeholder.textContent = 'No photos';
    placeholder.style.cssText =
      'display:flex;align-items:center;justify-content:center;height:100%;color:#6b6b76;';
    profilePhotos.appendChild(placeholder);
    return;
  }

  const scroll = document.createElement('div');
  scroll.className = 'photo-scroll';

  for (const url of urls) {
    const img = document.createElement('img');
    img.src = url;
    img.alt = 'Profile photo';
    img.loading = 'lazy';
    scroll.appendChild(img);
  }

  profilePhotos.appendChild(scroll);

  if (urls.length > 1) {
    const dots = document.createElement('div');
    dots.className = 'photo-dots';
    urls.forEach((_, index) => {
      const dot = document.createElement('span');
      dot.className = index === 0 ? 'photo-dot active' : 'photo-dot';
      dots.appendChild(dot);
    });
    profilePhotos.appendChild(dots);

    scroll.addEventListener('scroll', () => {
      const index = Math.round(scroll.scrollLeft / scroll.clientWidth);
      dots.querySelectorAll('.photo-dot').forEach((dot, i) => {
        dot.classList.toggle('active', i === index);
      });
    });
  }
}

function renderProfile(profile) {
  profileName.textContent = profile.name || '—';
  profileBio.textContent = profile.bio || '—';

  renderPhotos(resolvePhotoUrls(profile));

  renderListItems(
    profileWork,
    profile.work_history,
    formatWorkEntry,
    'No work history listed'
  );

  renderListItems(
    profileEducation,
    profile.education_background,
    formatEducationEntry,
    'No education listed'
  );

  setBadge(badgeLinkedin, 'LinkedIn', Boolean(profile.linkedin_verified));
  setBadge(badgeTrustSource, 'Trust Source', Boolean(profile.trust_source_verified));
}

function showEmptyState() {
  cardStack.hidden = true;
  emptyState.hidden = false;
  btnLike.disabled = true;
  btnPass.disabled = true;
}

function showCurrentProfile() {
  if (currentIndex >= deck.length) {
    showEmptyState();
    return;
  }

  cardStack.hidden = false;
  emptyState.hidden = true;
  btnLike.disabled = false;
  btnPass.disabled = false;

  cardStack.classList.remove('swipe-like', 'swipe-pass');
  renderProfile(deck[currentIndex]);
}

async function fetchDeck() {
  const response = await fetch(`${API_BASE}/api/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to load profiles (${response.status})`);
  }
  const data = await response.json();
  return data.profiles || [];
}

function animateSwipe(direction) {
  return new Promise((resolve) => {
    cardStack.classList.remove('swipe-like', 'swipe-pass');
    cardStack.classList.add(direction === 'like' ? 'swipe-like' : 'swipe-pass');
    window.setTimeout(resolve, 250);
  });
}

async function swipe(direction) {
  if (isSwiping || currentIndex >= deck.length) {
    return;
  }

  const profile = deck[currentIndex];
  isSwiping = true;
  btnLike.disabled = true;
  btnPass.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/swipes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile_id: profile.id,
        direction,
      }),
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `Swipe failed (${response.status})`);
    }

    await animateSwipe(direction);
    currentIndex += 1;
    showCurrentProfile();
  } catch (err) {
    showError(err.message || 'Could not record swipe.');
    btnLike.disabled = currentIndex >= deck.length;
    btnPass.disabled = currentIndex >= deck.length;
  } finally {
    isSwiping = false;
  }
}

async function init() {
  btnLike.addEventListener('click', () => swipe('like'));
  btnPass.addEventListener('click', () => swipe('pass'));
  wireVerificationPanel();

  try {
    clearError();
    deck = await fetchDeck();
    currentIndex = 0;

    if (deck.length === 0) {
      showEmptyState();
      return;
    }

    showCurrentProfile();
  } catch (err) {
    showError(err.message || 'Could not load profiles.');
    showEmptyState();
  }
}

document.addEventListener('DOMContentLoaded', init);
