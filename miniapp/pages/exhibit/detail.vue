<template>
	<view class="page">
		<view v-if="loading" class="state-card">
			<view class="state-text">文物内容加载中...</view>
		</view>

		<view v-else>
			<view class="hero-card">
				<view class="hero-top">
					<view class="hero-badge">文物详情</view>
					<view v-if="hallText" class="hall-chip">{{ hallText }}</view>
				</view>

				<view class="hero-title">{{ exhibit.name || pageName || '未命名文物' }}</view>
				<view v-if="metaLine" class="hero-meta">{{ metaLine }}</view>

				<view v-if="displayCoverImage" class="hero-image-wrap">
					<image class="hero-image" :src="displayCoverImage" mode="aspectFill" @tap="previewImages(0)"></image>
				</view>

				<scroll-view v-if="previewImageList.length > 1" class="thumb-scroll" scroll-x>
					<view class="thumb-row">
						<image
							v-for="(item, index) in previewImageList"
							:key="`${item}-${index}`"
							class="thumb-image"
							:src="item"
							mode="aspectFill"
							@tap="previewImages(index)"
						></image>
					</view>
				</scroll-view>

				<view v-if="safeText(assetData.image_caption)" class="hero-caption">{{ assetData.image_caption }}</view>

				<view v-if="heroFactCards.length" class="hero-facts">
					<view v-for="item in heroFactCards" :key="item.label" class="hero-fact-card">
						<view class="hero-fact-label">{{ item.label }}</view>
						<view class="hero-fact-value">{{ item.value }}</view>
					</view>
				</view>
			</view>

			<view v-if="quickFactItems.length" class="content-card">
				<view class="section-title">基础信息</view>
				<view class="fact-grid">
					<view v-for="(item, index) in quickFactItems" :key="`fact-${index}`" class="fact-card">
						<view class="fact-label">{{ item.label }}</view>
						<view class="fact-value">{{ item.value }}</view>
					</view>
				</view>
			</view>

			<view v-if="highlightTags.length" class="content-card">
				<view class="section-title">文物亮点</view>
				<view class="tag-list">
					<view v-for="(tag, index) in highlightTags" :key="`highlight-${index}`" class="tag">{{ tag }}</view>
				</view>
			</view>

			<view v-if="aiExplainPending || hasAiExplain || aiExplainError" class="content-card">
				<view class="section-head">
					<view class="section-title">AI 导览讲解</view>
					<view v-if="aiExplainSourceText" class="source-chip">{{ aiExplainSourceText }}</view>
				</view>

				<view class="mode-panel">
					<view class="mode-row">
						<view
							v-for="item in explainModeOptions"
							:key="item.value"
							class="mode-chip"
							:class="{ 'mode-chip-active': explainMode === item.value }"
							@tap="changeExplainMode(item.value)"
						>
							{{ item.label }}
						</view>
					</view>
					<view class="mode-hint">{{ currentExplainModeHint }}</view>
				</view>

				<view v-if="aiExplainPending" class="ai-placeholder">
					AI 正在生成{{ currentExplainModeLabel }}讲解...
				</view>

				<view v-else-if="hasAiExplain">
					<view v-if="safeText(aiExplainData.intro)" class="text-block">{{ aiExplainData.intro }}</view>

					<view v-if="safeText(aiExplainData.first_impression)" class="ai-quote">
						{{ aiExplainData.first_impression }}
					</view>

					<view v-if="aiWatchPoints.length" class="ai-watch-list">
						<view v-for="(item, index) in aiWatchPoints" :key="`watch-${index}`" class="ai-watch-item">
							<view class="ai-watch-index">{{ String(index + 1).padStart(2, '0') }}</view>
							<view class="ai-watch-text">{{ item }}</view>
						</view>
					</view>

					<view v-if="aiInsightItems.length" class="ai-insight-grid">
						<view v-for="(item, index) in aiInsightItems" :key="`insight-${index}`" class="value-card ai-insight-card">
							<view class="value-title">{{ item.label }}</view>
							<view class="value-text">{{ item.value }}</view>
						</view>
					</view>

					<view v-if="safeText(aiExplainData.one_sentence_takeaway)" class="ai-takeaway">
						<view class="ai-takeaway-label">一句话带走</view>
						<view class="ai-takeaway-text">{{ aiExplainData.one_sentence_takeaway }}</view>
					</view>
				</view>

				<view v-else class="ai-placeholder">
					{{ aiExplainError || '暂未生成 AI 讲解' }}
				</view>
			</view>

			<view v-if="safeText(exhibit.short_intro) || safeText(exhibit.deep_intro) || valueItems.length" class="content-card">
				<view class="section-title">深入理解</view>
				<view v-if="safeText(exhibit.short_intro)" class="text-block">{{ exhibit.short_intro }}</view>
				<view v-if="safeText(exhibit.deep_intro)" class="text-block text-block-secondary">{{ exhibit.deep_intro }}</view>

				<view v-for="(item, index) in valueItems" :key="`value-${index}`" class="value-card">
					<view class="value-title">{{ item.label }}</view>
					<view class="value-text">{{ item.value }}</view>
				</view>
			</view>

			<view v-if="hasSpeechContent" class="content-card">
				<view class="section-title">语音讲解</view>

				<view class="audio-panel">
					<button class="audio-btn audio-btn-primary" :disabled="!hasSpeechContent" @tap="toggleSpeech">
						{{ speechPrimaryText }}
					</button>
					<button class="audio-btn audio-btn-secondary" :disabled="speechStatus === 'idle'" @tap="stopSpeech">
						停止播放
					</button>
				</view>

				<view class="rate-row">
					<view class="rate-label">播放速度</view>
					<view class="rate-list">
						<view
							v-for="rate in speechRateOptions"
							:key="`rate-${rate}`"
							class="rate-chip"
							:class="{ 'rate-chip-active': speechRate === rate }"
							@tap="changeSpeechRate(rate)"
						>
							{{ rate }}x
						</view>
					</view>
				</view>

				<view v-if="speechHintText" class="audio-hint">{{ speechHintText }}</view>
			</view>

			<view class="content-card">
				<view class="section-title">继续探索</view>
				<view class="explore-grid">
					<view class="explore-card" @tap="goGraphPage">
						<view class="explore-top">
							<view class="explore-badge">知识图谱</view>
							<view class="explore-count">{{ graphNodeCountText }}</view>
						</view>
						<view class="explore-title">查看关联知识</view>
						<view class="explore-text">继续查看当前文物的关系网络、时间线与工艺关联。</view>
					</view>

					<view class="explore-card" @tap="goRelatedPage">
						<view class="explore-top">
							<view class="explore-badge explore-badge-accent">相关文物</view>
							<view class="explore-count">{{ relatedCountText }}</view>
						</view>
						<view class="explore-title">延伸相似文物</view>
						<view class="explore-text">查看主题、材质、工艺或展区相关的延伸对象。</view>
					</view>
				</view>
			</view>

			<view v-if="errorText" class="state-card error-card">
				<view class="state-text">{{ errorText }}</view>
			</view>

			<button class="reload-btn" @tap="reloadPage">重新加载文物内容</button>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onHide, onUnload } from '@dcloudio/uni-app'
