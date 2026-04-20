<template>
	<view class="page">
		<view v-if="loading" class="card loading-card">
			<view class="loading-text">加载中...</view>
		</view>

		<view v-else>
			<view class="card hero-card">
				<view class="hero-badge">相关文物</view>
				<view class="hero-name">围绕“{{ exhibit.name || pageName || '当前文物' }}”继续看</view>
				<view v-if="heroText" class="hero-text">{{ heroText }}</view>
			</view>

			<view v-if="relatedList.length" class="list-wrap">
				<view v-for="(item, index) in relatedList" :key="item.id || index" class="card related-card" @tap="goDetail(item)">
					<view class="related-top">
						<view class="related-name">{{ item.name }}</view>
						<view v-if="relationTypeLabel(item.relation_type)" class="related-chip">{{ relationTypeLabel(item.relation_type) }}</view>
					</view>
					<view v-if="buildMeta(item)" class="related-meta">{{ buildMeta(item) }}</view>
					<view v-if="safeText(item.relation_summary)" class="related-text">{{ item.relation_summary }}</view>
					<view v-else-if="safeText(item.short_intro)" class="related-text">{{ item.short_intro }}</view>
					<view v-if="buildTagList(item).length" class="tag-list">
						<view v-for="(tag, tagIndex) in buildTagList(item)" :key="`${item.id}-${tagIndex}`" class="tag">{{ tag }}</view>
					</view>
					<view class="action-text">点此查看这件文物</view>
				</view>
			</view>
			<view v-else class="card">
				<view class="empty-text">暂时还没有整理出更多相关文物。</view>
			</view>

			<view v-if="errorText" class="card error-card">
				<view class="error-text">{{ errorText }}</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getExhibitDetail, getExhibitGraph } from '../../api/exhibit'

const loading = ref(true)
const exhibitId = ref('')
const pageName = ref('')
const exhibit = ref({})
const graphData = ref({})
const errorText = ref('')

const safeText = (value) => {
	if (value === null || value === undefined) return ''
	return String(value).trim()
}

const uniqueById = (list) => {
	const result = []
	const seen = new Set()
	;(list || []).forEach(item => {
		const key = item?.id || `${item?.name || ''}-${item?.hall_id || ''}`
		if (!key || seen.has(key)) return
		seen.add(key)
		result.push(item)
	})
	return result
}

const relationTypeLabel = (relationType) => {
	const labelMap = {
		same_theme: '同主题',
		same_craft: '同工艺',
		same_material: '同材质',
		same_hall: '同馆延伸',
		background_for: '背景补充',
		contrast: '对照观看',
		route_next: '推荐下一站',
		thematic: '专题延展'
	}
	return labelMap[relationType] || safeText(relationType)
}

const heroText = computed(() => {
	return safeText(graphData.value?.graph_summary) || safeText(exhibit.value?.related_exhibits_hint) || '把适合继续连看的对象单独拉出来看，会比堆在主详情页里更清楚。'
})

const relatedList = computed(() => {
	const detailRelated = Array.isArray(exhibit.value?.related_exhibits) ? exhibit.value.related_exhibits : []
	const graphRelated = Array.isArray(graphData.value?.related_nodes) ? graphData.value.related_nodes : []
	return uniqueById([...detailRelated, ...graphRelated])
})

const buildMeta = (item) => {
	return [
		safeText(item?.era),
		safeText(item?.dynasty),
		safeText(item?.category),
		safeText(item?.hall_name)
	].filter(Boolean).join(' · ')
}

const buildTagList = (item) => {
	return [
		relationTypeLabel(item?.relation_type),
		safeText(item?.category),
		safeText(item?.hall_name)
	].filter(Boolean).slice(0, 3)
}

const goDetail = (item) => {
	if (!item?.id) return
	uni.navigateTo({
		url: `/pages/exhibit/detail?id=${item.id}&name=${encodeURIComponent(item.name || '')}`
	})
}

const fetchData = async () => {
	if (!exhibitId.value) {
		errorText.value = '缺少文物 id'
		loading.value = false
		return
	}
	loading.value = true
	errorText.value = ''
	try {
		const [detailRes, graphRes] = await Promise.all([
			getExhibitDetail(exhibitId.value),
			getExhibitGraph(exhibitId.value)
		])
		exhibit.value = detailRes || {}
		graphData.value = graphRes || {}
	} catch (error) {
		console.error('相关文物获取失败：', error)
		errorText.value = error?.message || '相关文物加载失败'
	} finally {
		loading.value = false
	}
}

onLoad((options) => {
	exhibitId.value = options?.id || ''
	pageName.value = decodeURIComponent(options?.name || '')
	fetchData()
})
</script>

<style scoped>
.page {
	min-height: 100vh;
	padding: 30rpx;
	background: #F8F4EC;
	box-sizing: border-box;
}

.card {
	background: #FFFFFF;
	border-radius: 26rpx;
	padding: 30rpx;
	box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.05);
	margin-bottom: 24rpx;
}

.loading-text,
.empty-text,
.error-text {
	font-size: 28rpx;
	color: #666666;
	text-align: center;
	line-height: 1.8;
}

.hero-badge {
	display: inline-flex;
	padding: 10rpx 18rpx;
	border-radius: 999rpx;
	background: rgba(47, 93, 80, 0.1);
	color: #2F5D50;
	font-size: 24rpx;
	line-height: 1.3;
	margin-bottom: 16rpx;
}

.hero-name {
	font-size: 36rpx;
	font-weight: 700;
	color: #2F5D50;
	line-height: 1.45;
	margin-bottom: 14rpx;
}

.hero-text,
.related-text {
	font-size: 26rpx;
	line-height: 1.8;
	color: #555555;
}

.list-wrap {
	display: flex;
	flex-direction: column;
	gap: 18rpx;
}

.related-card {
	padding: 26rpx;
}

.related-top {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 16rpx;
	margin-bottom: 10rpx;
}

.related-name {
	font-size: 30rpx;
	font-weight: 700;
	color: #333333;
	line-height: 1.45;
}

.related-chip {
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	background: rgba(199, 166, 106, 0.16);
	font-size: 22rpx;
	color: #8A6D3B;
	line-height: 1.3;
	white-space: nowrap;
}

.related-meta {
	font-size: 23rpx;
	line-height: 1.7;
	color: #8B8175;
	margin-bottom: 12rpx;
}

.tag-list {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 14rpx;
}

.tag {
	padding: 8rpx 14rpx;
	border-radius: 999rpx;
	background: rgba(47, 93, 80, 0.1);
	color: #2F5D50;
	font-size: 22rpx;
	line-height: 1.3;
}

.action-text {
	margin-top: 14rpx;
	font-size: 24rpx;
	color: #2F5D50;
	font-weight: 600;
}
</style>
