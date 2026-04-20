<template>
	<view class="page">
		<view class="page-glow glow-top"></view>
		<view class="page-glow glow-bottom"></view>

		<view class="hero-card">
			<view class="hero-badge">AI 博物馆导览</view>
			<view class="hero-title">楚韵导览</view>
			<view class="hero-subtitle">面向博物馆智慧导览场景的个性化观展小程序</view>
			<view class="hero-desc">
				围绕“路线规划、文物讲解、文创生成”三条主线，帮助观众快速形成有主题、有节奏、有记忆点的观展体验。
			</view>

			<view class="feature-grid">
				<view v-for="item in featureCards" :key="item.title" class="feature-card">
					<view class="feature-kicker">{{ item.kicker }}</view>
					<view class="feature-title">{{ item.title }}</view>
					<view class="feature-text">{{ item.text }}</view>
				</view>
			</view>

			<view class="hero-footer">
				<view class="hero-footer-label">竞赛展示定位</view>
				<view class="hero-footer-text">
					突出“人工智能应用 + 智能教育与文化”场景，让首页截图本身就能说明作品价值。
				</view>
			</view>
		</view>

		<view class="form-card">
			<view class="section-head">
				<view class="section-title">生成你的观展路线</view>
				<view class="section-desc">输入参观时间、兴趣偏好和观展目标，系统将自动生成更适合当前观众的推荐路线。</view>
			</view>

			<view class="form-item">
				<view class="label">参观时长（分钟）</view>
				<input class="input" type="number" v-model="form.duration" placeholder="例如：90" />
				<view class="quick-row">
					<view
						v-for="item in durationOptions"
						:key="item"
						class="quick-chip"
						:class="{ 'quick-chip-active': form.duration === String(item) }"
						@tap="form.duration = String(item)"
					>
						{{ item }} 分钟
					</view>
				</view>
			</view>

			<view class="form-item">
				<view class="label">兴趣方向</view>
				<input class="input" v-model="form.interests" placeholder="例如：楚文化、青铜器、礼乐文明" />
				<view class="quick-row">
					<view
						v-for="item in interestPresets"
						:key="item"
						class="quick-chip soft-chip"
						@tap="applyInterestPreset(item)"
					>
						{{ item }}
					</view>
				</view>
			</view>

			<view class="form-item">
				<view class="label">是否首次参观</view>
				<view class="toggle-row">
					<view
						class="toggle-chip"
						:class="{ 'toggle-chip-active': form.is_first_visit }"
						@tap="form.is_first_visit = true"
					>
						首次来馆
					</view>
					<view
						class="toggle-chip"
						:class="{ 'toggle-chip-active': !form.is_first_visit }"
						@tap="form.is_first_visit = false"
					>
						有过参观经验
					</view>
				</view>
			</view>

			<view class="form-item">
				<view class="label">观展目标</view>
				<textarea
					class="textarea"
					v-model="form.goal"
					placeholder="例如：希望优先看最具代表性的文物，路线清晰、不绕路，适合答辩展示和文化体验"
				/>
				<view class="goal-list">
					<view
						v-for="item in goalPresets"
						:key="item"
						class="goal-card"
						@tap="form.goal = item"
					>
						{{ item }}
					</view>
				</view>
			</view>
		</view>

		<view class="cta-card">
			<button class="primary-btn" :disabled="loading" @tap="handleGenerate">
				{{ loading ? 'AI 正在生成路线...' : '生成个性化路线' }}
			</button>
			<button class="secondary-btn" @tap="goMockRoute">查看比赛展示示例</button>
			<view class="cta-tip">建议截图：首页封面 + 示例路线页，可直接用于作品简介、系统展示和填表材料。</view>
		</view>
	</view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { generateRoute } from '../../api/route'

const loading = ref(false)

const durationOptions = [60, 90, 120, 150]
const interestPresets = ['楚文化', '青铜器', '礼乐文明', '精品文物', '历史脉络']
const goalPresets = [
	'希望优先看最具代表性的文物，路线清晰，适合首次参观快速了解馆藏亮点。',
	'希望围绕楚文化和青铜礼器展开参观，兼顾知识性和视觉冲击力。',
	'希望时间安排紧凑一些，优先看重点展区和适合讲解展示的核心文物。'
]