import { getExhibitDetail, getExhibitAssets, getExhibitGraph, explainExhibit } from '../../api/exhibit'

const loading = ref(true)
const exhibitId = ref('')
const pageName = ref('')
const exhibit = ref({})
const assetData = ref({})
const graphData = ref({})
const aiExplainData = ref({})
const aiExplainPending = ref(false)
const aiExplainError = ref('')
const errorText = ref('')

const explainMode = ref('normal')
const explainModeOptions = [
	{ value: 'normal', label: '普通讲解', hint: '适合大多数观众，兼顾信息量与阅读轻松度。' },
	{ value: 'deep', label: '深度讲解', hint: '更强调历史、工艺与文化背景，适合答辩和深入了解。' },
	{ value: 'child', label: '儿童讲解', hint: '语言更轻松易懂，更适合低龄观众或亲子导览。' }
]

const speechStatus = ref('idle')
const speechHintText = ref('')
const speechRate = ref(1)
const platformType = ref('unknown')
const speechRateOptions = [1, 1.25, 1.5]

let innerAudioContext = null
let currentUtterance = null
let h5SpeechSynthesis = null
let explainRequestSeed = 0

// #ifdef H5
h5SpeechSynthesis = window.speechSynthesis
// #endif

const safeText = (value) => {
	if (value === null || value === undefined) return ''
	return String(value).trim()
}

