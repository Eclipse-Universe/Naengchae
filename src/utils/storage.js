// AsyncStorage(휴대폰에 저장되는 간단한 로컬 저장소)를 다루는 함수 모음입니다.
// 다른 파일에서는 AsyncStorage를 직접 쓰지 않고 이 함수들을 통해서만 접근합니다.
// → 키 이름이 바뀌거나 저장 방식이 바뀌어도 이 파일만 수정하면 됩니다.

import AsyncStorage from '@react-native-async-storage/async-storage';

// AsyncStorage에 저장할 때 사용할 키 이름
const USER_PROFILE_KEY = 'userProfile';

// 온보딩에서 입력받은 사용자 프로필을 저장합니다.
// profile 예시: { householdType, memberCount, cookingEnv, foodPreference }
export async function saveUserProfile(profile) {
  const jsonValue = JSON.stringify(profile);
  await AsyncStorage.setItem(USER_PROFILE_KEY, jsonValue);
}

// 저장된 사용자 프로필을 불러옵니다.
// 저장된 값이 없으면 null을 반환합니다. (= 아직 온보딩을 안 한 사용자)
export async function getUserProfile() {
  const jsonValue = await AsyncStorage.getItem(USER_PROFILE_KEY);
  return jsonValue != null ? JSON.parse(jsonValue) : null;
}
