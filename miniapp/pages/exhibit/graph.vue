<template>
	<view class="page">
		<view v-if="loading" class="state-card">
			<view class="state-text">知识图谱加载中...</view>
		</view>

		<view v-else>
			<view class="hero-card">
				<view class="hero-badge">知识图谱</view>
				<view class="hero-title">{{ exhibit.name || pageName || '未命名文物' }}</view>
				<view v-if="heroMeta" class="hero-meta">{{ heroMeta }}</view>
				<view class="hero-summary">{{ graphSummaryText || '围绕当前文物，系统会将时间、工艺、主题与关联对象整理成更适合理解的知识网络。' }}</view>

				<view class="hero-stats">
					<view class="hero-stat-card">
						<view class="hero-stat-label">关联节点</view>
						<view class="hero-stat-value">{{ graphNodes.length || '--' }}</view>
					</view>
					<view class="hero-stat-card">
						<view class="hero-stat-label">时间线条目</view>
						<view class="hero-stat-value">{{ graphTimelineItems.length || '--' }}</view>
					</view>
					<view class="hero-stat-card">
						<view class="hero-stat-label">主要关系</view>
						<view class="hero-stat-value">{{ topRelationLabel }}</view>
					</view>
				</view>
			</view>

			<view class="tab-row">
				<view
					v-for="tab in graphViewTabs"
					:key="tab.key"
					class="tab-chip"
					:class="{ 'tab-chip-active': activeGraphView === tab.key }"
					@tap="activeGraphView = tab.key"
				>
					{{ tab.label }}
				</view>
			</view>

			<view v-if="activeGraphView === 'network'" class="content-card">
				<view class="section-head">
					<view class="section-title">关系网络</view>
					<view class="section-desc">重点展示“当前文物与谁有关、因为什么有关”，适合答辩时解释系统的可解释推荐能力。</view>
				</view>

				<view class="network-shell">
					<view class="center-node">
						<view class="center-node-title">{{ exhibit.name || pageName || '当前文物' }}</view>
						<view v-if="heroMeta" class="center-node-meta">{{ heroMeta }}</view>
						<view class="center-node-text">作为当前讲解核心，系统围绕它展开主题、工艺、材料和时代的多维关联。</view>
					</view>

					<view v-if="networkPreviewNodes.length" class="orbit-grid">
						<view
							v-for="(item, index) in networkPreviewNodes"
							:key="item.id || index"
							class="orbit-card"
							@tap="goRelatedDetail(item)"
						>
							<view class="orbit-title">{{ item.name }}</view>
							<view v-if="relationTypeLabel(item.relation_type)" class="orbit-type">{{ relationTypeLabel(item.relation_type) }}</view>
						</view>
					</view>
				</view>

				<view v-if="graphRelationFilterTabs.length" class="filter-row">
					<view
						v-for="tab in graphRelationFilterTabs"
						:key="tab.type"
						class="filter-chip"
						:class="{ 'filter-chip-active': activeRelationFilter === tab.type }"
						@tap="activeRelationFilter = tab.type"
					>
						{{ tab.label }}
						<text class="filter-count">{{ tab.count }}</text>
					</view>
				</view>

				<view v-if="filteredGraphNodes.length" class="node-list">
					<view v-for="(item, index) in filteredGraphNodes" :key="item.id || index" class="node-card" @tap="goRelatedDetail(item)">
						<view class="node-top">
							<view class="node-title">{{ item.name }}</view>
							<view v-if="relationTypeLabel(item.relation_type)" class="node-type">{{ relationTypeLabel(item.relation_type) }}</view>
						</view>
						<view v-if="buildGraphNodeMeta(item)" class="node-meta">{{ buildGraphNodeMeta(item) }}</view>
						<view class="node-text">{{ safeText(item.relation_summary) || safeText(item.short_intro) || '点击查看该节点对应的文物详情。' }}</view>
						<view v-if="item.strength_score !== null && item.strength_score !== undefined" class="strength-row">
							<view class="strength-label">关联强度</view>
							<view class="strength-track">
								<view class="strength-fill" :style="{ width: getStrengthWidth(item.strength_score) }"></view>
							</view>
						</view>
					</view>
				</view>
				<view v-else class="state-card inner-state-card">
					<view class="state-text">当前筛选下暂无可展示的关联节点。</view>
				</view>
			</view>

			<view v-else-if="activeGraphView === 'timeline'" class="content-card">
				<view class="section-head">
					<view class="section-title">时间线视图</view>
					<view class="section-desc">把当前文物重新放回历史顺序中看，能帮助用户从“孤立知识点”转向“完整叙事线”。</view>
				</view>

				<view v-if="graphTimelineItems.length" class="timeline-list">
					<view v-for="(item, index) in graphTimelineItems" :key="item.id || index" class="timeline-item">
						<view class="timeline-line"></view>
						<view class="timeline-card" :class="{ 'timeline-card-active': item.is_center }" @tap="item.is_center ? null : goRelatedDetail(item)">
							<view class="timeline-top">
								<view class="timeline-title">{{ item.name }}</view>
								<view v-if="item.time_label" class="timeline-badge">{{ item.time_label }}</view>
							</view>
							<view v-if="item.subtitle" class="timeline-subtitle">{{ item.subtitle }}</view>
							<view v-if="item.summary" class="timeline-text">{{ item.summary }}</view>
						</view>
					</view>
				</view>
				<view v-else class="state-card inner-state-card">
					<view class="state-text">暂未整理出时间线内容。</view>
				</view>
			</view>

			<view v-else-if="activeGraphView === 'craft'" class="content-card">
				<view class="section-head">
					<view class="section-title">工艺视图</view>
					<view class="section-desc">围绕材质、工艺、器型和用途组织对照关系，用于解释系统如何进行结构化知识拆解。</view>
				</view>

				<view v-if="graphCraftSections.length" class="craft-list">
					<view v-for="section in graphCraftSections" :key="section.key" class="craft-card">
						<view class="craft-title">{{ section.title }}</view>
						<view v-if="section.subtitle" class="craft-subtitle">{{ section.subtitle }}</view>
						<view v-if="section.description" class="craft-text">{{ section.description }}</view>

						<view v-if="section.tags && section.tags.length" class="tag-list">
							<view v-for="(tag, tagIndex) in section.tags" :key="`${section.key}-${tagIndex}`" class="tag">{{ tag }}</view>
						</view>

						<view v-if="section.related_nodes && section.related_nodes.length" class="craft-node-list">
							<view v-for="item in section.related_nodes" :key="`${section.key}-${item.id}`" class="craft-node" @tap="goRelatedDetail(item)">
								<view class="craft-node-title">{{ item.name }}</view>
								<view v-if="buildGraphNodeMeta(item)" class="craft-node-meta">{{ buildGraphNodeMeta(item) }}</view>
							</view>
						</view>
					</view>
				</view>
				<view v-else class="state-card inner-state-card">
					<view class="state-text">暂未整理出工艺视图内容。</view>
				</view>
			</view>

			<view v-if="errorText" class="state-card error-card">
				<view class="state-text">{{ errorText }}</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getExhibitDetail, getExhibitAssets, getExhibitGraph } from '../../api/exhibit'

