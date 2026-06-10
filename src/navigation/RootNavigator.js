// 앱 전체의 화면 이동(네비게이션)을 관리하는 최상위 컴포넌트입니다.
// 앱이 켜지면 먼저 AsyncStorage에 저장된 사용자 프로필이 있는지 확인해서,
// - 있으면 → 바로 메인 탭(MainTabs)으로
// - 없으면 → 온보딩(Onboarding)부터
// 시작하도록 분기합니다.

import { useEffect, useState } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../constants/colors';
import { getUserProfile } from '../utils/storage';
import OnboardingScreen from '../screens/onboarding/OnboardingScreen';
import MainTabs from './MainTabs';

const Stack = createNativeStackNavigator();

export default function RootNavigator() {
  // 사용자 프로필을 아직 확인 중인지 여부
  const [isLoading, setIsLoading] = useState(true);
  // 온보딩을 이미 완료했는지 여부 (저장된 프로필이 있는지)
  const [hasProfile, setHasProfile] = useState(false);

  // 앱이 처음 켜질 때 한 번만 AsyncStorage를 확인합니다.
  useEffect(() => {
    getUserProfile().then((profile) => {
      setHasProfile(profile !== null);
      setIsLoading(false);
    });
  }, []);

  // 확인이 끝나기 전까지는 로딩 화면을 보여줍니다.
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{ headerShown: false }}
        initialRouteName={hasProfile ? 'MainTabs' : 'Onboarding'}
      >
        <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        <Stack.Screen name="MainTabs" component={MainTabs} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
});
