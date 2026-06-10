// 온보딩 화면 전체를 감싸는 컨테이너입니다.
// - 가로로 스와이프되는 3개의 카드(Step1~3)를 보여줍니다.
// - 모든 단계에서 공통으로 쓰는 사용자 정보(profile)를 이 화면에서 관리하고
//   각 Step 컴포넌트에는 props로 내려줍니다.

import { useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { colors } from '../../constants/colors';
import { saveUserProfile } from '../../utils/storage';
import StepHousehold from './StepHousehold';
import StepCookingEnv from './StepCookingEnv';
import StepFoodPreference from './StepFoodPreference';

// 현재 기기 화면의 가로 너비 (스와이프 카드 한 장의 너비로 사용)
const { width: SCREEN_WIDTH } = Dimensions.get('window');

// 온보딩 단계는 총 3단계입니다.
const TOTAL_STEPS = 3;

// navigation: Stack.Navigator가 화면에 자동으로 넘겨주는 객체
// (이 객체로 다른 화면으로 이동할 수 있습니다)
export default function OnboardingScreen({ navigation }) {
  // ScrollView를 코드에서 직접 제어하기 위한 ref
  // (예: "다음" 버튼을 누르면 다음 카드로 스크롤 이동)
  const scrollViewRef = useRef(null);

  // 현재 보고 있는 단계 (0번 = Step1, 1번 = Step2, 2번 = Step3)
  const [currentStep, setCurrentStep] = useState(0);

  // ── 온보딩에서 수집할 사용자 프로필 정보 ──────────────────
  // householdType: "single"(1인 가구) | "family"(핵가족) | null(미선택)
  const [householdType, setHouseholdType] = useState(null);
  // memberCount: 가족 인원수 (1~5, 5는 "5명 이상"을 의미)
  const [memberCount, setMemberCount] = useState(1);
  // cookingEnv: "microwave" | "oneburner" | "full" | null(미선택)
  const [cookingEnv, setCookingEnv] = useState(null);
  // foodPreference: 선택된 음식 취향 값들의 배열 (예: ["korean", "highprotein"])
  const [foodPreference, setFoodPreference] = useState([]);

  // Step1에서 "혼자 살아요"를 선택하면 인원수를 자동으로 1명으로 맞춰줍니다.
  function handleSelectHouseholdType(type) {
    setHouseholdType(type);
    if (type === 'single') {
      setMemberCount(1);
    }
  }

  // 현재 단계에서 "다음" 버튼을 눌러도 되는지 확인합니다.
  // - Step1: 가구 유형을 선택해야 함
  // - Step2: 조리 환경을 선택해야 함
  // - Step3: 음식 취향을 1개 이상 선택해야 함
  function canGoNext() {
    if (currentStep === 0) {
      return householdType !== null;
    }
    if (currentStep === 1) {
      return cookingEnv !== null;
    }
    if (currentStep === 2) {
      return foodPreference.length > 0;
    }
    return true;
  }

  // "다음" 버튼을 눌렀을 때 실행되는 함수
  async function handleNext() {
    if (!canGoNext()) {
      return;
    }

    if (currentStep === TOTAL_STEPS - 1) {
      // 마지막 단계(Step3)에서는 온보딩을 마칩니다.
      // 1) 지금까지 선택한 정보를 AsyncStorage에 저장하고
      const profile = {
        householdType,
        memberCount,
        cookingEnv,
        foodPreference,
      };
      await saveUserProfile(profile);

      // 2) 메인 탭 화면으로 이동합니다.
      //    replace를 사용해서 "뒤로 가기"를 눌러도 온보딩으로
      //    돌아오지 않도록 합니다.
      navigation.replace('MainTabs');
      return;
    }

    // 다음 카드 위치로 스크롤 이동
    const nextStep = currentStep + 1;
    scrollViewRef.current?.scrollTo({
      x: nextStep * SCREEN_WIDTH,
      animated: true,
    });
    setCurrentStep(nextStep);
  }

  // 사용자가 손가락으로 직접 스와이프를 끝냈을 때,
  // 스크롤 위치를 계산해서 현재 단계(currentStep)를 업데이트합니다.
  function handleScrollEnd(event) {
    const offsetX = event.nativeEvent.contentOffset.x;
    const newStep = Math.round(offsetX / SCREEN_WIDTH);
    setCurrentStep(newStep);
  }

  return (
    <View style={styles.container}>
      {/* 가로로 스와이프되는 온보딩 카드 영역 */}
      <ScrollView
        ref={scrollViewRef}
        horizontal // 가로 방향 스크롤
        pagingEnabled // 한 화면씩 딱딱 끊어서 넘어가도록 설정 (카드 스와이프 느낌)
        showsHorizontalScrollIndicator={false} // 스크롤바 숨기기
        scrollEventThrottle={16} // 스크롤 이벤트를 얼마나 자주 감지할지
        onMomentumScrollEnd={handleScrollEnd}
      >
        {/* Step 1: 가구 유형 선택 (이번 작업에서 완성) */}
        <View style={{ width: SCREEN_WIDTH }}>
          <StepHousehold
            householdType={householdType}
            memberCount={memberCount}
            onSelectHouseholdType={handleSelectHouseholdType}
            onChangeMemberCount={setMemberCount}
          />
        </View>

        {/* Step 2: 조리 환경 선택 */}
        <View style={{ width: SCREEN_WIDTH }}>
          <StepCookingEnv
            cookingEnv={cookingEnv}
            onSelectCookingEnv={setCookingEnv}
          />
        </View>

        {/* Step 3: 음식 취향 선택 */}
        <View style={{ width: SCREEN_WIDTH }}>
          <StepFoodPreference
            foodPreference={foodPreference}
            onChangeFoodPreference={setFoodPreference}
          />
        </View>
      </ScrollView>

      {/* 하단 영역: 진행 상태 점(dot) + 다음 버튼 */}
      <View style={styles.footer}>
        {/* 현재 몇 번째 단계인지 보여주는 점들 */}
        <View style={styles.dotRow}>
          {Array.from({ length: TOTAL_STEPS }).map((_, index) => (
            <View
              key={index}
              style={[
                styles.dot,
                index === currentStep && styles.dotActive,
              ]}
            />
          ))}
        </View>

        {/* 다음 / 시작하기 버튼 */}
        <TouchableOpacity
          style={[
            styles.nextButton,
            !canGoNext() && styles.nextButtonDisabled,
          ]}
          onPress={handleNext}
          disabled={!canGoNext()}
          activeOpacity={0.8}
        >
          <Text style={styles.nextButtonText}>
            {currentStep === TOTAL_STEPS - 1 ? '시작하기' : '다음'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 40,
    paddingTop: 12,
    alignItems: 'center',
  },
  dotRow: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
    marginHorizontal: 4,
  },
  dotActive: {
    backgroundColor: colors.primary,
    width: 20, // 현재 단계의 점은 길쭉하게 표시
  },
  nextButton: {
    width: '100%',
    backgroundColor: colors.primary,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
  },
  nextButtonDisabled: {
    backgroundColor: colors.border,
  },
  nextButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