const loading = ref(true)
const exhibitId = ref('')
const pageName = ref('')
const exhibit = ref({})
const assetData = ref({})
const graphData = ref({})
const errorText = ref('')
const activeGraphView = ref('network')
const activeRelationFilter = ref('all')

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

const graphSummaryText = computed(() => safeText(graphData.value?.graph_summary) || safeText(assetData.value?.graph_summary))
const heroMeta = computed(() => [safeText(exhibit.value?.hall?.name), safeText(exhibit.value?.dynasty) || safeText(exhibit.value?.era), safeText(exhibit.value?.category)].filter(Boolean).join(' · '))
const graphNodes = computed(() => Array.isArray(graphData.value?.related_nodes) ? uniqueById(graphData.value.related_nodes) : [])
const networkPreviewNodes = computed(() => graphNodes.value.slice(0, 6))

const relationTypeLabel = (relationType) => {
	const labelMap = {
		same_theme: '同主题',
		same_craft: '同工艺',
		same_material: '同材质',
		same_hall: '同展区延伸',
		background_for: '背景补充',
		contrast: '对照观看',
		route_next: '路线下一站',
		thematic: '专题延展'
	}
	return labelMap[relationType] || safeText(relationType)
}

const relationTypeStats = computed(() => {
	const counter = {}
	graphNodes.value.forEach(item => {
		const type = safeText(item?.relation_type) || 'other'
		counter[type] = (counter[type] || 0) + 1
	})
	return Object.keys(counter).map(type => ({ type, label: relationTypeLabel(type) || '其他关联', count: counter[type] })).sort((a, b) => b.count - a.count)
})