const splitTags = (value) => {
	if (!safeText(value)) return []
	return String(value)
		.split(/[，、；;|\n]+/)
		.map(item => item.trim())
		.filter(Boolean)
}

const uniqueStrings = (list) => [...new Set((list || []).filter(Boolean))]

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

const normalizeExplainPoint = (item) => {
	if (typeof item === 'string') return safeText(item)
	if (item && typeof item === 'object') {
		return safeText(item.text) || safeText(item.content) || safeText(item.label) || safeText(item.title)
	}
	return ''
}

const currentExplainMode = computed(() => {
	return explainModeOptions.find(item => item.value === explainMode.value) || explainModeOptions[0]
})

const currentExplainModeLabel = computed(() => currentExplainMode.value.label)
const currentExplainModeHint = computed(() => currentExplainMode.value.hint)

const hallText = computed(() => safeText(exhibit.value?.hall?.name) || safeText(exhibit.value?.hall_name) || '')

const metaLine = computed(() => {
	return [
		safeText(exhibit.value?.era),
		safeText(exhibit.value?.dynasty),
		safeText(exhibit.value?.category),
		safeText(exhibit.value?.sub_category)
	].filter(Boolean).join(' · ')
})

const displayCoverImage = computed(() => {
	return safeText(assetData.value?.cover_image_url) || safeText(exhibit.value?.image_url)
})

const detailImageUrls = computed(() => {
	const list = Array.isArray(assetData.value?.detail_image_urls) ? assetData.value.detail_image_urls : []
	return uniqueStrings([
		...list.map(item => safeText(item)),
		safeText(assetData.value?.detail_image_url_1),
		safeText(assetData.value?.detail_image_url_2)
	])
})

const previewImageList = computed(() => {
	return uniqueStrings([displayCoverImage.value, ...detailImageUrls.value].filter(Boolean))
})

const quickFactItems = computed(() => {
	const raw = [
		{ label: '朝代', value: safeText(exhibit.value?.dynasty) || safeText(exhibit.value?.era) },
		{ label: '类别', value: safeText(exhibit.value?.category) },
		{ label: '工艺', value: safeText(exhibit.value?.craft) },
		{ label: '材质', value: safeText(exhibit.value?.material) },
		{ label: '用途', value: safeText(exhibit.value?.usage_desc) },
		{ label: '所属展区', value: hallText.value }
	]
	return raw.filter(item => safeText(item.value))
})

const heroFactCards = computed(() => quickFactItems.value.slice(0, 3))

const highlightTags = computed(() => {
	return uniqueStrings([
		...splitTags(exhibit.value?.style_tags),
		...splitTags(exhibit.value?.pattern_elements),
		...splitTags(exhibit.value?.creative_keywords)
	]).slice(0, 10)
})

const valueItems = computed(() => {
	return [
		{ label: '历史价值', value: safeText(exhibit.value?.historical_value) },
		{ label: '艺术价值', value: safeText(exhibit.value?.art_value) },
		{ label: '文化价值', value: safeText(exhibit.value?.cultural_value) }
	].filter(item => safeText(item.value))
})

const aiWatchPoints = computed(() => {
	const raw = Array.isArray(aiExplainData.value?.core_watch_points) ? aiExplainData.value.core_watch_points : []
	return raw.map(normalizeExplainPoint).filter(Boolean).slice(0, 4)
})

const aiInsightItems = computed(() => {
	return [
		{ label: '为什么现在看', value: safeText(aiExplainData.value?.why_now) },
		{ label: '历史角色', value: safeText(aiExplainData.value?.historical_role) },
		{ label: '工艺价值', value: safeText(aiExplainData.value?.craft_value) },
		{ label: '路线关联', value: safeText(aiExplainData.value?.relation_to_route) },
		{ label: '对比提示', value: safeText(aiExplainData.value?.compare_hint) }
	].filter(item => safeText(item.value))
})

const aiExplainSourceText = computed(() => {
	if (aiExplainData.value?.source === 'llm') return 'AI 实时生成'
	if (aiExplainData.value?.source === 'template') return '智能模板生成'
	return ''
})

