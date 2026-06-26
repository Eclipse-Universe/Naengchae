// 온보딩 Step 1: 가구원 수를 선택하는 화면입니다.
//
// 원래는 "혼자 살아요"/"가족이랑 살아요" 두 카드 중 하나를 고르고, "가족"을 선택했을 때만
// 인원수 슬라이더가 나타나는 구조였습니다. 그런데 웹 데모를 먼저 만들어 써보니 2~3인 가구가
// 둘 중 뭘 골라야 할지 애매하다는 문제가 있었습니다(자세한 원인은
// docs/ENGINEERING_LOG.md의 "Phase 4-2" 참고). 웹에서 이미 고친 것과 동일하게, 가구원 수
// 슬라이더 하나만 항상 보여주고 householdType(single/family)은 인원수에서 자동으로
// 계산합니다.

import { View, Text, StyleSheet } from 'react-native';
import Slider from '@react-native-community/slider';
import { colors } from '../../constants/colors';

function memberCountLabel(count) {
  if (count >= 5) {
    return '5명+';
  }
  return `${count}명`;
}

// 부모(OnboardingScreen)로부터 현재 선택값과, 값이 바뀌었을 때 호출할 함수를 props로 받습니다.
export default function StepHousehold({ memberCount, onChangeMemberCount }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>몇 명과 함께 식사하시나요?</Text>
      <Text style={styles.subtitle}>
        가구원 수에 맞춰 레시피 분량과 재료 양을 계산해 드릴게요
      </Text>

      <View style={styles.sliderSection}>
        <Text style={styles.sliderLabel}>{memberCountLabel(memberCount)}</Text>
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
        <View style={styles.sliderRangeRow}>
          <Text style={styles.sliderRangeText}>1명</Text>
          <Text style={styles.sliderRangeText}>5명+</Text>
        </View>
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
  sliderSection: {
    marginTop: 24,
    paddingHorizontal: 4,
  },
  sliderLabel: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 16,
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