const featureCards = [
	{
		kicker: '01',
		title: '智能路线规划',
		text: '根据观众时长、兴趣和目标自动生成更合适的观展顺序。'
	},
	{
		kicker: '02',
		title: '文物深度讲解',
		text: '围绕重点文物提供可解释的知识导览和延伸理解入口。'
	},
	{
		kicker: '03',
		title: 'AI 文创生成',
		text: '基于路线主题和重点文物，生成可用于传播和纪念的海报。'
	}
]

const form = reactive({
	duration: '90',
	interests: '楚文化、青铜器、礼乐文明',
	is_first_visit: true,
	goal: '希望优先看最具代表性的文物，路线清晰，适合首次参观快速了解馆藏亮点。'
})

const mockRouteData = {
	route_title: '楚风青铜寻脉路线',
	route_theme: '楚文化与青铜礼乐',
	route_summary:
		'这是一条适合首次参观的示范路线，重点围绕楚文化代表性展区与青铜礼器展开，兼顾代表性、叙事性与参观节奏。',
	target_fit_reason:
		'根据“首次参观 + 90 分钟 + 想看馆藏亮点”的目标，优先选取辨识度高、适合讲解展示且故事线完整的展区与文物。',
	order_logic:
		'先从整体历史脉络入手，再进入楚文化核心展区，最后收束到礼乐与工艺代表文物，便于形成完整记忆。',
	source: 'demo',
	selected_halls: [
		{ id: 'hall-1', name: '楚文化展区', recommended_duration_min: 30 },
		{ id: 'hall-2', name: '青铜器展区', recommended_duration_min: 35 },
		{ id: 'hall-3', name: '礼乐文明展区', recommended_duration_min: 25 }
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
			symbolism: '体现楚地礼乐文明与青铜工艺高度成就',
			style_tags: '礼乐、庄重、恢弘',
			short_intro: '以恢弘的乐器体系和精密音律结构，成为认识楚文化的重要入口。'
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
			symbolism: '象征高超冶铸技术与历史传奇',
			style_tags: '锋锐、传奇、工艺',
			short_intro: '兼具历史传奇与工艺价值，是观众最容易建立记忆点的代表文物之一。'
		},
		{
			id: 'demo-3',
			name: '虎座鸟架鼓',
			era: '战国',
			dynasty: '战国中期',
			category: '礼乐器',
			material: '木胎彩绘',
			craft: '彩绘漆艺',
			usage_desc: '礼仪陈设',
			symbolism: '体现楚文化浪漫奇诡的审美气质',
			style_tags: '浪漫、奇诡、楚风',
			short_intro: '造型强烈、视觉辨识度高，适合用于路线讲解和作品展示截图。'
		}
	],
	stop_guides: [
		{
			hall_id: 'hall-1',
			hall_name: '楚文化展区',
			hall_theme: '先建立楚文化整体印象',
			time_budget_min: 30,
			focus: '从区域文明、器物特征和审美气质入手快速建立背景知识。',
			why_here: '作为路线起点，先理解楚文化的整体面貌，后续看青铜礼器会更容易进入状态。',
			key_exhibits: ['虎座鸟架鼓', '彩绘漆木器'],
			transition_to_next: '看完文化背景后，进入更具代表性的青铜器展区，体验工艺与礼制。'
		},
		{
			hall_id: 'hall-2',
			hall_name: '青铜器展区',
			hall_theme: '观察青铜工艺与权力象征',
			time_budget_min: 35,
			focus: '重点理解青铜礼器在礼制、工艺和权力表达中的作用。',
			why_here: '这是最能体现馆藏代表性和观众“值回票价”感受的核心区域。',
			key_exhibits: ['曾侯乙编钟', '越王勾践剑'],
			transition_to_next: '从工艺高峰过渡到礼乐文明，让路线叙事更完整。'
		},
		{
			hall_id: 'hall-3',
			hall_name: '礼乐文明展区',
			hall_theme: '收束为礼乐叙事',
			time_budget_min: 25,
			focus: '用礼乐文明总结楚地器物背后的社会秩序与文化表达。',
			why_here: '作为最后一站，有助于把前面看到的文物重新串成一条更有层次的文化线索。',
			key_exhibits: ['礼乐制度相关展项'],
			transition_to_next: '完成整条路线后，可继续进入文创共创页面生成纪念海报。'
		}
	],
	skip_strategy: '若现场时间不足，可适当缩短第三展区停留时间，但建议保留曾侯乙编钟与越王勾践剑两处重点讲解。',
	route_closing: '这条路线适合比赛展示、课堂讲解和首次参观体验，能够在有限时间内兼顾知识性、代表性与观感。'
}

