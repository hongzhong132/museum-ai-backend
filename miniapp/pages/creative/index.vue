<!-- miniapp/pages/creative/index.vue -->
<template>
	<view class="page">
		<view class="summary-card">
			<view class="summary-badge">AI 文创共创</view>
			<view class="summary-title">生成你的专属观展海报</view>
			<view class="summary-text">画面以文物主体为主，文字仅做轻量点缀，不遮挡主体。</view>
		</view>

		<view class="editor-card">
			<view class="editor-section">
				<view class="editor-label">海报风格</view>
				<view class="style-grid">
					<view
						v-for="item in styleOptions"
						:key="item"
						class="style-card"
						:class="{ 'style-card-active': form.style_mode === item }"
						@tap="form.style_mode = item"
					>
						<view class="style-title">{{ item }}</view>
						<view class="style-short">{{ styleMetaMap[item].short }}</view>
					</view>
				</view>
			</view>

			<view v-if="featuredExhibits.length" class="editor-section">
				<view class="editor-label">选择海报主角</view>
				<view class="exhibit-grid">
					<view
						v-for="item in featuredExhibits"
						:key="item.id"
						class="exhibit-card"
						:class="{ 'exhibit-card-active': form.exhibit_ids.includes(item.id) }"
						@tap="toggleExhibit(item.id)"
					>
						<view class="exhibit-card-title">{{ item.name }}</view>
						<view class="exhibit-card-meta">{{ buildExhibitMeta(item) }}</view>
					</view>
				</view>
				<view class="helper-text">最多选择 3 件重点文物，系统优先使用第一件作为主视觉。</view>
			</view>

			<view class="editor-section two-col">
				<view class="field-item">
					<view class="editor-label">署名</view>
					<input class="input" v-model="form.visitor_name" placeholder="例如：楚韵知博体验者" />
				</view>
				<view class="field-item">
					<view class="editor-label">参观日期</view>
					<input class="input" v-model="form.visit_date" placeholder="例如：2026-04-18" />
				</view>
			</view>

			<view class="editor-section">
				<view class="editor-label">简短寄语</view>
				<textarea
					class="textarea"
					v-model="form.message"
					placeholder="例如：希望把这次观展的楚文化震撼与青铜礼乐之美，沉淀成一张值得保存的海报。"
				></textarea>
				<view class="quick-row">
					<view v-for="item in messagePresets" :key="item" class="quick-chip" @tap="form.message = item">{{ item }}</view>
				</view>
			</view>
		</view>

		<button class="primary-btn" :disabled="loading" @tap="handleGenerate">
			{{ loading ? 'AI 正在生成海报...' : '生成专属纪念海报' }}
		</button>

		<view class="poster-card">
			<view class="poster-head">
				<view class="poster-head-title">海报实时预览</view>
				<view class="poster-status">{{ result ? '已生成' : '预览' }}</view>
			</view>

			<view class="poster-stage">
				<view class="poster-art" :style="posterArtStyle">
					<view class="poster-dim"></view>

					<view class="poster-topline">
						<view class="poster-chip">湖北省博物馆</view>
						<view v-if="mainExhibitName" class="poster-chip poster-chip-accent">{{ mainExhibitName }}</view>
					</view>

					<view v-if="posterBriefText" class="poster-note">
						{{ posterBriefText }}
					</view>

					<view v-if="signatureText" class="poster-signature">
						<view v-if="safeText(posterData.visitor_name)" class="poster-signature-name">{{ posterData.visitor_name }}</view>
						<view v-if="safeText(posterData.visit_date)" class="poster-signature-date">{{ posterData.visit_date }}</view>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { createCreativePoster } from '../../api/creative'

const loading = ref(false)
const result = ref(null)
const routeCache = ref({})
const featuredExhibits = ref([])

const styleOptions = ['楚风雅韵', '青铜史诗', '礼乐庄重']
const messagePresets = [
	'希望把这次观展中的楚文化震撼与青铜礼乐之美，沉淀成一张值得保存的海报。',
	'愿这次博物馆之旅既有知识收获，也留下属于自己的文化纪念。',
	'希望画面以文物本身为主，只保留克制、轻量的文字点缀。'
]