const topRelationLabel = computed(() => relationTypeStats.value[0]?.label || '综合关联')
const graphRelationFilterTabs = computed(() => [{ type: 'all', label: '全部', count: graphNodes.value.length }].concat(relationTypeStats.value))
const filteredGraphNodes = computed(() => activeRelationFilter.value === 'all' ? graphNodes.value : graphNodes.value.filter(item => safeText(item?.relation_type) === activeRelationFilter.value))

const mergeTagValues = (...groups) => {
	const result = []
	const seen = new Set()
	groups.forEach(group => {
		(group || []).forEach(item => {
			const text = safeText(item)
			if (!text || seen.has(text)) return
			seen.add(text)
			result.push(text)
		})
	})
	return result
}

const timeRank = (item) => {
	const text = `${safeText(item?.dynasty)} ${safeText(item?.era)}`
	const rules = [['新石器', 0], ['夏', 1], ['商', 2], ['西周', 3], ['东周', 4], ['春秋', 5], ['战国', 6], ['秦', 7], ['西汉', 8], ['东汉', 9], ['汉', 10], ['三国', 11], ['晋', 12], ['南北朝', 13], ['隋', 14], ['唐', 15], ['宋', 16], ['元', 17], ['明', 18], ['清', 19], ['近代', 20]]
	for (const [keyword, rank] of rules) if (text.includes(keyword)) return rank
	return 999
}

const graphTimelineItems = computed(() => {
	if (Array.isArray(graphData.value?.timeline_nodes) && graphData.value.timeline_nodes.length) return graphData.value.timeline_nodes
	const centerNode = {
		id: exhibit.value?.id,
		name: exhibit.value?.name,
		era: exhibit.value?.era,
		dynasty: exhibit.value?.dynasty,
		category: exhibit.value?.category,
		short_intro: exhibit.value?.short_intro,
		is_center: true,
		time_label: safeText(exhibit.value?.dynasty) || safeText(exhibit.value?.era),
		subtitle: [safeText(exhibit.value?.era), safeText(exhibit.value?.category), '中心文物'].filter(Boolean).join(' · '),
		summary: safeText(exhibit.value?.short_intro)
	}
	return uniqueById([centerNode, ...graphNodes.value]).sort((a, b) => {
		const rankGap = timeRank(a) - timeRank(b)
		if (rankGap !== 0) return rankGap
		return Number(b?.strength_score || 0) - Number(a?.strength_score || 0)
	}).map(item => ({
		id: item.id,
		name: item.name,
		time_label: safeText(item.time_label) || safeText(item.dynasty) || safeText(item.era),
		subtitle: safeText(item.subtitle) || [safeText(item.era), safeText(item.category), item.is_center ? '中心文物' : relationTypeLabel(item.relation_type)].filter(Boolean).join(' · '),
		summary: safeText(item.summary) || safeText(item.relation_summary) || safeText(item.short_intro),
		is_center: !!item.is_center,
		relation_type: item.relation_type
	}))
})

const graphCraftSections = computed(() => {
	if (Array.isArray(graphData.value?.craft_sections) && graphData.value.craft_sections.length) return graphData.value.craft_sections
	const sameCraftNodes = graphNodes.value.filter(item => ['same_craft', 'same_material'].includes(safeText(item?.relation_type)))
	const contrastNodes = graphNodes.value.filter(item => ['contrast', 'background_for'].includes(safeText(item?.relation_type)))
	const sections = [{
		key: 'current',
		title: '当前文物的工艺指纹',
		subtitle: '先抓住材质、工艺、用途和器型',
		description: safeText(exhibit.value?.core_value) || safeText(exhibit.value?.short_intro),
		tags: mergeTagValues([safeText(exhibit.value?.material), safeText(exhibit.value?.craft), safeText(exhibit.value?.usage_desc), safeText(exhibit.value?.shape_desc)]),
		related_nodes: []
	}]
	if (sameCraftNodes.length) {
		sections.push({
			key: 'same_craft',
			title: '同工艺 / 同材质对照',
			subtitle: '适合解释相似工艺脉络',
			description: '把当前文物和这些对象放在一起看，更容易理解工艺层面的共性与延续。',
			tags: mergeTagValues(sameCraftNodes.map(item => safeText(item.material)).filter(Boolean), sameCraftNodes.map(item => safeText(item.craft)).filter(Boolean)).slice(0, 6),
			related_nodes: sameCraftNodes.slice(0, 3)
		})
	}
	if (contrastNodes.length) {
		sections.push({
			key: 'contrast',
			title: '用途与表达对照',
			subtitle: '适合讲解礼器、兵器和生活器的差异',
			description: '这些对象的价值不一定在“相像”，而在“对照后更容易看懂”。',
			tags: mergeTagValues(contrastNodes.map(item => safeText(item.category)).filter(Boolean), contrastNodes.map(item => safeText(item.usage_desc)).filter(Boolean)).slice(0, 6),
			related_nodes: contrastNodes.slice(0, 3)
		})
	}
	return sections
})

