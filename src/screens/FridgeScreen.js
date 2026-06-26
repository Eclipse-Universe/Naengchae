// 탭 1: 냉장고 (홈) 화면입니다.
// 웹 데모(web/static/index.html)와 동일한 /fridge API를 호출합니다 — 같은 백엔드, 같은
// 데이터를 쓰므로 웹에서 추가한 재료가 모바일에도 그대로 보입니다.
//
// 유통기한은 정확한 날짜 대신 "곧 먹어야 해요" 토글 하나로 입력받습니다. 대부분의 사용자가
// 재료의 정확한 소비기한을 모른다는 웹 데모 사용 피드백을 반영한 것으로, 토글을 켜면 내부적으로
// 오늘 날짜를 보내 백엔드의 임박 판정 로직(EXPIRY_WARNING_DAYS)을 그대로 재사용합니다
// (자세한 이유는 docs/ENGINEERING_LOG.md의 "Phase 4-3" 참고).

import { useCallback, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors } from '../constants/colors';
import { getFridge, addFridgeIngredient, deleteFridgeIngredient } from '../utils/api';

function today() {
  return new Date().toISOString().slice(0, 10);
}

// expiryDate(있으면)와 오늘 날짜의 차이를 일 단위로 계산합니다. 없으면 null.
function daysUntil(expiryDate) {
  if (!expiryDate) return null;
  const diff = (new Date(expiryDate) - new Date(today())) / 86400000;
  return Math.ceil(diff);
}

export default function FridgeScreen() {
  const [ingredients, setIngredients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [name, setName] = useState('');
  const [urgentOn, setUrgentOn] = useState(false);
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await getFridge();
      setIngredients(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // 다른 탭(예: 웹 데모나 추천 화면)에서 재료가 바뀌었을 수 있으므로, 이 탭에 올 때마다 다시 불러온다.
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed || adding) return;
    setAdding(true);
    try {
      const expiryDate = urgentOn ? today() : null;
      await addFridgeIngredient(trimmed, expiryDate);
      setName('');
      setUrgentOn(false);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteFridgeIngredient(id);
      setIngredients((prev) => prev.filter((ing) => ing.id !== id));
    } catch (e) {
      setError(e.message);
    }
  }

  function renderItem({ item }) {
    const days = daysUntil(item.expiryDate);
    const isUrgent = days !== null && days <= 3;
    let badgeText = null;
    if (days !== null) {
      badgeText = days <= 0 ? '오늘 만료' : `D+${days}`;
    }
    return (
      <View style={[styles.row, isUrgent && styles.rowUrgent]}>
        <Text style={styles.rowName}>{item.name}</Text>
        <View style={styles.rowRight}>
          {badgeText && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{badgeText}</Text>
            </View>
          )}
          <TouchableOpacity onPress={() => handleDelete(item.id)} style={styles.deleteBtn}>
            <Ionicons name="close" size={18} color={colors.textLight} />
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Text style={styles.title}>냉장고</Text>

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="재료명 (예: 계란)"
          value={name}
          onChangeText={setName}
          onSubmitEditing={handleAdd}
          returnKeyType="done"
        />
      </View>
      <View style={styles.inputRow}>
        <TouchableOpacity
          style={[styles.urgentChip, urgentOn && styles.urgentChipOn]}
          onPress={() => setUrgentOn((v) => !v)}
        >
          <Text style={[styles.urgentChipText, urgentOn && styles.urgentChipTextOn]}>
            🔥 곧 먹어야 해요
          </Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.addBtn} onPress={handleAdd} disabled={adding}>
          <Text style={styles.addBtnText}>추가</Text>
        </TouchableOpacity>
      </View>

      {error && <Text style={styles.errorText}>{error}</Text>}

      {loading ? (
        <Text style={styles.emptyText}>불러오는 중...</Text>
      ) : (
        <FlatList
          data={ingredients}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load();
              }}
            />
          }
          ListEmptyComponent={<Text style={styles.emptyText}>재료를 추가해보세요</Text>}
          contentContainerStyle={ingredients.length === 0 && styles.emptyContainer}
        />
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: 20,
    paddingTop: 60,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  input: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: colors.text,
  },
  urgentChip: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
  },
  urgentChipOn: {
    backgroundColor: colors.danger,
    borderColor: colors.danger,
  },
  urgentChipText: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textLight,
  },
  urgentChipTextOn: {
    color: '#FFFFFF',
  },
  addBtn: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 20,
    justifyContent: 'center',
  },
  addBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 14,
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.primaryLight,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 8,
  },
  rowUrgent: {
    backgroundColor: '#FFEBEE',
  },
  rowName: {
    fontSize: 15,
    fontWeight: '500',
    color: colors.text,
  },
  rowRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  badge: {
    backgroundColor: colors.danger,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  deleteBtn: {
    padding: 4,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.textLight,
    fontSize: 14,
    marginTop: 24,
  },
  emptyContainer: {
    flexGrow: 1,
  },
});
