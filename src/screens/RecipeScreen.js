// 탭 2: 오늘 뭐 먹지? (레시피 추천) 화면입니다.
// 원래 계획은 하드코딩된 레시피 10개를 보여주는 것이었지만, 백엔드(LangGraph RAG 에이전트)가
// 갖춰지면서 실제 /recommend API를 호출해 보유 재료·프로필 기반 추천을 받아오는 것으로
// 범위를 키웠습니다. 웹 데모(web/static/index.html)와 동일한 응답 구조를 그대로 렌더링합니다.

import { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors } from '../constants/colors';
import { getUserProfile } from '../utils/storage';
import { ensureProfileSynced, recommend } from '../utils/api';

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function RecipeScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [expandedSteps, setExpandedSteps] = useState({});

  async function handleRecommend() {
    setLoading(true);
    setError(null);
    try {
      // 온보딩 때 서버 동기화가 실패했을 수 있으므로, 추천 직전에 한 번 더 확인한다.
      const localProfile = await getUserProfile();
      await ensureProfileSynced(localProfile);

      const data = await recommend(today());
      setResult(data);
      setExpandedSteps({});
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function toggleSteps(idx) {
    setExpandedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>오늘 뭐 먹지?</Text>

      {!result && !loading && (
        <Text style={styles.subtitle}>
          냉장고 탭에서 재료를 등록한 뒤{'\n'}아래 버튼을 눌러 추천을 받아보세요
        </Text>
      )}

      <TouchableOpacity
        style={[styles.recommendBtn, loading && styles.recommendBtnDisabled]}
        onPress={handleRecommend}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.recommendBtnText}>🍽️ 레시피 추천받기</Text>
        )}
      </TouchableOpacity>

      {error && <Text style={styles.errorText}>{error}</Text>}

      {result && (
        <>
          <View style={[styles.validBanner, result.valid ? styles.validPass : styles.validFail]}>
            <Text style={styles.validBannerText}>
              {result.valid
                ? `✅ 검증 통과 · 재시도 ${result.retryCount}회`
                : `⚠️ 검증 미통과 · 재시도 ${result.retryCount}회 (최선의 결과 반환)`}
            </Text>
          </View>

          {result.recipes.map((recipe, idx) => (
            <View key={idx} style={styles.recipeCard}>
              <View style={styles.recipeHeader}>
                <Text style={styles.recipeName}>{recipe.name}</Text>
                {recipe.usesExpiringIngredient && (
                  <View style={styles.expiringBadge}>
                    <Text style={styles.expiringBadgeText}>⏰ 임박재료 사용</Text>
                  </View>
                )}
              </View>
              <Text style={styles.recipeMeta}>
                ⏱ {recipe.cookingTime}분 · 🍽 {recipe.servings}인분
              </Text>

              {recipe.tags.length > 0 && (
                <View style={styles.tagRow}>
                  {recipe.tags.map((tag) => (
                    <View key={tag} style={styles.tag}>
                      <Text style={styles.tagText}>{tag}</Text>
                    </View>
                  ))}
                </View>
              )}

              <Text style={styles.groupTitle}>사용 재료</Text>
              {recipe.usedIngredients.map((ing) => (
                <Text key={ing.name} style={styles.ingLine}>
                  {ing.name} <Text style={styles.ingAmount}>{ing.amount}</Text>{' '}
                  <Text style={styles.ingPerServing}>· 1인분 {ing.perServingAmount}</Text>
                </Text>
              ))}

              <Text style={styles.groupTitle}>추가 필요</Text>
              {recipe.missingIngredients.length === 0 ? (
                <Text style={styles.ingLineOk}>없음 ✓</Text>
              ) : (
                recipe.missingIngredients.map((ing) => (
                  <Text key={ing.name} style={styles.ingLineMissing}>
                    + {ing.name} {ing.amount}
                  </Text>
                ))
              )}

              <TouchableOpacity onPress={() => toggleSteps(idx)} style={styles.stepsToggle}>
                <Text style={styles.stepsToggleText}>
                  {expandedSteps[idx] ? '▼' : '▶'} 조리 순서 보기 ({recipe.steps.length}단계)
                </Text>
              </TouchableOpacity>
              {expandedSteps[idx] &&
                recipe.steps.map((step, stepIdx) => (
                  <Text key={stepIdx} style={styles.stepLine}>
                    {stepIdx + 1}. {step}
                  </Text>
                ))}
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 40,
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
    marginBottom: 20,
  },
  recommendBtn: {
    backgroundColor: colors.primary,
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  recommendBtnDisabled: {
    backgroundColor: colors.border,
  },
  recommendBtnText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
    marginBottom: 12,
  },
  validBanner: {
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginBottom: 16,
  },
  validPass: {
    backgroundColor: colors.primaryLight,
  },
  validFail: {
    backgroundColor: '#FFF3E0',
  },
  validBannerText: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
  },
  recipeCard: {
    borderWidth: 1.5,
    borderColor: colors.border,
    borderLeftWidth: 4,
    borderLeftColor: colors.primary,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  recipeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  recipeName: {
    fontSize: 17,
    fontWeight: '700',
    color: colors.text,
    flex: 1,
  },
  expiringBadge: {
    backgroundColor: colors.danger,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  expiringBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '700',
  },
  recipeMeta: {
    fontSize: 12,
    color: colors.textLight,
    marginBottom: 10,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 12,
  },
  tag: {
    backgroundColor: colors.primaryLight,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  tagText: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.primary,
  },
  groupTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textLight,
    marginTop: 6,
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  ingLine: {
    fontSize: 13,
    color: colors.text,
    lineHeight: 19,
  },
  ingAmount: {
    color: colors.textLight,
  },
  ingPerServing: {
    color: colors.textLight,
    fontSize: 11,
  },
  ingLineOk: {
    fontSize: 13,
    color: colors.primary,
  },
  ingLineMissing: {
    fontSize: 13,
    color: '#F57C00',
    lineHeight: 19,
  },
  stepsToggle: {
    marginTop: 10,
    paddingVertical: 4,
  },
  stepsToggleText: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.primary,
  },
  stepLine: {
    fontSize: 13,
    color: colors.text,
    lineHeight: 20,
    marginTop: 6,
    paddingLeft: 8,
  },
});
