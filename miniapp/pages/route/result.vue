<template>
	<view class="page">
		<view class="hero-card">
			<view class="hero-top">
				<view class="hero-badge">AI 推荐路线</view>
				<view class="hero-source">{{ sourceText }}</view>
			</view>

			<view class="hero-title">{{ displayTitle }}</view>
			<view v-if="displayTheme" class="hero-theme">{{ displayTheme }}</view>
			<view class="hero-summary">{{ displaySummary }}</view>

			<view class="stats-grid">
				<view v-for="item in statCards" :key="item.label" class="stat-card">
					<view class="stat-label">{{ item.label }}</view>
					<view class="stat-value">{{ item.value }}</view>
				</view>
			</view>

			<view v-if="reasonCards.length" class="reason-grid">
				<view v-for="item in reasonCards" :key="item.label" class="reason-card">
					<view class="reason-label">{{ item.label }}</view>
					<view class="reason-text">{{ item.text }}</view>
				</view>
			</view>
		</view>

		<view class="action-card">
			<view class="section-title">下一步操作</view>
			<view class="section-desc">这页适合直接截图做“系统智能路线展示”。如果要继续演示，可以从这里进入中途重规划和 AI 文创共创。</view>

			<view class="action-grid">
				<view class="action-panel replan-panel" @tap="goReplan">
					<view class="action-title">中途重规划</view>
					<view class="action-text">根据当前所在展区、剩余时间和新目标，动态生成后半程路线。</view>
					<view class="action-link">继续调整路线</view>
				</view>

				<view class="action-panel creative-panel" @tap="goCreative">
					<view class="action-title">AI 文创共创</view>
					<view class="action-text">围绕路线主题与重点文物生成纪念海报，适合做展示页和传播页截图。</view>
					<view class="action-link">生成纪念海报</view>
				</view>

				<view class="action-panel home-panel" @tap="goHome">
					<view class="action-title">返回首页</view>
					<view class="action-text">重新输入条件，演示不同观众需求下的智能路线生成效果。</view>
					<view class="action-link">重新生成路线</view>
				</view>
			</view>
		</view>

		<view v-if="selectedHalls.length" class="section-card">
			<view class="section-head">
				<view class="section-title">路线时间轴</view>
				<view class="section-desc">以展区为单位呈现推荐停留顺序，强调“为什么这样安排”。</view>
			</view>

			<view class="timeline">
				<view v-for="(hall, index) in selectedHalls" :key="hall.id || index" class="timeline-item">
					<view class="timeline-marker">
						<view class="timeline-index">{{ index + 1 }}</view>
						<view v-if="index !== selectedHalls.length - 1" class="timeline-line"></view>
					</view>
					<view class="timeline-card">
						<view class="timeline-top">
							<view class="timeline-name">{{ hall.name || `第 ${index + 1} 站` }}</view>
							<view v-if="hall.recommended_duration_min" class="timeline-time">{{ hall.recommended_duration_min }} 分钟</view>
						</view>
						<view v-if="safeText(hall.description)" class="timeline-text">{{ hall.description }}</view>
						<view v-else class="timeline-text">建议作为路线中的重点停留展区，帮助观众建立完整而清晰的观展节奏。</view>
					</view>
				</view>
			</view>
		</view>

		<view v-if="featuredExhibits.length" class="section-card">
			<view class="section-head">
				<view class="section-title">重点文物聚焦</view>
				<view class="section-desc">这些文物用于承接“代表性、故事性、讲解性”三类展示目标，也是最适合截图和答辩讲解的核心内容。</view>
			</view>

			<view class="artifact-list">
				<view v-for="(item, index) in featuredExhibits" :key="item.id || index" class="artifact-card">
					<view class="artifact-left">
						<view class="artifact-order">0{{ index + 1 }}</view>
						<image v-if="safeText(item.image_url)" class="artifact-image" :src="item.image_url" mode="aspectFill"></image>
						<view v-else class="artifact-image artifact-placeholder">
							<view class="artifact-placeholder-text">文物主视觉</view>
						</view>
					</view>

					<view class="artifact-main">
						<view class="artifact-title">{{ item.name || '未命名文物' }}</view>

						<view v-if="buildExhibitTags(item).length" class="tag-row">
							<view v-for="tag in buildExhibitTags(item)" :key="`${item.id}-${tag}`" class="tag">{{ tag }}</view>
						</view>

						<view v-if="safeText(item.material)" class="artifact-text">材质：{{ item.material }}</view>
						<view v-if="safeText(item.craft)" class="artifact-text">工艺：{{ item.craft }}</view>
						<view v-if="safeText(item.usage_desc)" class="artifact-text">用途：{{ item.usage_desc }}</view>
						<view v-if="safeText(item.symbolism)" class="artifact-text">文化寓意：{{ item.symbolism }}</view>
						<view v-if="safeText(item.short_intro)" class="artifact-intro">{{ item.short_intro }}</view>

						<button v-if="item.id" class="mini-btn" @tap="goExhibitDetail(item.id, item.name)">查看文物详情</button>
					</view>
				</view>
			</view>
		</view>

		<view v-if="stopGuides.length" class="section-card">
			<view class="section-head">
				<view class="section-title">分站导览说明</view>
				<view class="section-desc">这部分更适合答辩时讲“为什么路线可解释”，展示系统不仅给出结果，也给出推荐理由。</view>
			</view>

			<view class="guide-list">
				<view v-for="(stop, index) in stopGuides" :key="stop.hall_id || index" class="guide-card">
					<view class="guide-top">
						<view class="guide-index">第 {{ index + 1 }} 站</view>
						<view v-if="stop.time_budget_min" class="guide-time">{{ stop.time_budget_min }} 分钟</view>
					</view>

					<view class="guide-title">{{ stop.hall_name || stop.name || `第 ${index + 1} 站` }}</view>
					<view v-if="safeText(stop.hall_theme)" class="guide-text">展区主题：{{ stop.hall_theme }}</view>
					<view v-if="safeText(stop.focus)" class="guide-text">重点看点：{{ stop.focus }}</view>
					<view v-if="safeText(stop.why_here)" class="guide-text">推荐原因：{{ stop.why_here }}</view>
					<view v-if="formatKeyExhibits(stop.key_exhibits)" class="guide-text">建议关注：{{ formatKeyExhibits(stop.key_exhibits) }}</view>
					<view v-if="safeText(stop.transition_to_next)" class="guide-emphasis">转场提示：{{ stop.transition_to_next }}</view>
				</view>
			</view>
		</view>

		<view v-if="safeText(routeData.skip_strategy)" class="section-card note-card">
			<view class="section-title">时间不足时如何压缩</view>
			<view class="section-text">{{ routeData.skip_strategy }}</view>
		</view>

		<view v-if="safeText(routeData.route_closing)" class="section-card note-card">
			<view class="section-title">路线总结</view>
			<view class="section-text">{{ routeData.route_closing }}</view>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