const styleMetaMap = {
	楚风雅韵: {
		short: '青玉清雅',
		fallback: 'linear-gradient(180deg, #d9e6df 0%, #a8c0b2 40%, #6f8f80 100%)',
		border: '#9db8aa'
	},
	青铜史诗: {
		short: '鎏金铜影',
		fallback: 'linear-gradient(180deg, #f0d49f 0%, #c58f50 42%, #754927 100%)',
		border: '#d4ab74'
	},
	礼乐庄重: {
		short: '玄黑礼制',
		fallback: 'linear-gradient(180deg, #2d2424 0%, #5b272c 44%, #121114 100%)',
		border: '#76434a'
	}
}

const mockRouteCache = {
	route_title: '楚风青铜寻脉路线',
	route_theme: '楚文化与青铜礼乐',
	route_summary: '以楚文化和青铜礼器为主线的示范路线。',
	featured_exhibits: [
		{ id: 'demo-1', name: '曾侯乙编钟', dynasty: '战国', category: '青铜礼器', image_url: '' },
		{ id: 'demo-2', name: '越王勾践剑', dynasty: '春秋', category: '兵器', image_url: '' },
		{ id: 'demo-3', name: '虎座鸟架鼓', dynasty: '战国', category: '礼乐器', image_url: '' }
	]
}

const form = reactive({
	style_mode: '楚风雅韵',
	visitor_name: '',
	visit_date: '',
	message: '',
	exhibit_ids: []
})

const safeText = (value) => {
	if (value === null || value === undefined) return ''
	return String(value).trim()
}

const clampText = (value, max = 46) => {
	const text = safeText(value)
	if (!text) return ''
	return text.length > max ? `${text.slice(0, max)}...` : text
}

const todayText = () => {
	const now = new Date()
	const year = now.getFullYear()
	const month = String(now.getMonth() + 1).padStart(2, '0')
	const day = String(now.getDate()).padStart(2, '0')
	return `${year}-${month}-${day}`
}

const selectedExhibits = computed(() => {
	const activeIds = Array.isArray(form.exhibit_ids) ? form.exhibit_ids : []
	return featuredExhibits.value.filter(item => activeIds.includes(item.id))
})

const currentStyleMeta = computed(() => styleMetaMap[form.style_mode] || styleMetaMap['楚风雅韵'])

const previewPosterData = computed(() => {
	const mainExhibit = selectedExhibits.value[0] || featuredExhibits.value[0] || null
	const routeTheme = safeText(routeCache.value?.route_theme)
	return {
		title: safeText(mainExhibit?.name) || routeTheme || '楚韵知博',
		subtitle: routeTheme,
		commemorative_text: '',
		style_mode: form.style_mode,
		visitor_name: safeText(form.visitor_name),
		visit_date: safeText(form.visit_date),
		poster_image_url: '',
		fallback_cover_image_url: safeText(mainExhibit?.image_url)
	}
})

const posterData = computed(() => result.value || previewPosterData.value)

const posterArtStyle = computed(() => {
	const image = safeText(posterData.value?.poster_image_url) || safeText(posterData.value?.fallback_cover_image_url)
	const fallback = currentStyleMeta.value.fallback
	const border = currentStyleMeta.value.border
	if (image) {
		return {
			backgroundImage: `url(${image})`,
			borderColor: border
		}
	}
	return {
		background: fallback,
		borderColor: border
	}
})

const mainExhibitName = computed(() => {
	const mainExhibit = selectedExhibits.value[0] || featuredExhibits.value[0] || null
	return safeText(mainExhibit?.name)
})

const posterBriefText = computed(() => {
	return clampText(
		safeText(posterData.value?.commemorative_text) ||
			safeText(form.message) ||
			safeText(routeCache.value?.route_theme)
	)
})