const hasAiExplain = computed(() => {
	return Boolean(
		safeText(aiExplainData.value?.intro) ||
		safeText(aiExplainData.value?.first_impression) ||
		safeText(aiExplainData.value?.one_sentence_takeaway) ||
		aiWatchPoints.value.length ||
		aiInsightItems.value.length
	)
})

const explainNarrationText = computed(() => {
	const parts = [
		safeText(aiExplainData.value?.intro),
		safeText(aiExplainData.value?.first_impression),
		...aiWatchPoints.value,
		safeText(aiExplainData.value?.why_now),
		safeText(aiExplainData.value?.one_sentence_takeaway)
	].filter(Boolean)
	return parts.join('。')
})

const relatedExhibits = computed(() => {
	const detailRelated = Array.isArray(exhibit.value?.related_exhibits) ? exhibit.value.related_exhibits : []
	const graphRelated = Array.isArray(graphData.value?.related_nodes) ? graphData.value.related_nodes : []
	return uniqueById([...detailRelated, ...graphRelated])
})

const graphNodeCountText = computed(() => {
	const count = Array.isArray(graphData.value?.related_nodes) ? graphData.value.related_nodes.length : 0
	return count ? `${count} 个节点` : '进入查看'
})

const relatedCountText = computed(() => {
	return relatedExhibits.value.length ? `${relatedExhibits.value.length} 件文物` : '进入查看'
})

const audioScriptText = computed(() => {
	return (
		explainNarrationText.value ||
		safeText(assetData.value?.audio_script) ||
		safeText(exhibit.value?.short_intro) ||
		safeText(exhibit.value?.deep_intro)
	)
})

const audioUrl = computed(() => {
	return safeText(assetData.value?.audio_url) || safeText(assetData.value?.audio_src) || safeText(assetData.value?.audio_file_url)
})

const hasSpeechContent = computed(() => !!audioScriptText.value)

const speechPrimaryText = computed(() => {
	if (!hasSpeechContent.value) return '暂无讲解内容'
	if (speechStatus.value === 'playing') return '暂停讲解'
	if (speechStatus.value === 'paused') return audioUrl.value ? '继续播放' : '继续朗读'
	if (audioUrl.value) return '播放讲解'
	if (platformType.value === 'h5') return '开始朗读'
	return '播放讲解'
})

const previewImages = (index = 0) => {
	if (!previewImageList.value.length) return
	uni.previewImage({
		urls: previewImageList.value,
		current: previewImageList.value[index] || previewImageList.value[0]
	})
}

const initInnerAudioContext = () => {
	if (innerAudioContext) return innerAudioContext
	innerAudioContext = uni.createInnerAudioContext()
	innerAudioContext.obeyMuteSwitch = false

	innerAudioContext.onPlay(() => {
		speechStatus.value = 'playing'
		speechHintText.value = audioUrl.value ? '正在播放讲解音频' : ''
	})
	innerAudioContext.onPause(() => {
		speechStatus.value = 'paused'
		speechHintText.value = '已暂停，可继续播放'
	})
	innerAudioContext.onStop(() => {
		speechStatus.value = 'idle'
		speechHintText.value = '已停止播放'
	})
	innerAudioContext.onEnded(() => {
		speechStatus.value = 'idle'
		speechHintText.value = '讲解播放完成'
	})
	innerAudioContext.onError(() => {
		speechStatus.value = 'idle'
		speechHintText.value = '音频播放失败'
	})

	return innerAudioContext
}

const applyAudioPlaybackRate = () => {
	if (!innerAudioContext) return
	try {
		innerAudioContext.playbackRate = speechRate.value
	} catch (error) {
		console.warn('当前平台暂不支持动态调整播放倍速：', error)
	}
}

const playAudioByUrl = () => {
	if (!audioUrl.value) return
	const ctx = initInnerAudioContext()
	ctx.src = audioUrl.value
	applyAudioPlaybackRate()
	ctx.play()
}

const pauseAudioByUrl = () => {
	if (!innerAudioContext) return
	innerAudioContext.pause()
}

const stopAudioByUrl = () => {
	if (!innerAudioContext) return
	innerAudioContext.stop()
}