const routeData = ref({})

const demoRouteData = {
	route_title: '楚风青铜寻脉路线',
	route_theme: '楚文化与青铜礼乐',
	route_summary:
		'系统根据首次参观、90 分钟和偏好重点文物的需求，优先推荐最能体现馆藏特色与讲解价值的路线组合。',
	target_fit_reason:
		'这条路线兼顾观展效率、知识浓度和展示观感，适合比赛场景中的产品演示与答辩说明。',
	order_logic:
		'从文化背景到工艺高峰，再到礼乐收束，帮助观众在有限时间内获得更完整的叙事体验。',
	source: 'demo',
	selected_halls: [
		{ id: 'hall-1', name: '楚文化展区', recommended_duration_min: 30, description: '先建立对楚文化整体气质和历史背景的理解。' },
		{ id: 'hall-2', name: '青铜器展区', recommended_duration_min: 35, description: '重点观察馆藏代表性强、适合讲解展示的核心文物。' },
		{ id: 'hall-3', name: '礼乐文明展区', recommended_duration_min: 25, description: '通过礼乐文明进行叙事收束，让路线更完整。' }
	],
	featured_exhibits: [
		{
			id: 'demo-1',
			name: '曾侯乙编钟',
			era: '战国',
			dynasty: '战国早期',
			category: '青铜礼器',
			material: '青铜',
			craft: '铸造',
			usage_desc: '礼乐重器',
			symbolism: '体现楚地礼乐文明的高度发展',
			style_tags: '礼乐、庄重、恢弘',
			short_intro: '是理解礼乐制度、青铜工艺和楚文化气质的最佳入口之一。'
		},
		{
			id: 'demo-2',
			name: '越王勾践剑',
			era: '春秋晚期',
			dynasty: '春秋',
			category: '兵器',
			material: '青铜',
			craft: '复合铸造',
			usage_desc: '王室兵器',
			symbolism: '体现精湛冶铸工艺与历史传奇性',
			style_tags: '锋锐、传奇、工艺',
			short_intro: '兼具辨识度、话题度和工艺亮点，是比赛展示中最容易建立记忆点的文物之一。'
		}
	],
	stop_guides: [
		{
			hall_id: 'hall-1',
			hall_name: '楚文化展区',
			hall_theme: '建立整体文化背景',
			time_budget_min: 30,
			focus: '快速了解楚文化的时代背景、审美风格和器物特征。',
			why_here: '先看文化背景能降低后续理解门槛。',
			key_exhibits: ['虎座鸟架鼓', '彩绘漆木器'],
			transition_to_next: '带着楚文化印象进入青铜器展区。'
		},
		{
			hall_id: 'hall-2',
			hall_name: '青铜器展区',
			hall_theme: '观察工艺高峰与权力表达',
			time_budget_min: 35,
			focus: '围绕代表性礼器和兵器观察青铜工艺及其文化意义。',
			why_here: '这一站最适合展示系统如何聚焦“代表文物”。',
			key_exhibits: ['曾侯乙编钟', '越王勾践剑'],
			transition_to_next: '由工艺高峰转入礼乐文明叙事。'
		}
	],
	skip_strategy: '若现场时间不足，可优先保留青铜器展区和两件核心文物的讲解。',
	route_closing: '整条路线兼顾可看性、可讲性和 AI 推荐逻辑，非常适合参赛展示与用户体验演示。'
}

