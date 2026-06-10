// 앱의 진입점입니다.
// 실제 화면 구성은 src/navigation/RootNavigator.js 에서 관리합니다.

import { StatusBar } from 'expo-status-bar';
import RootNavigator from './src/navigation/RootNavigator';

export default function App() {
  return (
    <>
      <RootNavigator />
      <StatusBar style="auto" />
    </>
  );
}