const signatureText = computed(() => {
	return safeText(posterData.value?.visitor_name) || safeText(posterData.value?.visit_date)
})

const buildExhibitMeta = (item) => {
	return [safeText(item?.dynasty), safeText(item?.category)].filter(Boolean).join(' · ')
}

const fillRouteCache = () => {
	const cache = uni.getStorageSync('routeResult')
	const finalCache = cache || mockRouteCache
	routeCache.value = finalCache
	featuredExhibits.value = Array.isArray(finalCache.featured_exhibits) ? finalCache.featured_exhibits.slice(0, 6) : []
	form.exhibit_ids = featuredExhibits.value.slice(0, 3).map(item => item.id).filter(Boolean)
}

const toggleExhibit = (id) => {
	if (!id) return
	if (form.exhibit_ids.includes(id)) {
		form.exhibit_ids = form.exhibit_ids.filter(item => item !== id)
		return
	}
	if (form.exhibit_ids.length >= 3) {
		uni.showToast({ title: '最多选择 3 件文物', icon: 'none' })
		return
	}
	form.exhibit_ids = [...form.exhibit_ids, id]
}

const handleGenerate = async () => {
	if (!form.exhibit_ids.length) {
		uni.showToast({ title: '请至少选择 1 件文物', icon: 'none' })
		return
	}
	loading.value = true
	try {
		const payload = {
			route_title: routeCache.value?.route_title || '',
			route_theme: routeCache.value?.route_theme || '',
			route_summary: routeCache.value?.route_summary || '',
			exhibit_ids: form.exhibit_ids,
			visitor_name: form.visitor_name,
			visit_date: form.visit_date,
			message: form.message,
			style_mode: form.style_mode
		}
		result.value = await createCreativePoster(payload)
	} catch (error) {
		console.error('文创生成失败：', error)
		uni.showToast({
			title: error?.data?.detail || error?.message || '文创生成失败',
			icon: 'none',
			duration: 3000
		})
	} finally {
		loading.value = false
	}
}

onLoad(() => {
	form.visit_date = todayText()
	fillRouteCache()
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
		radial-gradient(circle at 100% 0, rgba(185, 139, 77, 0.18), transparent 24%),
		linear-gradient(180deg, #f7f1e7 0%, #efe5d8 100%);
	box-sizing: border-box;
}

.summary-card,
.editor-card,
.poster-card {
	background: var(--panel);
	border-radius: 34rpx;
	padding: 32rpx;
	box-shadow: var(--shadow);
	border: 1rpx solid rgba(255, 255, 255, 0.52);
	margin-bottom: 24rpx;
}

.summary-badge,
.poster-status,
.poster-chip {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 8rpx 18rpx;
	border-radius: 999rpx;
	font-size: 22rpx;
	line-height: 1.3;
}

.summary-badge,
.poster-chip {
	background: rgba(110, 139, 120, 0.14);
	color: var(--brand-deep);
}

.summary-title,
.editor-label,
.poster-head-title {
	color: var(--text);
	font-family: 'STSong', 'Songti SC', serif;
}

.summary-title {
	margin-top: 18rpx;
	font-size: 46rpx;
	line-height: 1.2;
	font-weight: 700;
}

.summary-text,
.helper-text,
.exhibit-card-meta {
	font-size: 25rpx;
	line-height: 1.82;
	color: var(--muted);
}

.summary-text {
	margin-top: 14rpx;
}

.editor-section {
	margin-bottom: 28rpx;
}

.editor-section:last-child {
	margin-bottom: 0;
}

.editor-label {
	font-size: 28rpx;
	line-height: 1.45;
	font-weight: 700;
	margin-bottom: 14rpx;
}

.style-grid,
.exhibit-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16rpx;
}

.style-card,
.exhibit-card {
	padding: 22rpx;
	border-radius: 26rpx;
	background: rgba(255, 255, 255, 0.78);
	border: 1rpx solid rgba(185, 139, 77, 0.08);
}

.style-card-active,
.exhibit-card-active {
	border-color: rgba(110, 139, 120, 0.3);
	background: rgba(246, 251, 248, 0.96);
	box-shadow: 0 16rpx 34rpx rgba(73, 103, 86, 0.12);
}

.style-title,
.exhibit-card-title {
	font-size: 30rpx;
	line-height: 1.4;
	font-weight: 700;
	color: var(--text);
	font-family: 'STSong', 'Songti SC', serif;
}

.style-short {
	margin-top: 8rpx;
	font-size: 24rpx;
	color: #8d6834;
}

.two-col {
	display: flex;
	gap: 18rpx;
}

.field-item {
	flex: 1;
	min-width: 0;
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
	min-height: 170rpx;
	line-height: 1.7;
}

.quick-row {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 16rpx;
}

.quick-chip {
	padding: 10rpx 18rpx;
	border-radius: 999rpx;
	background: rgba(185, 139, 77, 0.12);
	color: #866438;
	font-size: 22rpx;
	line-height: 1.3;
}

.helper-text {
	margin-top: 12rpx;
}

.primary-btn {
	width: 100%;
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	border-radius: 999rpx;
	font-size: 28rpx;
	line-height: 1.4;
	border: none;
	box-shadow: 0 18rpx 32rpx rgba(73, 103, 86, 0.22);
	margin-bottom: 24rpx;
}

.primary-btn[disabled] {
	opacity: 0.72;
}

.poster-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20rpx;
	margin-bottom: 18rpx;
}