const safeText = (value) => {
	if (value === null || value === undefined) return ''
	return String(value).trim()
}

const buildFallbackHalls = (route) => {
	const stops = Array.isArray(route?.stop_guides) ? route.stop_guides : []
	return stops.map((item, index) => ({
		id: item?.hall_id || `fallback-hall-${index}`,
		name: item?.hall_name || item?.name || `第 ${index + 1} 站`,
		recommended_duration_min: item?.time_budget_min || '',
		description: item?.focus || item?.why_here || ''
	}))
}

const displayTitle = computed(() => safeText(routeData.value?.route_title) || safeText(routeData.value?.title) || '推荐路线')
const displayTheme = computed(() => safeText(routeData.value?.route_theme) || safeText(routeData.value?.theme))
const displaySummary = computed(() => {
	return (
		safeText(routeData.value?.route_summary) ||
		safeText(routeData.value?.summary) ||
		safeText(routeData.value?.recommendation_reason) ||
		'系统已基于当前输入条件生成推荐路线，可继续查看重点文物、分站说明与后续操作。'
	)
})

const selectedHalls = computed(() => {
	const halls = Array.isArray(routeData.value?.selected_halls) ? routeData.value.selected_halls : []
	if (halls.length) return halls
	return buildFallbackHalls(routeData.value)
})

const featuredExhibits = computed(() => {
	if (Array.isArray(routeData.value?.featured_exhibits)) return routeData.value.featured_exhibits
	if (Array.isArray(routeData.value?.exhibits)) return routeData.value.exhibits
	return []
})

const stopGuides = computed(() => {
	if (Array.isArray(routeData.value?.stop_guides)) return routeData.value.stop_guides
	return []
})

const totalMinutes = computed(() => {
	const total = selectedHalls.value.reduce((sum, item) => sum + Number(item?.recommended_duration_min || 0), 0)
	return total || ''
})

const sourceText = computed(() => {
	const source = safeText(routeData.value?.source)
	if (source === 'llm') return 'AI 深度生成'
	if (source === 'template') return '模板增强结果'
	if (source === 'demo') return '比赛展示示例'
	return '标准推荐结果'
})

const statCards = computed(() => [
	{ label: '推荐展区', value: selectedHalls.value.length || '--' },
	{ label: '重点文物', value: featuredExhibits.value.length || '--' },
	{ label: '建议时长', value: totalMinutes.value ? `${totalMinutes.value} 分钟` : '--' }
])

const reasonCards = computed(() => {
	return [
		{ label: '目标匹配', text: safeText(routeData.value?.target_fit_reason) || safeText(routeData.value?.reason) },
		{ label: '排序逻辑', text: safeText(routeData.value?.order_logic) || safeText(routeData.value?.logic) },
		{ label: '重规划说明', text: safeText(routeData.value?.replan_reason) }
	].filter(item => safeText(item.text))
})

const buildExhibitTags = (item) => {
	const raw = [safeText(item?.era), safeText(item?.dynasty), safeText(item?.category), safeText(item?.sub_category)].filter(Boolean)
	return [...new Set(raw)].slice(0, 4)
}

