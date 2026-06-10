// 탭 2: 오늘 뭐 먹지? (레시피 추천) 화면입니다.
// 지금은 자리만 잡아둔 placeholder이고,
// 다음 작업에서 하드코딩 레시피 10개 기반 추천 카드를 채울 예정입니다.

import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../constants/colors';

export default function RecipeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>오늘 뭐 먹지?</Text>
      <Text style={styles.subtitle}>
        보유 재료 기반 추천 레시피 카드가{'\n'}여기에 표시될 예정이에요{'\n'}(다음 작업에서 구현)
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
