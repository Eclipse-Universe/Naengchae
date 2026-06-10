// 온보딩 Step 1: 가구 유형을 선택하는 화면입니다.
// "혼자 살아요" / "가족이랑 살아요" 중 하나를 고르고,
// 가족을 선택한 경우에는 인원수 슬라이더가 추가로 나타납니다.

import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Slider from '@react-native-community/slider';
import { colors } from '../../constants/colors';

// 인원수(1~5)를 화면에 표시할 때 쓸 글자를 만들어주는 함수
// 5는 "5명 이상"을 의미하므로 "5명+"로 보여줍니다.
function memberCountLabel(count) {
  if (count >= 5) {
    return '5명+';
  }
  return `${count}명`;
}

// 부모(OnboardingScreen)로부터 현재 선택값과,
// 값이 바뀌었을 때 호출할 함수들을 props로 받습니다.
// → 이렇게 부모가 상태를 가지고 자식에게 내려주는 방식을 "controlled component"라고 합니다.
export default function StepHousehold({
  householdType,
  memberCount,
  onSelectHouseholdType,
  onChangeMemberCount,
}) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>어떤 환경에서 생활하시나요?</Text>
      <Text style={styles.subtitle}>
        선택하신 정보로 더 알맞은 레시피를 추천해 드릴게요
      </Text>

      {/* 선택지 1: 1인 가구 */}
      <TouchableOpacity
        style={[
          styles.optionCard,
          householdType === 'single' && styles.optionCardSelected,
        ]}
        onPress={() => onSelectHouseholdType('single')}
        activeOpacity={0.8}
      >
        <Text style={styles.optionEmoji}>🧑</Text>
        <View style={styles.optionTextWrap}>
          <Text style={styles.optionTitle}>혼자 살아요</Text>
          <Text style={styles.optionDescription}>1인 가구</Text>
        </View>
      </TouchableOpacity>

      {/* 선택지 2: 가족(핵가족) */}
      <TouchableOpacity
        style={[
          styles.optionCard,
          householdType === 'family' && styles.optionCardSelected,
        ]}
        onPress={() => onSelectHouseholdType('family')}
        activeOpacity={0.8}
      >
        <Text style={styles.optionEmoji}>👨‍👩‍👧</Text>
        <View style={styles.optionTextWrap}>
          <Text style={styles.optionTitle}>가족이랑 살아요</Text>
          <Text style={styles.optionDescription}>핵가족</Text>
        </View>
      </TouchableOpacity>

      {/* 가족을 선택했을 때만 인원수 슬라이더를 보여줍니다 */}
      {householdType === 'family' && (
        <View style={styles.sliderSection}>
          <Text style={styles.sliderLabel}>
            인원수: {memberCountLabel(memberCount)}
          </Text>
          <Slider
            style={styles.slider}
            minimumValue={1}
            maximumValue={5}
            step={1}
            value={memberCount}
            onValueChange={onChangeMemberCount}
            minimumTrackTintColor={colors.primary}
            maximumTrackTintColor={colors.border}
            thumbTintColor={colors.primary}
          />
          {/* 슬라이더 양 끝에 보여줄 안내 글자 */}
          <View style={styles.sliderRangeRow}>
            <Text style={styles.sliderRangeText}>1명</Text>
            <Text style={styles.sliderRangeText}>5명+</Text>
          </View>
        </View>
      )}
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
  // 선택된 카드는 테두리와 배경색을 메인 색상으로 강조합니다
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
  sliderSection: {
    marginTop: 16,
    paddingHorizontal: 4,
  },
  sliderLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
    textAlign: 'center',
  },
  slider: {
    width: '100%',
    height: 40,
  },
  sliderRangeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  sliderRangeText: {
    fontSize: 12,
    color: colors.textLight,
  },
});
