// 온보딩 Step 2: 조리 환경을 선택하는 화면입니다.
// "전자레인지만 있어요" / "가스레인지 1구" / "풀옵션" 중 하나를 고릅니다.
// (Step1의 카드 선택 UI와 같은 패턴을 사용합니다)

import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../../constants/colors';

// 화면에 보여줄 조리 환경 옵션 목록
// value: 데이터로 저장될 값, emoji/title/description: 화면 표시용
const COOKING_ENV_OPTIONS = [
  {
    value: 'microwave',
    emoji: '⚡️',
    title: '전자레인지만 있어요',
    description: '전자레인지 위주 조리',
  },
  {
    value: 'oneburner',
    emoji: '🔥',
    title: '가스레인지 1구',
    description: '간단한 화구 요리 가능',
  },
  {
    value: 'full',
    emoji: '🍳',
    title: '풀옵션',
    description: '오븐, 에어프라이어 등 다양한 조리 가능',
  },
];

// 부모(OnboardingScreen)로부터 현재 선택값(cookingEnv)과
// 선택이 바뀌었을 때 호출할 함수(onSelectCookingEnv)를 props로 받습니다.
export default function StepCookingEnv({ cookingEnv, onSelectCookingEnv }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>어떤 환경에서 요리하시나요?</Text>
      <Text style={styles.subtitle}>
        보유한 조리 도구에 맞는 레시피만 추천해 드릴게요
      </Text>

      {/* 옵션 목록을 하나씩 그려줍니다 */}
      {COOKING_ENV_OPTIONS.map((option) => (
        <TouchableOpacity
          key={option.value}
          style={[
            styles.optionCard,
            cookingEnv === option.value && styles.optionCardSelected,
          ]}
          onPress={() => onSelectCookingEnv(option.value)}
          activeOpacity={0.8}
        >
          <Text style={styles.optionEmoji}>{option.emoji}</Text>
          <View style={styles.optionTextWrap}>
            <Text style={styles.optionTitle}>{option.title}</Text>
            <Text style={styles.optionDescription}>{option.description}</Text>
          </View>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 60,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textLight,
    marginBottom: 32,
  },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  optionCardSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primaryLight,
  },
  optionEmoji: {
    fontSize: 32,
    marginRight: 16,
  },
  optionTextWrap: {
    flex: 1,
  },
  optionTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: colors.text,
  },
  optionDescription: {
    fontSize: 13,
    color: colors.textLight,
    marginTop: 2,
  },
});
