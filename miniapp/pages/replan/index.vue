<template>
	<view class="page">
		<view class="header-card">
			<view class="title">中途重规划</view>
			<view class="desc">
				根据你当前所在馆区、已看过的馆区、剩余时间和新的目标，重新生成后续路线。
			</view>
		</view>

		<view v-if="routeCache" class="form-card">
			<view class="section-title">当前路线摘要</view>
			<view class="summary-title">{{ routeCache.route_title || '当前路线' }}</view>
			<view v-if="routeCache.route_theme" class="summary-text">路线主题：{{ routeCache.route_theme }}</view>
			<view v-if="hallOptions.length" class="summary-text">
				当前可选馆区：{{ hallOptions.map(item => item.name).join(' → ') }}
			</view>
			<view v-if="estimatedMinutes" class="summary-text">
				当前路线建议总时长：{{ estimatedMinutes }} 分钟
			</view>
		</view>

		<view v-if="routeCache" class="creative-card">
			<view class="section-title">AI 文创共创</view>
			<view class="summary-text">如果你已经想把这次参观沉淀成纪念成果，可以直接进入文创页生成专属海报，不必先重规划。</view>
			<button class="creative-btn" @tap="goCreative">进入 AI 文创共创</button>
		</view>

		<view class="form-card">
			<view class="section-title">重规划信息</view>

			<view class="form-item">
				<view class="label">当前所在馆区</view>
				<picker mode="selector" :range="hallOptions" range-key="name" @change="onCurrentHallChange">
					<view class="picker-box">{{ currentHallName || '请选择当前馆区' }}</view>
				</picker>
			</view>

			<view class="form-item">
				<view class="label">已访问馆区</view>
				<view v-if="hallOptions.length" class="tag-list">
					<view
						v-for="(item, index) in hallOptions"
						:key="item.id || index"
						class="tag"
						:class="{ 'tag-active': form.visited_hall_ids.includes(item.id), 'tag-disabled': item.id === form.current_hall_id }"
						@tap="toggleVisitedHall(item)"
					>
						{{ item.name }}
					</view>
				</view>
				<view v-else class="empty-tip">请先自动读取当前路线。</view>
				<view class="helper-text">默认会把当前馆区记入已访问；你也可以手动补充之前已经看过的馆区。</view>
			</view>

			<view class="form-item">
				<view class="label">剩余时间（分钟）</view>
				<input class="input" type="number" v-model="form.remaining_minutes" placeholder="例如：60" />
			</view>

			<view class="form-item">
				<view class="label">新的参观目标</view>
				<textarea class="textarea" v-model="form.updated_goal" placeholder="例如：希望后半程更紧凑，优先看楚文化、工艺和重点文物"></textarea>
			</view>
		</view>

		<button class="primary-btn" :disabled="loading" @tap="handleReplan">{{ loading ? '重规划中...' : '生成新的后续路线' }}</button>
		<button class="secondary-btn" @tap="fillFromCurrentRoute">自动读取当前路线</button>
	</view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { replanRoute } from '../../api/route'

const loading = ref(false)
const routeCache = ref(null)
const hallOptions = ref([])
const currentHallIndex = ref(-1)

const form = reactive({
	current_hall_id: null,
	visited_hall_ids: [],
	remaining_minutes: '60',
	updated_goal: ''
})

const currentHallName = computed(() => {
	if (currentHallIndex.value < 0 || !hallOptions.value[currentHallIndex.value]) {
		return ''
	}
	return hallOptions.value[currentHallIndex.value].name
})

const estimatedMinutes = computed(() => {
	if (!routeCache.value?.selected_halls) return 0
	return routeCache.value.selected_halls.reduce((sum, item) => sum + Number(item?.recommended_duration_min || 0), 0)
})

const buildHallOptionsFromRoute = (routeData) => {
	if (!routeData) return []
	const selectedHalls = Array.isArray(routeData.selected_halls) ? routeData.selected_halls : []
	return selectedHalls.map(item => ({ id: item.id, name: item.name }))
}

const setVisitedByCurrentIndex = (index) => {
	const validIndex = Number(index)
	if (validIndex < 0) return
	const visited = hallOptions.value.slice(0, validIndex + 1).map(item => item.id)
	form.visited_hall_ids = Array.from(new Set(visited))
}