const formatKeyExhibits = (value) => {
	if (Array.isArray(value) && value.length) return value.filter(Boolean).join('、')
	return safeText(value)
}

const goExhibitDetail = (id, name) => {
	if (!id) {
		uni.showToast({ title: '缺少文物 id', icon: 'none' })
		return
	}
	uni.navigateTo({
		url: `/pages/exhibit/detail?id=${id}&name=${encodeURIComponent(name || '')}`
	})
}

const goReplan = () => {
	uni.navigateTo({ url: '/pages/replan/index' })
}

const goCreative = () => {
	uni.navigateTo({ url: '/pages/creative/index' })
}

const goHome = () => {
	uni.navigateBack({
		delta: 1,
		fail: () => {
			uni.reLaunch({ url: '/pages/index/index' })
		}
	})
}

onLoad(() => {
	const cache = uni.getStorageSync('routeResult')
	routeData.value = cache || demoRouteData
})
</script>

<style scoped>
.page {
	--panel: rgba(255, 251, 246, 0.96);
	--text: #2f241d;
	--muted: #6b6056;
	--brand: #6e8b78;
	--brand-deep: #4c6959;
	--accent: #b98b4d;
	--line: rgba(92, 70, 46, 0.12);
	--shadow: 0 24rpx 54rpx rgba(59, 43, 27, 0.08);
	min-height: 100vh;
	padding: 30rpx 28rpx 40rpx;
	background:
		radial-gradient(circle at 100% 0, rgba(185, 139, 77, 0.18), transparent 24%),
		linear-gradient(180deg, #f7f1e7 0%, #f1e8dc 100%);
	box-sizing: border-box;
}

.hero-card,
.action-card,
.section-card {
	background: var(--panel);
	border-radius: 34rpx;
	padding: 32rpx;
	box-shadow: var(--shadow);
	border: 1rpx solid rgba(255, 255, 255, 0.52);
	margin-bottom: 24rpx;
}

.hero-top,
.timeline-top,
.guide-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16rpx;
}

.hero-badge,
.hero-source,
.timeline-time,
.guide-time,
.guide-index {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	font-size: 22rpx;
	line-height: 1.3;
}

.hero-badge {
	background: rgba(110, 139, 120, 0.14);
	color: var(--brand-deep);
}

.hero-source {
	background: rgba(185, 139, 77, 0.14);
	color: #8d6834;
}

.hero-title,
.section-title,
.timeline-name,
.artifact-title,
.guide-title,
.action-title {
	color: var(--text);
	font-family: 'STSong', 'Songti SC', serif;
}

.hero-title {
	margin-top: 18rpx;
	font-size: 52rpx;
	line-height: 1.18;
	font-weight: 700;
}

.hero-theme {
	margin-top: 12rpx;
	font-size: 28rpx;
	line-height: 1.45;
	color: var(--accent);
	font-weight: 600;
}

.hero-summary,
.section-desc,
.reason-text,
.section-text,
.timeline-text,
.artifact-text,
.artifact-intro,
.guide-text,
.guide-emphasis,
.action-text,
.action-link {
	font-size: 25rpx;
	line-height: 1.82;
	color: var(--muted);
}

.hero-summary {
	margin-top: 18rpx;
}

.stats-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 26rpx;
}

.stat-card {
	padding: 24rpx 18rpx;
	border-radius: 24rpx;
	background: rgba(255, 255, 255, 0.76);
	border: 1rpx solid rgba(185, 139, 77, 0.08);
	text-align: center;
}

.stat-label {
	font-size: 22rpx;
	color: #857a71;
	margin-bottom: 10rpx;
}

.stat-value {
	font-size: 30rpx;
	line-height: 1.35;
	font-weight: 700;
	color: var(--brand-deep);
}

.reason-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 14rpx;
	margin-top: 22rpx;
}

.reason-card {
	padding: 22rpx 20rpx;
	border-radius: 24rpx;
	background: rgba(250, 245, 238, 0.92);
	border: 1rpx solid rgba(110, 139, 120, 0.1);
}

.reason-label {
	font-size: 24rpx;
	line-height: 1.4;
	font-weight: 700;
	color: var(--text);
	margin-bottom: 10rpx;
}

.section-head {
	margin-bottom: 20rpx;
}

.section-title {
	font-size: 38rpx;
	line-height: 1.35;
	font-weight: 700;
}

.section-desc {
	margin-top: 10rpx;
}

.action-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 18rpx;
}