.poster-head-title {
	font-size: 38rpx;
	line-height: 1.35;
	font-weight: 700;
}

.poster-status {
	background: rgba(185, 139, 77, 0.14);
	color: #8d6834;
}

.poster-stage {
	width: 100%;
}

.poster-art {
	position: relative;
	min-height: 980rpx;
	border-radius: 32rpx;
	background-size: cover;
	background-position: center;
	background-repeat: no-repeat;
	border: 2rpx solid transparent;
	overflow: hidden;
}

.poster-dim {
	position: absolute;
	inset: 0;
	background: linear-gradient(180deg, rgba(16, 16, 16, 0.08) 0%, rgba(16, 16, 16, 0.2) 100%);
}

.poster-topline,
.poster-note,
.poster-signature {
	position: absolute;
	z-index: 2;
}

.poster-topline {
	top: 24rpx;
	left: 24rpx;
	right: 24rpx;
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 12rpx;
}

.poster-chip {
	background: rgba(255, 255, 255, 0.14);
	color: rgba(255, 248, 239, 0.82);
	backdrop-filter: blur(10rpx);
}

.poster-chip-accent {
	background: rgba(255, 248, 239, 0.14);
}

.poster-note {
	left: 24rpx;
	bottom: 26rpx;
	max-width: 56%;
	padding: 14rpx 16rpx;
	border-radius: 18rpx;
	background: rgba(255, 255, 255, 0.1);
	backdrop-filter: blur(10rpx);
	font-size: 22rpx;
	line-height: 1.6;
	color: rgba(255, 248, 239, 0.74);
}

.poster-signature {
	right: 24rpx;
	bottom: 24rpx;
	padding: 14rpx 16rpx;
	border-radius: 18rpx;
	background: rgba(255, 255, 255, 0.08);
	backdrop-filter: blur(10rpx);
	text-align: right;
	color: rgba(255, 248, 239, 0.68);
}

.poster-signature-name {
	font-size: 22rpx;
	line-height: 1.5;
}

.poster-signature-date {
	margin-top: 4rpx;
	font-size: 20rpx;
	line-height: 1.4;
}

button::after {
	border: none;
}

@media screen and (max-width: 640px) {
	.style-grid,
	.exhibit-grid {
		grid-template-columns: 1fr;
	}

	.two-col,
	.poster-head {
		flex-direction: column;
		align-items: stretch;
	}

	.poster-art {
		min-height: 760rpx;
	}

	.poster-note {
		max-width: 60%;
	}
}
</style>