const cancelH5Speech = () => {
	// #ifdef H5
	if (h5SpeechSynthesis) h5SpeechSynthesis.cancel()
	currentUtterance = null
	// #endif
}

const playH5Speech = () => {
	// #ifdef H5
	if (!audioScriptText.value || !h5SpeechSynthesis || typeof SpeechSynthesisUtterance === 'undefined') {
		speechHintText.value = '当前浏览器暂不支持直接朗读'
		return
	}
	cancelH5Speech()
	const utterance = new SpeechSynthesisUtterance(audioScriptText.value)
	utterance.rate = speechRate.value
	utterance.lang = 'zh-CN'
	utterance.onstart = () => {
		speechStatus.value = 'playing'
		speechHintText.value = '正在朗读讲解内容'
	}
	utterance.onend = () => {
		speechStatus.value = 'idle'
		speechHintText.value = '朗读完成'
		currentUtterance = null
	}
	utterance.onerror = () => {
		speechStatus.value = 'idle'
		speechHintText.value = '朗读失败'
		currentUtterance = null
	}
	currentUtterance = utterance
	h5SpeechSynthesis.speak(utterance)
	// #endif
}

const toggleSpeech = () => {
	if (!hasSpeechContent.value) return
	if (audioUrl.value) {
		if (speechStatus.value === 'playing') pauseAudioByUrl()
		else playAudioByUrl()
		return
	}
	if (platformType.value === 'h5') {
		if (speechStatus.value === 'playing') {
			cancelH5Speech()
			speechStatus.value = 'paused'
			speechHintText.value = '已暂停，可继续朗读'
		} else {
			playH5Speech()
		}
		return
	}
	uni.showToast({ title: '当前端需后端返回音频链接后才可真播', icon: 'none' })
}

const stopSpeech = () => {
	if (audioUrl.value) {
		stopAudioByUrl()
		return
	}
	cancelH5Speech()
	speechStatus.value = 'idle'
	speechHintText.value = '已停止'
}

const changeSpeechRate = (rate) => {
	speechRate.value = rate
	applyAudioPlaybackRate()
}

const resetSpeechState = () => {
	stopSpeech()
}

const resetAiExplain = () => {
	explainRequestSeed += 1
	aiExplainData.value = {}
	aiExplainError.value = ''
	aiExplainPending.value = false
}

const fetchAiExplain = async () => {
	if (!exhibitId.value) return

	const requestId = ++explainRequestSeed
	aiExplainPending.value = true
	aiExplainError.value = ''
	aiExplainData.value = {}

	try {
		const result = await explainExhibit(exhibitId.value, {
			mode: explainMode.value
		})
		if (requestId !== explainRequestSeed) return
		aiExplainData.value = result || {}
	} catch (error) {
		if (requestId !== explainRequestSeed) return
		console.error('AI 文物讲解获取失败：', error)
		aiExplainError.value = error?.message || 'AI 讲解暂时不可用'
		aiExplainData.value = {}
	} finally {
		if (requestId === explainRequestSeed) {
			aiExplainPending.value = false
		}
	}
}

const changeExplainMode = (mode) => {
	if (!mode || mode === explainMode.value) return
	explainMode.value = mode
	resetSpeechState()
	fetchAiExplain()
}

const fetchExhibitData = async () => {
	if (!exhibitId.value) {
		errorText.value = '缺少文物 id'
		loading.value = false
		return
	}

	loading.value = true
	errorText.value = ''
	resetAiExplain()

	try {
		exhibit.value = await getExhibitDetail(exhibitId.value)

		const [assetsRes, graphRes] = await Promise.allSettled([
			getExhibitAssets(exhibitId.value),
			getExhibitGraph(exhibitId.value)
		])

		if (assetsRes.status === 'fulfilled') assetData.value = assetsRes.value || {}
		if (graphRes.status === 'fulfilled') graphData.value = graphRes.value || {}

		fetchAiExplain()
	} catch (error) {
		console.error('文物详情获取失败：', error)
		errorText.value = error?.message || '文物详情加载失败'
	} finally {
		loading.value = false
	}
}

const buildPageUrl = (path) => {
	return `${path}?id=${exhibitId.value}&name=${encodeURIComponent(exhibit.value?.name || pageName.value || '')}`
}

