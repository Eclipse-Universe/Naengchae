// 모바일 앱이 FastAPI 백엔드(web/main.py)와 통신할 때 쓰는 함수 모음입니다.
// 웹 데모(web/static/index.html)가 호출하는 것과 동일한 /fridge, /profile, /recommend
// API를 그대로 재사용합니다 — 백엔드를 두 번 만들지 않기 위함입니다.
//
// API 주소는 .env의 EXPO_PUBLIC_API_URL에서 가져옵니다. 기기/에뮬레이터마다 백엔드에
// 접속하는 주소가 다르기 때문입니다(iOS 시뮬레이터는 localhost, Android 에뮬레이터는
// 10.0.2.2, 실기기는 PC의 LAN IP). 이 한 줄만 바꾸면 되도록 설정을 코드에서 분리해뒀습니다.
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
  } catch (e) {
    throw new Error(
      `백엔드 서버(${API_BASE_URL})에 연결할 수 없습니다. .env의 EXPO_PUBLIC_API_URL이 ` +
        '이 기기에서 접속 가능한 주소인지 확인하세요.'
    );
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `서버 오류 (${res.status})`);
  }
  if (res.status === 204) {
    return null;
  }
  return res.json();
}

export function getFridge() {
  return request('/fridge');
}

export function addFridgeIngredient(name, expiryDate) {
  return request('/fridge', {
    method: 'POST',
    body: JSON.stringify({ name, expiryDate }),
  });
}

export function deleteFridgeIngredient(id) {
  return request(`/fridge/${id}`, { method: 'DELETE' });
}

export function getProfile() {
  return request('/profile');
}

export function saveProfile(profile) {
  return request('/profile', {
    method: 'POST',
    body: JSON.stringify(profile),
  });
}

export function recommend(today) {
  return request('/recommend', {
    method: 'POST',
    body: JSON.stringify({ today }),
  });
}

// 온보딩은 AsyncStorage(로컬)에 프로필을 저장하지만, 추천 API는 서버 DB의 프로필을 읽는다.
// 둘이 어긋날 수 있는 경우(예: 온보딩 때 네트워크가 끊겨 서버 동기화가 실패한 경우)를 위해,
// 추천을 누르는 시점에 한 번 더 "서버에 프로필이 있는지" 확인하고 없으면 로컬 값으로 채워준다.
export async function ensureProfileSynced(localProfile) {
  const serverProfile = await getProfile();
  if (serverProfile) {
    return serverProfile;
  }
  if (!localProfile) {
    return null;
  }
  return saveProfile(localProfile);
}
