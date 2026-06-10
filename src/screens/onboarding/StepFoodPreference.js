// 온보딩 Step 3: 음식 취향을 선택하는 화면입니다.
// Step1, Step2와 다르게 "복수 선택"이 가능한 칩(chip) 형태 버튼입니다.
// "가리는 거 없음"을 선택하면 다른 선택은 모두 해제되고,
// 반대로 다른 항목을 고르면 "가리는 거 없음"은 자동으로 해제됩니다.

import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../../constants/colors';

// 화면에 보여줄 음식 취향 옵션 목록
const FOOD_PREFERENCE_OPTIONS = [
  { value: 'korean', label: '한식' },
  { value: 'western', label: '양식' },
  { value: 'japanese', label: '일식' },
  { value: 'highprotein', label: '단백질 위주 (헬스식단)' },
  { value: 'none', label: '가리는 거 없음' },
];

// 현재 선택 목록(current)에 value를 추가/제거한 새 배열을 반환합니다.
// "가리는 거 없음"과 다른 항목은 동시에 선택될 수 없도록 처리합니다.
function toggleFoodPreference(current, value) {
  const isSelected = current.includes(value);

  if (value === 'none') {
    // "가리는 거 없음"을 누르면: 이미 선택돼 있으면 전부 해제, 아니면 이것만 선택
    return isSelected ? [] : ['none'];
  }

  if (isSelected) {
    // 이미 선택된 항목을 다시 누르면 선택 해제
    return current.filter((item) => item !== value);
  }

  // 새 항목을 선택할 때 "가리는 거 없음"이 들어있다면 함께 제거
  return [...current.filter((item) => item !== 'none'), value];
}

// 부모(OnboardingScreen)로부터 현재 선택 목록(foodPreference)과
// 선택이 바뀔 때 호출할 함수(onChangeFoodPreference)를 props로 받습니다.
export default function StepFoodPreference({
  foodPreference,
  onChangeFoodPreference,
}) {
  function handlePress(value) {
    onChangeFoodPreference(toggleFoodPreference(foodPreference, value));
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>어떤 음식을 좋아하시나요?</Text>
      <Text style={styles.subtitle}>여러 개를 골라도 괜찮아요 (복수 선택 가능)</Text>

      {/* 칩 버튼들을 가로로 나열하고, 화면 너비를 넘으면 자동 줄바꿈 */}
      <View style={styles.chipWrap}>
        {FOOD_PREFERENCE_OPTIONS.map((option) => {
          const isSelected = foodPreference.includes(option.value);
          return (
            <TouchableOpacity
              key={option.value}
              style={[styles.chip, isSelected && styles.chipSelected]}
              onPress={() => handlePress(option.value)}
              activeOpacity={0.8}
            >
              <Text
                style={[
                  styles.chipText,
                  isSelected && styles.chipTextSelected,
                ]}
              >
                {option.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
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
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap', // 한 줄에 다 안 들어가면 다음 줄로 넘김
  },
  chip: {
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 24,
    paddingVertical: 10,
    paddingHorizontal: 18,
    marginRight: 10,
    marginBottom: 12,
  },
  chipSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary,
  },
  chipText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  chipTextSelected: {
    color: '#FFFFFF',
  },
});