const graphViewTabs = computed(() => {
	const tabs = []
	if (graphNodes.value.length || exhibit.value?.id) tabs.push({ key: 'network', label: '关系网络' })
	if (graphTimelineItems.value.length) tabs.push({ key: 'timeline', label: '时间线视图' })
	if (graphCraftSections.value.length) tabs.push({ key: 'craft', label: '工艺视图' })
	return tabs
})

const buildGraphNodeMeta = (item) => [safeText(item?.era), safeText(item?.dynasty), safeText(item?.category), safeText(item?.hall_name)].filter(Boolean).join(' · ')
const getStrengthWidth = (value) => `${Math.max(12, Math.min(100, Math.round(Number(value || 0) * 100)))}%`

const goRelatedDetail = (item) => {
	if (!item?.id) return
	uni.navigateTo({ url: `/pages/exhibit/detail?id=${item.id}&name=${encodeURIComponent(item.name || '')}` })
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
		const [detailRes, assetRes, graphRes] = await Promise.all([
			getExhibitDetail(exhibitId.value),
			getExhibitAssets(exhibitId.value),
			getExhibitGraph(exhibitId.value)
		])
		exhibit.value = detailRes || {}
		assetData.value = assetRes || {}
		graphData.value = graphRes || {}
	} catch (error) {
		console.error('知识图谱获取失败：', error)
		errorText.value = error?.message || '知识图谱加载失败'
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
	--text: #2f241d;
	--muted: #6d6258;
	--brand: #6e8b78;
	--brand-deep: #496756;
	--accent: #b98b4d;
	--panel: rgba(255, 251, 246, 0.96);
	--shadow: 0 24rpx 56rpx rgba(59, 43, 27, 0.08);
	min-height: 100vh;
	padding: 30rpx 28rpx 40rpx;
	background:
		radial-gradient(circle at 100% 0, rgba(110, 139, 120, 0.14), transparent 24%),
		linear-gradient(180deg, #f7f1e7 0%, #efe5d8 100%);
	box-sizing: border-box;
}

.hero-card,
.content-card,
.state-card {
	background: var(--panel);
	border-radius: 34rpx;
	padding: 32rpx;
	box-shadow: var(--shadow);
	border: 1rpx solid rgba(255, 255, 255, 0.5);
	margin-bottom: 24rpx;
}

.state-text {
	font-size: 28rpx;
	line-height: 1.8;
	text-align: center;
	color: var(--muted);
}

.hero-badge,
.tab-chip,
.filter-chip,
.node-type,
.timeline-badge,
.orbit-type {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 8rpx 18rpx;
	border-radius: 999rpx;
	font-size: 22rpx;
	line-height: 1.3;
}

.hero-badge {
	background: rgba(110, 139, 120, 0.14);
	color: var(--brand-deep);
}

.hero-title,
.section-title,
.center-node-title,
.orbit-title,
.node-title,
.timeline-title,
.craft-title,
.craft-node-title {
	color: var(--text);
	font-family: 'STSong', 'Songti SC', serif;
}

.hero-title {
	margin-top: 18rpx;
	font-size: 50rpx;
	line-height: 1.2;
	font-weight: 700;
}

.hero-meta,
.hero-summary,
.section-desc,
.center-node-meta,
.center-node-text,
.node-meta,
.node-text,
.timeline-subtitle,
.timeline-text,
.craft-subtitle,
.craft-text,
.craft-node-meta {
	font-size: 25rpx;
	line-height: 1.82;
	color: var(--muted);
}

.hero-meta {
	margin-top: 12rpx;
}

.hero-summary {
	margin-top: 18rpx;
}

.hero-stats {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 24rpx;
}

.hero-stat-card {
	padding: 22rpx 18rpx;
	border-radius: 24rpx;
	background: rgba(255, 255, 255, 0.76);
	border: 1rpx solid rgba(185, 139, 77, 0.08);
	text-align: center;
}

.hero-stat-label {
	font-size: 22rpx;
	color: #8a7f74;
	margin-bottom: 10rpx;
}

.hero-stat-value {
	font-size: 28rpx;
	line-height: 1.4;
	font-weight: 700;
	color: var(--brand-deep);
}

.tab-row,
.filter-row {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
	margin-bottom: 22rpx;
}

.tab-chip,
.filter-chip {
	background: rgba(47, 36, 29, 0.06);
	color: #665b51;
}

.tab-chip-active,
.filter-chip-active {
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
}

.filter-count {
	margin-left: 8rpx;
	font-size: 22rpx;
}

.section-head {
	margin-bottom: 18rpx;
}

.section-title {
	font-size: 38rpx;
	line-height: 1.35;
	font-weight: 700;
}

.section-desc {
	margin-top: 10rpx;
}

.network-shell {
	padding: 24rpx;
	border-radius: 30rpx;
	background: linear-gradient(180deg, rgba(255, 252, 248, 0.96), rgba(246, 240, 230, 0.96));
	margin-bottom: 22rpx;
}

.center-node {
	padding: 26rpx;
	border-radius: 28rpx;
	background: rgba(255, 255, 255, 0.84);
	border: 1rpx solid rgba(110, 139, 120, 0.12);
	box-shadow: 0 18rpx 40rpx rgba(73, 103, 86, 0.08);
}

.center-node-title {
	font-size: 34rpx;
	line-height: 1.35;
	font-weight: 700;
}

.center-node-meta,
.center-node-text {
	margin-top: 10rpx;
}

.orbit-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 18rpx;
}

