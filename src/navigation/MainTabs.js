// 온보딩이 끝난 뒤 보여줄 메인 화면입니다.
// 하단에 탭 3개(냉장고 / 오늘 뭐 먹지? / 리포트)를 두고 화면을 전환합니다.

import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { colors } from '../constants/colors';
import FridgeScreen from '../screens/FridgeScreen';
import RecipeScreen from '../screens/RecipeScreen';
import ReportScreen from '../screens/ReportScreen';

const Tab = createBottomTabNavigator();

// 탭 이름에 맞는 아이콘 이름을 정해주는 함수
// (선택된 탭은 채워진 아이콘, 아닌 탭은 테두리만 있는 아이콘을 사용)
function getIconName(routeName, focused) {
  switch (routeName) {
    case '냉장고':
      return focused ? 'snow' : 'snow-outline';
    case '오늘 뭐 먹지?':
      return focused ? 'restaurant' : 'restaurant-outline';
    case '리포트':
      return focused ? 'bar-chart' : 'bar-chart-outline';
    default:
      return 'ellipse-outline';
  }
}

export default function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false, // 각 화면에서 자체적으로 제목을 표시하므로 헤더는 숨김
        tabBarActiveTintColor: colors.primary, // 선택된 탭 색상
        tabBarInactiveTintColor: colors.textLight, // 선택 안 된 탭 색상
        // 탭마다 다른 아이콘을 보여주기 위한 설정
        tabBarIcon: ({ focused, color, size }) => (
          <Ionicons
            name={getIconName(route.name, focused)}
            size={size}
            color={color}
          />
        ),
      })}
    >
      <Tab.Screen name="냉장고" component={FridgeScreen} />
      <Tab.Screen name="오늘 뭐 먹지?" component={RecipeScreen} />
      <Tab.Screen name="리포트" component={ReportScreen} />
    </Tab.Navigator>
  );
}