const goGraphPage = () => {
	uni.navigateTo({ url: buildPageUrl('/pages/exhibit/graph') })
}

const goRelatedPage = () => {
	uni.navigateTo({ url: buildPageUrl('/pages/exhibit/related') })
}

const reloadPage = () => {
	fetchExhibitData()
}

onLoad((options) => {
	// #ifdef MP-WEIXIN
	platformType.value = 'mp-weixin'
	// #endif
	// #ifdef H5
	platformType.value = 'h5'
	// #endif
	// #ifdef APP-PLUS
	platformType.value = 'app-plus'
	// #endif

	exhibitId.value = options?.id || ''
	pageName.value = decodeURIComponent(options?.name || '')
	fetchExhibitData()
})

onHide(() => {
	resetSpeechState()
})

onUnload(() => {
	resetSpeechState()
	if (innerAudioContext) {
		innerAudioContext.destroy()
		innerAudioContext = null
	}
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
		radial-gradient(circle at 100% 0, rgba(185, 139, 77, 0.16), transparent 24%),
		linear-gradient(180deg, #f7f1e7 0%, #f1e7da 100%);
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

.hero-top,
.explore-top,
.section-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16rpx;
}

.hero-badge,
.hall-chip,
.explore-badge,
.source-chip {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 8rpx 18rpx;
	border-radius: 999rpx;
	font-size: 22rpx;
	line-height: 1.3;
}

.hero-badge,
.explore-badge {
	background: rgba(110, 139, 120, 0.14);
	color: var(--brand-deep);
}

.hall-chip,
.explore-badge-accent,
.source-chip {
	background: rgba(185, 139, 77, 0.14);
	color: #8d6834;
}

.hero-title,
.section-title,
.explore-title,
.value-title {
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
.hero-caption,
.text-block,
.value-text,
.audio-hint,
.explore-text,
.explore-count,
.ai-placeholder,
.ai-watch-text,
.ai-quote,
.ai-takeaway-text,
.mode-hint {
	font-size: 25rpx;
	line-height: 1.82;
	color: var(--muted);
}

.hero-meta {
	margin-top: 12rpx;
}

.hero-image-wrap {
	margin-top: 24rpx;
	height: 520rpx;
	border-radius: 30rpx;
	overflow: hidden;
	background: linear-gradient(180deg, #e7ddd1 0%, #d8cab8 100%);
}

.hero-image {
	width: 100%;
	height: 100%;
}

.thumb-scroll {
	margin-top: 18rpx;
	white-space: nowrap;
}

.thumb-row {
	display: inline-flex;
	gap: 14rpx;
}

.thumb-image {
	width: 156rpx;
	height: 156rpx;
	border-radius: 22rpx;
	background: #dfd4c7;
}

.hero-caption {
	margin-top: 16rpx;
}

.hero-facts {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 14rpx;
	margin-top: 24rpx;
}

.hero-fact-card,
.fact-card,
.value-card,
.explore-card {
	padding: 22rpx;
	border-radius: 26rpx;
	background: rgba(255, 255, 255, 0.76);
	border: 1rpx solid rgba(185, 139, 77, 0.08);
}

.hero-fact-label,
.fact-label,
.ai-takeaway-label {
	font-size: 22rpx;
	color: #8a7f74;
	margin-bottom: 10rpx;
}

.hero-fact-value,
.fact-value {
	font-size: 26rpx;
	line-height: 1.55;
	font-weight: 700;
	color: var(--text);
}

.section-title {
	font-size: 38rpx;
	line-height: 1.35;
	font-weight: 700;
	margin-bottom: 18rpx;
}

.section-head .section-title {
	margin-bottom: 0;
}

.fact-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16rpx;
}

.tag-list {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
}

.tag {
	padding: 10rpx 18rpx;
	border-radius: 999rpx;
	background: rgba(110, 139, 120, 0.12);
	color: var(--brand-deep);
	font-size: 23rpx;
	line-height: 1.3;
}

.mode-panel {
	margin-top: 18rpx;
	margin-bottom: 10rpx;
}

.mode-row {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
}

.mode-chip {
	padding: 12rpx 20rpx;
	border-radius: 999rpx;
	background: rgba(47, 36, 29, 0.06);
	color: #665b51;
	font-size: 24rpx;
	line-height: 1.3;
}

.mode-chip-active {
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	font-weight: 700;
	box-shadow: 0 12rpx 24rpx rgba(73, 103, 86, 0.18);
}

.mode-hint {
	margin-top: 12rpx;
	font-size: 23rpx;
}

.text-block {
	margin-bottom: 16rpx;
}

.text-block-secondary {
	color: #5e544a;
}

.ai-placeholder {
	padding-top: 8rpx;
}

.ai-quote {
	margin-top: 14rpx;
	padding: 22rpx 24rpx;
	border-radius: 24rpx;
	background: linear-gradient(135deg, rgba(185, 139, 77, 0.12), rgba(110, 139, 120, 0.08));
	color: #4a4037;
}

.ai-watch-list {
	display: flex;
	flex-direction: column;
	gap: 14rpx;
	margin-top: 18rpx;
}

.ai-watch-item {
	display: flex;
	align-items: flex-start;
	gap: 16rpx;
	padding: 20rpx 22rpx;
	border-radius: 24rpx;
	background: rgba(110, 139, 120, 0.08);
}

.ai-watch-index {
	width: 50rpx;
	height: 50rpx;
	border-radius: 999rpx;
	flex-shrink: 0;
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	font-size: 22rpx;
	font-weight: 700;
	display: flex;
	align-items: center;
	justify-content: center;
}

.ai-watch-text {
	flex: 1;
	color: var(--text);
}

.ai-insight-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 18rpx;
}

.ai-insight-card {
	margin-top: 0;
}

.ai-takeaway {
	margin-top: 18rpx;
	padding: 22rpx 24rpx;
	border-radius: 26rpx;
	background: linear-gradient(135deg, rgba(185, 139, 77, 0.14), rgba(110, 139, 120, 0.1));
	border: 1rpx solid rgba(185, 139, 77, 0.14);
}

.ai-takeaway-text {
	color: var(--text);
	font-weight: 700;
}

.value-card {
	margin-top: 14rpx;
}

.value-title {
	font-size: 30rpx;
	line-height: 1.4;
	font-weight: 700;
	margin-bottom: 10rpx;
}

.audio-panel {
	display: flex;
	gap: 16rpx;
}

.audio-btn {
	flex: 1;
	border-radius: 999rpx;
	font-size: 26rpx;
	line-height: 1.4;
	border: none;
}

.audio-btn-primary {
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
}

.audio-btn-secondary {
	background: rgba(185, 139, 77, 0.14);
	color: #8d6834;
}

.rate-row {
	display: flex;
	align-items: center;
	gap: 18rpx;
	margin-top: 18rpx;
	flex-wrap: wrap;
}

.rate-label {
	font-size: 24rpx;
	color: #8a7f74;
}

.rate-list {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
}

.rate-chip {
	padding: 8rpx 18rpx;
	border-radius: 999rpx;
	background: rgba(47, 36, 29, 0.06);
	color: #665b51;
	font-size: 22rpx;
	line-height: 1.3;
}

.rate-chip-active {
	background: rgba(110, 139, 120, 0.16);
	color: var(--brand-deep);
	font-weight: 700;
}

.audio-hint {
	margin-top: 14rpx;
}

.explore-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16rpx;
}

.explore-title {
	margin-top: 14rpx;
	font-size: 30rpx;
	line-height: 1.4;
	font-weight: 700;
}

.explore-text {
	margin-top: 12rpx;
}

.reload-btn {
	width: 100%;
	background: linear-gradient(135deg, var(--brand), var(--brand-deep));
	color: #fffdf8;
	border-radius: 999rpx;
	font-size: 28rpx;
	line-height: 1.4;
	border: none;
}

.error-card {
	border: 1rpx solid rgba(188, 92, 58, 0.18);
}

button::after {
	border: none;
}

@media screen and (max-width: 640px) {
	.hero-facts,
	.fact-grid,
	.ai-insight-grid,
	.explore-grid {
		grid-template-columns: 1fr;
	}

	.audio-panel,
	.section-head {
		flex-direction: column;
		align-items: stretch;
	}
}
</style>