const applyInterestPreset = (value) => {
	const current = String(form.interests || '').trim()
	if (!current) {
		form.interests = value
		return
	}
	if (current.includes(value)) return
	form.interests = `${current}、${value}`
}

const handleGenerate = async () => {
	if (!form.duration) {
		uni.showToast({
			title: '请先填写参观时长',
			icon: 'none'
		})
		return
	}

	loading.value = true

	try {
		const payload = {
			available_minutes: Number(form.duration),
			interest: form.interests,
			first_visit: form.is_first_visit,
			visit_goal: form.goal
		}

		const res = await generateRoute(payload)
		uni.setStorageSync('routeResult', res)

		uni.navigateTo({
			url: '/pages/route/result'
		})
	} catch (error) {
		console.error('生成路线失败：', error)
		console.error('后端返回详情：', error?.data)

		uni.showToast({
			title: error?.data?.detail?.[0]?.msg || error?.data?.detail || '生成失败，请检查接口参数',
			icon: 'none',
			duration: 3000
		})
	} finally {
		loading.value = false
	}
}

const goMockRoute = () => {
	uni.setStorageSync('routeResult', mockRouteData)
	uni.navigateTo({
		url: '/pages/route/result'
	})
}
</script>

<style scoped>
.page {
	--bg: #f5efe5;
	--panel: rgba(255, 250, 244, 0.94);
	--panel-strong: #fffdf8;
	--line: rgba(118, 91, 61, 0.12);
	--text: #2f241d;
	--muted: #6f6459;
	--brand: #6e8b78;
	--brand-deep: #496756;
	--accent: #b98b4d;
	--accent-soft: rgba(185, 139, 77, 0.12);
	--shadow: 0 22rpx 50rpx rgba(59, 43, 27, 0.08);
	position: relative;
	min-height: 100vh;
	padding: 34rpx 28rpx 40rpx;
	background:
		radial-gradient(circle at top right, rgba(185, 139, 77, 0.18), transparent 28%),
		linear-gradient(180deg, #f7f1e7 0%, #f1e8db 100%);
	box-sizing: border-box;
	overflow: hidden;
}

.page-glow {
	position: absolute;
	border-radius: 50%;
	filter: blur(8rpx);
	pointer-events: none;
}

.glow-top {
	top: -80rpx;
	right: -40rpx;
	width: 260rpx;
	height: 260rpx;
	background: rgba(185, 139, 77, 0.16);
}

.glow-bottom {
	left: -90rpx;
	bottom: 120rpx;
	width: 240rpx;
	height: 240rpx;
	background: rgba(110, 139, 120, 0.12);
}

.hero-card,
.form-card,
.cta-card {
	position: relative;
	z-index: 1;
	background: var(--panel);
	backdrop-filter: blur(10rpx);
	border: 1rpx solid rgba(255, 255, 255, 0.5);
	border-radius: 34rpx;
	padding: 34rpx;
	box-shadow: var(--shadow);
	margin-bottom: 24rpx;
}

.hero-card::before {
	content: '';
	position: absolute;
	inset: 0;
	border-radius: 34rpx;
	background:
		linear-gradient(135deg, rgba(110, 139, 120, 0.12), transparent 36%),
		linear-gradient(315deg, rgba(185, 139, 77, 0.1), transparent 34%);
	pointer-events: none;
}

.hero-badge,
.feature-kicker,
.hero-footer-label {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 8rpx 18rpx;
	border-radius: 999rpx;
	font-size: 22rpx;
	letter-spacing: 1rpx;
}

.hero-badge {
	background: rgba(110, 139, 120, 0.14);
	color: var(--brand-deep);
	margin-bottom: 18rpx;
}

.hero-title {
	font-size: 60rpx;
	line-height: 1.12;
	font-weight: 700;
	color: var(--text);
	font-family: 'STSong', 'Songti SC', serif;
	letter-spacing: 2rpx;
}

.hero-subtitle {
	margin-top: 16rpx;
	font-size: 30rpx;
	line-height: 1.55;
	color: #4b4037;
	font-weight: 600;
}

.hero-desc,
.section-desc,
.cta-tip,
.hero-footer-text,
.feature-text {
	font-size: 25rpx;
	line-height: 1.82;
	color: var(--muted);
}

.hero-desc {
	margin-top: 16rpx;
	max-width: 640rpx;
}

.feature-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 28rpx;
}