const fillFromCurrentRoute = () => {
	const cache = uni.getStorageSync('routeResult')
	if (!cache) {
		uni.showToast({ title: '当前没有缓存路线', icon: 'none' })
		return
	}

	routeCache.value = cache
	hallOptions.value = buildHallOptionsFromRoute(cache)

	if (hallOptions.value.length) {
		currentHallIndex.value = 0
		form.current_hall_id = hallOptions.value[0].id
		setVisitedByCurrentIndex(0)
	}

	if (!form.updated_goal) {
		form.updated_goal = cache.route_theme
			? `希望后半程更紧凑，优先围绕“${cache.route_theme}”继续看重点内容`
			: '希望后半程更紧凑，优先看重点文物和主线内容'
	}

	if (!form.remaining_minutes && estimatedMinutes.value) {
		form.remaining_minutes = String(estimatedMinutes.value)
	}

	uni.showToast({ title: '已自动读取当前路线', icon: 'none' })
}

const onCurrentHallChange = (e) => {
	const index = Number(e.detail.value)
	currentHallIndex.value = index
	const selected = hallOptions.value[index]
	if (!selected) return
	form.current_hall_id = selected.id
	setVisitedByCurrentIndex(index)
}

const toggleVisitedHall = (item) => {
	if (!item?.id || item.id === form.current_hall_id) return
	const exists = form.visited_hall_ids.includes(item.id)
	form.visited_hall_ids = exists ? form.visited_hall_ids.filter(id => id !== item.id) : [...form.visited_hall_ids, item.id]
}

const handleReplan = async () => {
	if (!form.current_hall_id) {
		uni.showToast({ title: '请选择当前馆区', icon: 'none' })
		return
	}
	if (!form.remaining_minutes) {
		uni.showToast({ title: '请填写剩余时间', icon: 'none' })
		return
	}
	if (!form.updated_goal) {
		uni.showToast({ title: '请填写新的参观目标', icon: 'none' })
		return
	}

	loading.value = true
	try {
		const visited = Array.from(new Set([...form.visited_hall_ids.map(id => Number(id)), Number(form.current_hall_id)]))
		const payload = {
			current_hall_id: Number(form.current_hall_id),
			visited_hall_ids: visited,
			remaining_minutes: Number(form.remaining_minutes),
			updated_goal: form.updated_goal
		}
		const res = await replanRoute(payload)
		uni.setStorageSync('routeResult', res)
		uni.redirectTo({ url: '/pages/route/result' })
	} catch (error) {
		console.error('重规划失败：', error)
		uni.showToast({ title: error?.data?.detail?.[0]?.msg || error?.message || '重规划失败', icon: 'none', duration: 3000 })
	} finally {
		loading.value = false
	}
}

const goCreative = () => {
	uni.navigateTo({ url: '/pages/creative/index' })
}

onLoad(() => {
	fillFromCurrentRoute()
})
</script>

<style scoped>
.page { min-height: 100vh; padding: 30rpx; background: #F8F4EC; box-sizing: border-box; }
.header-card, .form-card, .creative-card { background: #FFFFFF; border-radius: 24rpx; padding: 30rpx; box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.05); margin-bottom: 30rpx; }
.title { font-size: 40rpx; font-weight: 700; color: #2F5D50; margin-bottom: 18rpx; }
.desc, .summary-text, .helper-text { font-size: 27rpx; color: #666666; line-height: 1.8; }
.summary-title { font-size: 30rpx; font-weight: 600; color: #8A6D3B; margin-bottom: 14rpx; }
.helper-text { margin-top: 14rpx; font-size: 24rpx; color: #999999; }
.section-title { font-size: 32rpx; font-weight: 600; color: #2F5D50; margin-bottom: 24rpx; }
.form-item { margin-bottom: 26rpx; }
.label { font-size: 28rpx; font-weight: 600; color: #333333; margin-bottom: 14rpx; }
.input, .picker-box { height: 82rpx; background: #F8F4EC; border-radius: 18rpx; padding: 0 24rpx; box-sizing: border-box; display: flex; align-items: center; font-size: 27rpx; color: #333333; }
.textarea { width: 100%; min-height: 200rpx; background: #F8F4EC; border-radius: 18rpx; padding: 20rpx 24rpx; box-sizing: border-box; font-size: 27rpx; color: #333333; line-height: 1.7; }
.tag-list { display: flex; flex-wrap: wrap; gap: 14rpx; }
.tag { padding: 12rpx 22rpx; border-radius: 999rpx; background: #F8F4EC; color: #666666; font-size: 24rpx; line-height: 1.4; }
.tag-active { background: rgba(47, 93, 80, 0.14); color: #2F5D50; }
.tag-disabled { opacity: 0.55; }
.empty-tip { font-size: 24rpx; color: #999999; }
.primary-btn, .secondary-btn, .creative-btn { width: 100%; border-radius: 999rpx; font-size: 28rpx; line-height: 1.4; }
.primary-btn { background: #2F5D50; color: #FFFFFF; margin-bottom: 20rpx; }
.secondary-btn { background: #8A6D3B; color: #FFFFFF; }
.creative-btn { margin-top: 20rpx; background: #8A6D3B; color: #FFFFFF; }
</style>