.action-panel {
	border-radius: 28rpx;
	padding: 24rpx;
	min-height: 230rpx;
	box-sizing: border-box;
}

.replan-panel {
	background: linear-gradient(180deg, rgba(185, 139, 77, 0.14), rgba(255, 247, 236, 0.94));
}

.creative-panel {
	background: linear-gradient(180deg, rgba(110, 139, 120, 0.14), rgba(246, 252, 248, 0.96));
}

.home-panel {
	background: linear-gradient(180deg, rgba(47, 36, 29, 0.06), rgba(255, 250, 244, 0.96));
}

.action-title {
	font-size: 30rpx;
	line-height: 1.4;
	font-weight: 700;
	margin-bottom: 14rpx;
}

.action-link {
	margin-top: 16rpx;
	color: var(--brand-deep);
	font-weight: 600;
}

.timeline {
	display: flex;
	flex-direction: column;
	gap: 18rpx;
}

.timeline-item {
	display: flex;
	gap: 18rpx;
	align-items: stretch;
}

.timeline-marker {
	width: 56rpx;
	display: flex;
	flex-direction: column;
	align-items: center;
	flex-shrink: 0;
}

.timeline-index {
	width: 50rpx;
	height: 50rpx;
	border-radius: 50%;
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 24rpx;
	font-weight: 700;
	box-shadow: 0 12rpx 24rpx rgba(73, 103, 86, 0.2);
}

.timeline-line {
	flex: 1;
	width: 4rpx;
	margin-top: 10rpx;
	border-radius: 999rpx;
	background: rgba(110, 139, 120, 0.24);
}

.timeline-card,
.guide-card {
	flex: 1;
	padding: 24rpx;
	border-radius: 26rpx;
	background: rgba(255, 255, 255, 0.8);
	border: 1rpx solid rgba(185, 139, 77, 0.08);
}

.timeline-name,
.guide-title {
	font-size: 30rpx;
	line-height: 1.4;
	font-weight: 700;
}

.timeline-time,
.guide-time,
.guide-index {
	background: rgba(185, 139, 77, 0.12);
	color: #8d6834;
}

.timeline-text {
	margin-top: 12rpx;
}

.artifact-list,
.guide-list {
	display: flex;
	flex-direction: column;
	gap: 18rpx;
}

.artifact-card {
	display: flex;
	gap: 20rpx;
	padding: 22rpx;
	border-radius: 28rpx;
	background: rgba(255, 255, 255, 0.8);
	border: 1rpx solid rgba(110, 139, 120, 0.1);
}

.artifact-left {
	width: 180rpx;
	flex-shrink: 0;
}

.artifact-order {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	background: rgba(47, 36, 29, 0.08);
	color: #6f6459;
	font-size: 22rpx;
	margin-bottom: 14rpx;
}

.artifact-image {
	width: 180rpx;
	height: 180rpx;
	border-radius: 24rpx;
	background: linear-gradient(180deg, #e8ddd0 0%, #d9ccb9 100%);
}

.artifact-placeholder {
	display: flex;
	align-items: center;
	justify-content: center;
}

.artifact-placeholder-text {
	font-size: 24rpx;
	color: #877968;
}

.artifact-main {
	flex: 1;
	min-width: 0;
}

.artifact-title {
	font-size: 34rpx;
	line-height: 1.35;
	font-weight: 700;
}

.tag-row {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 14rpx;
	margin-bottom: 14rpx;
}

.tag {
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	background: rgba(110, 139, 120, 0.12);
	color: var(--brand-deep);
	font-size: 22rpx;
	line-height: 1.3;
}

.artifact-text {
	margin-bottom: 6rpx;
}

.artifact-intro {
	margin-top: 12rpx;
	color: #5e544a;
}

.mini-btn {
	margin-top: 16rpx;
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	border-radius: 999rpx;
	font-size: 24rpx;
	line-height: 1.4;
}

.guide-text {
	margin-top: 10rpx;
}

.guide-emphasis {
	margin-top: 12rpx;
	color: #8d6834;
}

.note-card {
	background: linear-gradient(180deg, rgba(255, 251, 246, 0.96), rgba(249, 244, 236, 0.96));
}

button::after {
	border: none;
}

@media screen and (max-width: 640px) {
	.stats-grid,
	.reason-grid,
	.action-grid {
		grid-template-columns: 1fr;
	}

	.artifact-card {
		flex-direction: column;
	}

	.artifact-left {
		width: 100%;
	}

	.artifact-image {
		width: 100%;
		height: 300rpx;
	}
}
</style>