.orbit-card,
.node-card,
.timeline-card,
.craft-card,
.craft-node {
	padding: 22rpx;
	border-radius: 26rpx;
	background: rgba(255, 255, 255, 0.76);
	border: 1rpx solid rgba(185, 139, 77, 0.08);
}

.orbit-title,
.node-title,
.timeline-title,
.craft-title,
.craft-node-title {
	font-size: 30rpx;
	line-height: 1.4;
	font-weight: 700;
}

.orbit-type,
.node-type,
.timeline-badge {
	background: rgba(185, 139, 77, 0.14);
	color: #8d6834;
}

.orbit-type {
	margin-top: 12rpx;
}

.node-list,
.craft-list,
.timeline-list {
	display: flex;
	flex-direction: column;
	gap: 18rpx;
}

.node-top,
.timeline-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16rpx;
}

.node-meta,
.node-text,
.timeline-subtitle,
.timeline-text,
.craft-subtitle,
.craft-text,
.craft-node-meta {
	margin-top: 10rpx;
}

.strength-row {
	margin-top: 14rpx;
}

.strength-label {
	font-size: 22rpx;
	color: #8a7f74;
	margin-bottom: 8rpx;
}

.strength-track {
	height: 10rpx;
	border-radius: 999rpx;
	background: rgba(185, 139, 77, 0.16);
	overflow: hidden;
}

.strength-fill {
	height: 100%;
	border-radius: 999rpx;
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
}

.timeline-item {
	display: flex;
	gap: 18rpx;
}

.timeline-line {
	width: 8rpx;
	border-radius: 999rpx;
	background: rgba(110, 139, 120, 0.24);
	flex-shrink: 0;
}

.timeline-card {
	flex: 1;
}

.timeline-card-active {
	background: rgba(110, 139, 120, 0.08);
	border-color: rgba(110, 139, 120, 0.2);
}

.tag-list {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 14rpx;
}

.tag {
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	background: rgba(110, 139, 120, 0.12);
	color: var(--brand-deep);
	font-size: 22rpx;
	line-height: 1.3;
}

.craft-node-list {
	display: flex;
	flex-direction: column;
	gap: 14rpx;
	margin-top: 16rpx;
}

.inner-state-card {
	margin-bottom: 0;
	box-shadow: none;
}

.error-card {
	border: 1rpx solid rgba(188, 92, 58, 0.18);
}

@media screen and (max-width: 640px) {
	.hero-stats,
	.orbit-grid {
		grid-template-columns: 1fr;
	}
}
</style>