.feature-card {
	padding: 22rpx 20rpx;
	border-radius: 24rpx;
	background: rgba(255, 255, 255, 0.66);
	border: 1rpx solid rgba(185, 139, 77, 0.1);
}

.feature-kicker {
	background: var(--accent-soft);
	color: #8d6834;
	margin-bottom: 14rpx;
	font-weight: 600;
}

.feature-title {
	font-size: 28rpx;
	line-height: 1.4;
	font-weight: 700;
	color: var(--text);
	margin-bottom: 10rpx;
}

.hero-footer {
	margin-top: 26rpx;
	padding-top: 24rpx;
	border-top: 1rpx solid var(--line);
}

.hero-footer-label {
	background: rgba(47, 36, 29, 0.06);
	color: #5b5047;
	margin-bottom: 12rpx;
}

.section-head {
	margin-bottom: 24rpx;
}

.section-title {
	font-size: 38rpx;
	line-height: 1.35;
	font-weight: 700;
	color: var(--text);
	font-family: 'STSong', 'Songti SC', serif;
}

.section-desc {
	margin-top: 10rpx;
}

.form-item {
	margin-bottom: 28rpx;
}

.form-item:last-child {
	margin-bottom: 0;
}

.label {
	font-size: 28rpx;
	line-height: 1.45;
	font-weight: 700;
	color: var(--text);
	margin-bottom: 14rpx;
}

.input,
.textarea {
	width: 100%;
	background: rgba(252, 248, 241, 0.96);
	border: 1rpx solid rgba(110, 139, 120, 0.14);
	border-radius: 22rpx;
	padding: 22rpx 24rpx;
	box-sizing: border-box;
	font-size: 28rpx;
	color: var(--text);
}

.textarea {
	min-height: 180rpx;
	line-height: 1.7;
}

.quick-row,
.toggle-row {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
	margin-top: 16rpx;
}

.quick-chip,
.toggle-chip {
	padding: 12rpx 22rpx;
	border-radius: 999rpx;
	background: rgba(47, 36, 29, 0.05);
	color: #665b51;
	font-size: 24rpx;
	line-height: 1.4;
}

.quick-chip-active,
.toggle-chip-active {
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	box-shadow: 0 12rpx 24rpx rgba(73, 103, 86, 0.18);
}

.soft-chip {
	background: rgba(185, 139, 77, 0.12);
	color: #866438;
}

.goal-list {
	display: flex;
	flex-direction: column;
	gap: 14rpx;
	margin-top: 18rpx;
}

.goal-card {
	padding: 20rpx 22rpx;
	border-radius: 22rpx;
	background: rgba(255, 252, 247, 0.92);
	border: 1rpx solid rgba(185, 139, 77, 0.12);
	font-size: 24rpx;
	line-height: 1.74;
	color: #6c6157;
}

.primary-btn,
.secondary-btn {
	width: 100%;
	border-radius: 999rpx;
	font-size: 28rpx;
	line-height: 1.4;
	border: none;
}

.primary-btn {
	background: linear-gradient(135deg, #6e8b78 0%, #496756 100%);
	color: #fffdf8;
	box-shadow: 0 18rpx 32rpx rgba(73, 103, 86, 0.22);
}

.secondary-btn {
	margin-top: 18rpx;
	background: linear-gradient(135deg, rgba(185, 139, 77, 0.14), rgba(185, 139, 77, 0.2));
	color: #7f5d33;
}

.primary-btn[disabled] {
	opacity: 0.72;
}

.cta-tip {
	margin-top: 16rpx;
	text-align: center;
}

button::after {
	border: none;
}

@media screen and (max-width: 640px) {
	.feature-grid {
		grid-template-columns: 1fr;
	}
}
</style>
