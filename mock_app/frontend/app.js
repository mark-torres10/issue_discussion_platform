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
