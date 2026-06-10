// 탭 3: 리포트 화면입니다.
// 지금은 자리만 잡아둔 placeholder이고,
// 다음 작업에서 냉파율, 절약 금액, 소비 패턴 요약을 채울 예정입니다.

import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../constants/colors';

export default function ReportScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>리포트</Text>
      <Text style={styles.subtitle}>
        이번 주 냉파율, 절약 금액 등이{'\n'}여기에 표시될 예정이에요{'\n'}(다음 작업에서 구현)
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textLight,
    textAlign: 'center',
    lineHeight: 22,
  },
});
