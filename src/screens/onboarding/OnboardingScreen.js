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
import { saveProfile } from '../../utils/api';
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
  // memberCount: 가구원 수 (1~5, 5는 "5명 이상"을 의미). householdType은 여기서 자동 계산
  // (웹 데모에서 1인가구/핵가족 칩이 2~3인 가구에 애매했던 문제를 같은 방식으로 해결 —
  // docs/ENGINEERING_LOG.md "Phase 4-2" 참고).
  const [memberCount, setMemberCount] = useState(1);
  // cookingEnv: "microwave" | "oneburner" | "full" | null(미선택)
  const [cookingEnv, setCookingEnv] = useState(null);
  // foodPreference: 선택된 음식 취향 값들의 배열 (예: ["korean", "highprotein"])
  const [foodPreference, setFoodPreference] = useState([]);

  // 현재 단계에서 "다음" 버튼을 눌러도 되는지 확인합니다.
  // - Step1: 가구원 수는 항상 기본값(1명)이 있으므로 별도 선택 없이도 진행 가능
  // - Step2: 조리 환경을 선택해야 함
  // - Step3: 음식 취향을 1개 이상 선택해야 함
  function canGoNext() {
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
      const profile = {
        householdType: memberCount === 1 ? 'single' : 'family',
        memberCount,
        cookingEnv,
        foodPreference,
      };

      // 1) 기기 로컬(AsyncStorage)에 저장 — 앱 재실행 시 "온보딩 완료 여부" 판단에 씀
      await saveUserProfile(profile);

      // 2) 백엔드 DB에도 저장 — 레시피 추천 API(/recommend)는 이 DB의 프로필을 읽음.
      //    네트워크가 없거나 백엔드 주소가 아직 안 맞아도 온보딩 자체는 막지 않고
      //    best-effort로만 시도한다 — 추천을 누르는 시점에 ensureProfileSynced로
      //    한 번 더 재시도하기 때문에(api.js), 여기서 실패해도 복구 가능하다.
      try {
        await saveProfile(profile);
      } catch (e) {
        console.warn('온보딩 중 서버 프로필 동기화 실패(나중에 재시도됨):', e.message);
      }

      // 3) 메인 탭 화면으로 이동합니다.
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
        {/* Step 1: 가구원 수 선택 */}
        <View style={{ width: SCREEN_WIDTH }}>
          <StepHousehold memberCount={memberCount} onChangeMemberCount={setMemberCount} />
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
