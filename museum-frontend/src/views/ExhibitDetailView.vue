<template>
  <div class="page-shell">
    <div class="top-bar">
      <div class="top-actions">
        <el-button @click="goBack">返回路线页</el-button>
        <el-button @click="goHome">回首页</el-button>
      </div>
      <div class="top-actions">
        <el-button @click="goGraph">关系图谱</el-button>
        <el-button type="success" plain @click="goCreative">做文创</el-button>
      </div>
    </div>

    <el-card class="surface-card mb20" shadow="never" v-loading="pageLoading">
      <template #header>
        <div class="card-head">
          <span>展品信息</span>
          <span class="head-tip">图片、来源与语音放在这里</span>
        </div>
      </template>

      <template v-if="detail">
        <section class="detail-layout">
          <div class="media-panel">
            <div class="hero-image-wrap">
              <img
                v-if="mainImageUrl"
                :src="mainImageUrl"
                :alt="detailTitle"
                class="hero-image"
              />
              <div v-else class="image-empty">暂无图片</div>
            </div>

            <div v-if="galleryImages.length > 1" class="thumb-list">
              <button
                v-for="(image, index) in galleryImages"
                :key="`${image}-${index}`"
                class="thumb-btn"
                :class="{ 'is-active': activeImage === image }"
                type="button"
                @click="activeImage = image"
              >
                <img :src="image" :alt="`${detailTitle}-${index}`" />
              </button>
            </div>

            <div v-if="assets?.image_caption || assets?.source_name || assets?.source_url" class="asset-note">
              <p v-if="assets?.image_caption">{{ assets.image_caption }}</p>
              <p v-if="assets?.source_name">来源：{{ assets.source_name }}</p>
              <p v-if="assets?.source_url">
                链接：
                <a :href="assets.source_url" target="_blank" rel="noreferrer">查看原始来源</a>
              </p>
            </div>
          </div>

          <div class="content-panel">
            <div class="eyebrow">EXHIBIT DETAIL</div>
            <h1 class="title">{{ detailTitle }}</h1>

            <div class="tag-row">
              <el-tag v-if="detail.era" class="meta-tag">{{ detail.era }}</el-tag>
              <el-tag v-if="detail.category" class="meta-tag" type="success">
                {{ detail.category }}
              </el-tag>
              <el-tag v-if="hallName" class="meta-tag" type="warning">
                {{ hallName }}
              </el-tag>
            </div>

            <p class="intro-text">{{ detail.short_intro || '暂无简介' }}</p>

            <div class="info-grid">
              <div class="info-box" v-if="detail.era">
                <span>时代</span>
                <strong>{{ detail.era }}</strong>
              </div>
              <div class="info-box" v-if="detail.dynasty">
                <span>朝代</span>
                <strong>{{ detail.dynasty }}</strong>
              </div>
              <div class="info-box" v-if="detail.category">
                <span>类别</span>
                <strong>{{ detail.category }}</strong>
              </div>
              <div class="info-box" v-if="detail.sub_category">
                <span>细分</span>
                <strong>{{ detail.sub_category }}</strong>
              </div>
              <div class="info-box" v-if="detail.material">
                <span>材质</span>
                <strong>{{ detail.material }}</strong>
              </div>
              <div class="info-box" v-if="detail.craft">
                <span>工艺</span>
                <strong>{{ detail.craft }}</strong>
              </div>
              <div class="info-box" v-if="detail.usage_desc">
                <span>用途</span>
                <strong>{{ detail.usage_desc }}</strong>
              </div>
              <div class="info-box" v-if="detail.shape_desc">
                <span>器形特征</span>
                <strong>{{ detail.shape_desc }}</strong>
              </div>
              <div class="info-box" v-if="detail.recommended_duration_min">
                <span>建议停留</span>
                <strong>{{ detail.recommended_duration_min }} 分钟</strong>
              </div>
            </div>

            <div v-if="styleTags.length" class="mini-section">
              <h4>风格标签</h4>
              <div class="chip-row">
                <el-tag v-for="tag in styleTags" :key="tag" effect="plain">{{ tag }}</el-tag>
              </div>
            </div>

            <div v-if="patternTags.length" class="mini-section">
              <h4>纹样元素</h4>
              <div class="chip-row">
                <el-tag v-for="tag in patternTags" :key="tag" effect="plain">{{ tag }}</el-tag>
              </div>
            </div>

            <div class="mini-section" v-if="detail.deep_intro || detail.core_value || detail.hall?.summary">
              <h4>补充理解</h4>
              <p v-if="detail.deep_intro" class="paragraph">{{ detail.deep_intro }}</p>
              <p v-if="detail.core_value" class="paragraph">{{ detail.core_value }}</p>
              <p v-if="detail.hall?.summary" class="paragraph">
                所属展区：<span class="inline-strong">{{ detail.hall.name }}</span>
                <span v-if="detail.hall.theme"> · {{ detail.hall.theme }}</span>
                <span>。{{ detail.hall.summary }}</span>
              </p>
            </div>
          </div>
        </section>
      </template>

      <el-empty v-else description="暂无展品详情" />
    </el-card>

    <el-card class="surface-card mb20" shadow="never" v-if="assets?.audio_url || assets?.audio_script">
      <template #header>
        <div class="card-head">
          <span>语音讲解</span>
          <span class="head-tip">支持播放、停止和倍速切换</span>
        </div>
      </template>

      <div class="audio-box">
        <div class="audio-buttons">
          <el-button type="primary" :disabled="!assets?.audio_url" @click="playAudio">
            播放讲解
          </el-button>
          <el-button :disabled="!isAudioReady" @click="stopAudio">停止</el-button>
        </div>

        <div v-if="assets?.audio_url" class="speed-row">
          <button
            v-for="item in speedOptions"
            :key="item"
            class="speed-chip"
            :class="{ 'is-active': playbackRate === item }"
            type="button"
            @click="changeSpeed(item)"
          >
            {{ formatSpeed(item) }}
          </button>
        </div>

        <p v-if="assets?.audio_script" class="audio-script">{{ assets.audio_script }}</p>
        <audio ref="audioRef" :src="assets?.audio_url || ''" preload="none" @ended="handleAudioEnded" />
      </div>
    </el-card>

    <el-card class="surface-card mb20" shadow="never">
      <template #header>
        <div class="card-head">
          <span>讲解模式</span>
          <span class="head-tip">先选模式，再看 AI 讲解</span>
        </div>
      </template>

      <div class="mode-switcher">
        <button
          v-for="item in modeOptions"
          :key="item.value"
          class="mode-chip"
          :class="{ 'is-active': mode === item.value }"
          type="button"
          @click="changeMode(item.value)"
        >
          <strong>{{ item.label }}</strong>
          <span>{{ item.desc }}</span>
        </button>
      </div>
    </el-card>

    <el-card class="surface-card mb20" shadow="never" v-loading="explainLoading">
      <template #header>
        <div class="card-head">
          <span>AI 讲解内容</span>
          <span class="head-tip">拆成几个小块，不再整页堆满</span>
        </div>
      </template>

      <template v-if="explanation">
        <div class="explain-grid">
          <div v-if="explanation.intro" class="explain-section">
            <h4>开场理解</h4>
            <p>{{ explanation.intro }}</p>
          </div>
          <div v-if="explanation.first_impression" class="explain-section">
            <h4>第一眼看什么</h4>
            <p>{{ explanation.first_impression }}</p>
          </div>
          <div v-if="explanation.historical_role" class="explain-section">
            <h4>历史角色</h4>
            <p>{{ explanation.historical_role }}</p>
          </div>
          <div v-if="explanation.craft_value" class="explain-section">
            <h4>工艺价值</h4>
            <p>{{ explanation.craft_value }}</p>
          </div>
          <div v-if="watchPoints.length" class="explain-section full-span">
            <h4>观看重点</h4>
            <div class="chip-row">
              <el-tag v-for="point in watchPoints" :key="point" effect="plain">{{ point }}</el-tag>
            </div>
          </div>
          <div v-if="explanation.relation_to_route" class="explain-section">
            <h4>为什么现在看它</h4>
            <p>{{ explanation.relation_to_route }}</p>
          </div>
          <div v-if="explanation.compare_hint" class="explain-section">
            <h4>可以和哪件一起看</h4>
            <p>{{ explanation.compare_hint }}</p>
          </div>
          <div v-if="explanation.one_sentence_takeaway" class="explain-section full-span">
            <h4>一句话记住它</h4>
            <p>{{ explanation.one_sentence_takeaway }}</p>
          </div>
          <div class="explain-section full-span">
            <h4>完整讲解</h4>
            <p class="paragraph">{{ explanation.explanation || '暂无讲解内容' }}</p>
          </div>
        </div>
      </template>

      <el-empty v-else description="暂无讲解内容" />
    </el-card>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span>继续深入</span>
          <span class="head-tip">把图谱和相关文物拆出去，不全堆在详情页</span>
        </div>
      </template>

      <div class="deep-grid">
        <button class="jump-card" type="button" @click="goGraph">
          <div class="jump-badge">图</div>
          <div class="jump-meta">{{ graphCountText }}</div>
          <h3>知识图谱</h3>
          <p>把关联网络、时间线和工艺视图放到独立页面里看。</p>
        </button>

        <button class="jump-card" type="button" @click="goRelated">
          <div class="jump-badge">联</div>
          <div class="jump-meta">{{ relatedCountText }}</div>
          <h3>相关文物</h3>
          <p>单独查看适合继续去看的文物，不把所有内容堆在当前页。</p>
        </button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  explainExhibit,
  getExhibitAssets,
  getExhibitDetail,
  getExhibitGraph,
  getRelatedExhibits
} from '../api/exhibit'

const route = useRoute()
const router = useRouter()

const exhibitId = ref(route.params.id)
const detail = ref(null)
const assets = ref(null)
const graph = ref(null)
const relatedList = ref([])
const explanation = ref(null)
const pageLoading = ref(false)
const explainLoading = ref(false)
const mode = ref('normal')
const activeImage = ref('')
const audioRef = ref(null)
const isAudioReady = ref(false)
const playbackRate = ref(1)

const speedOptions = [1, 1.25, 1.5]

const modeOptions = [
  { value: 'normal', label: '普通讲解', desc: '适合快速理解核心信息' },
  { value: 'deep', label: '深度讲解', desc: '更强调历史背景和工艺细节' },
  { value: 'child', label: '儿童讲解', desc: '更轻松，更容易进入情境' }
]

const detailTitle = computed(() => detail.value?.name || detail.value?.exhibit_name || '展品详情')
const hallName = computed(() => detail.value?.hall?.name || '')
const styleTags = computed(() => splitTags(detail.value?.style_tags))
const patternTags = computed(() => splitTags(detail.value?.pattern_elements))
const watchPoints = computed(() => explanation.value?.core_watch_points || [])
const graphCountText = computed(() => `${(graph.value?.related_nodes?.length || 0) + 1} 个节点`)
const relatedCountText = computed(() => `${relatedList.value.length || detail.value?.related_exhibits?.length || 0} 件`)
const galleryImages = computed(() => {
  const list = []
  const add = (value) => {
    if (!value || list.includes(value)) return
    list.push(value)
  }
  add(activeImage.value)
  add(detail.value?.image_url)
  add(assets.value?.cover_image_url)
  ;(assets.value?.detail_image_urls || []).forEach(add)
  return list.filter(Boolean)
})
const mainImageUrl = computed(() => activeImage.value || galleryImages.value[0] || '')

const currentContextExhibitId = computed(() => {
  const from = route.query.from
  if (!from) return null
  const num = Number(from)
  return Number.isNaN(num) ? null : num
})

function splitTags(value) {
  if (!value) return []
  return String(value)
    .split(/[，,、；;|\n\t ]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function formatSpeed(value) {
  return value === 1 ? '1x' : `${value}x`
}

async function loadPageData() {
  pageLoading.value = true
  try {
    const [detailRes, assetsRes, graphRes, relatedRes] = await Promise.all([
      getExhibitDetail(exhibitId.value),
      getExhibitAssets(exhibitId.value),
      getExhibitGraph(exhibitId.value),
      getRelatedExhibits(exhibitId.value)
    ])
    detail.value = detailRes
    assets.value = assetsRes
    graph.value = graphRes
    relatedList.value = relatedRes || []
    activeImage.value =
      detailRes?.image_url ||
      assetsRes?.cover_image_url ||
      assetsRes?.detail_image_urls?.[0] ||
      ''
    await nextTick()
    applyPlaybackRate(playbackRate.value)
  } catch (error) {
    ElMessage.error(error.message || '获取展品信息失败')
  } finally {
    pageLoading.value = false
  }
}

async function loadExplanation() {
  explainLoading.value = true
  try {
    explanation.value = await explainExhibit(exhibitId.value, {
      mode: mode.value,
      current_context_exhibit_id: currentContextExhibitId.value
    })
  } catch (error) {
    ElMessage.error(error.message || '获取讲解失败')
  } finally {
    explainLoading.value = false
  }
}

function goBack() {
  router.push('/route-result')
}

function goHome() {
  router.push('/')
}

function goGraph() {
  router.push({
    path: `/exhibit/${exhibitId.value}/graph`,
    query: { from: route.query.from || '' }
  })
}

function goRelated() {
  router.push({
    path: `/exhibit/${exhibitId.value}/related`,
    query: { from: route.query.from || '' }
  })
}

function goCreative() {
  router.push({
    path: '/creative',
    query: {
      exhibitId: exhibitId.value,
      exhibitName: detail.value?.name || ''
    }
  })
}

function changeMode(value) {
  if (mode.value === value) return
  mode.value = value
}

async function playAudio() {
  if (!audioRef.value || !assets.value?.audio_url) return
  try {
    applyPlaybackRate(playbackRate.value)
    await audioRef.value.play()
    isAudioReady.value = true
  } catch (error) {
    ElMessage.error('音频播放失败')
  }
}

function stopAudio() {
  if (!audioRef.value) return
  audioRef.value.pause()
  audioRef.value.currentTime = 0
  isAudioReady.value = false
}

function changeSpeed(value) {
  playbackRate.value = value
  applyPlaybackRate(value)
}

function applyPlaybackRate(value) {
  if (!audioRef.value) return
  audioRef.value.playbackRate = value
}

function handleAudioEnded() {
  isAudioReady.value = false
}

onMounted(async () => {
  await Promise.all([loadPageData(), loadExplanation()])
})

onUnmounted(() => {
  stopAudio()
})

watch(
  () => route.params.id,
  async (newId) => {
    exhibitId.value = newId
    detail.value = null
    assets.value = null
    graph.value = null
    relatedList.value = []
    explanation.value = null
    mode.value = 'normal'
    activeImage.value = ''
    stopAudio()
    await Promise.all([loadPageData(), loadExplanation()])
  }
)

watch(mode, async () => {
  await loadExplanation()
})
</script>

<style scoped>
.page-shell {
  width: min(1240px, calc(100% - 32px));
  margin: 0 auto;
  padding: 26px 0 42px;
}

.top-bar,
.top-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.top-bar {
  justify-content: space-between;
  margin-bottom: 16px;
}

.mb20 {
  margin-bottom: 20px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.head-tip {
  color: #8b93a2;
  font-size: 13px;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 470px) minmax(0, 1fr);
  gap: 20px;
}

.media-panel {
  min-width: 0;
}

.hero-image-wrap {
  border-radius: 26px;
  overflow: hidden;
  background: rgba(237, 240, 239, 0.9);
  min-height: 560px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-image {
  width: 100%;
  height: 100%;
  min-height: 560px;
  object-fit: cover;
  display: block;
}

.image-empty {
  color: #8b93a2;
}

.thumb-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.thumb-btn {
  width: 84px;
  height: 84px;
  padding: 0;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(20, 24, 34, 0.08);
  background: #fff;
  cursor: pointer;
}

.thumb-btn.is-active {
  border-color: rgba(140, 91, 45, 0.45);
  box-shadow: 0 10px 22px rgba(140, 91, 45, 0.14);
}

.thumb-btn img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.asset-note {
  margin-top: 14px;
  padding: 16px;
  border-radius: 20px;
  background: rgba(245, 241, 235, 0.78);
}

.asset-note p {
  margin: 0 0 8px;
  color: #5d6778;
  line-height: 1.75;
}

.asset-note p:last-child {
  margin-bottom: 0;
}

.asset-note a {
  color: #8c5b2d;
  text-decoration: none;
}

.content-panel {
  min-width: 0;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(180, 122, 61, 0.12);
  color: #9a6833;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.title {
  margin: 14px 0 12px;
  font-size: clamp(38px, 4vw, 56px);
  line-height: 1.08;
  color: #1d2737;
}

.tag-row,
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.meta-tag {
  margin-right: 0;
}

.intro-text,
.paragraph {
  margin: 16px 0 0;
  color: #5d6778;
  line-height: 1.85;
  white-space: pre-wrap;
}

.info-grid {
  margin-top: 20px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.info-box {
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px solid rgba(19, 24, 36, 0.06);
  background: rgba(248, 247, 244, 0.88);
}

.info-box span {
  display: block;
  color: #8b93a2;
  font-size: 13px;
  margin-bottom: 8px;
}

.info-box strong {
  color: #273243;
  line-height: 1.75;
}

.mini-section {
  margin-top: 20px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(248, 247, 244, 0.8);
}

.mini-section h4,
.explain-section h4,
.jump-card h3 {
  margin: 0 0 10px;
  color: #273243;
}

.inline-strong {
  font-weight: 700;
  color: #273243;
}

.audio-box {
  display: grid;
  gap: 14px;
}

.audio-buttons,
.speed-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.speed-chip {
  min-height: 36px;
  padding: 0 16px;
  border-radius: 999px;
  border: none;
  background: rgba(244, 239, 232, 0.9);
  color: #8b93a2;
  cursor: pointer;
}

.speed-chip.is-active {
  background: rgba(50, 109, 90, 0.14);
  color: #2f6b5a;
  font-weight: 700;
}

.audio-script {
  margin: 0;
  color: #7b8594;
  line-height: 1.8;
}

.mode-switcher {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.mode-chip {
  text-align: left;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(19, 24, 36, 0.08);
  background: rgba(248, 247, 244, 0.84);
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-chip strong {
  display: block;
  color: #273243;
}

.mode-chip span {
  display: block;
  margin-top: 8px;
  color: #7b8594;
  line-height: 1.65;
  font-size: 13px;
}

.mode-chip.is-active {
  border-color: rgba(140, 91, 45, 0.4);
  background: rgba(180, 122, 61, 0.1);
}

.explain-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.explain-section {
  padding: 18px;
  border-radius: 20px;
  background: rgba(248, 247, 244, 0.84);
  border: 1px solid rgba(19, 24, 36, 0.06);
}

.explain-section p {
  margin: 0;
  color: #5d6778;
  line-height: 1.85;
  white-space: pre-wrap;
}

.full-span {
  grid-column: 1 / -1;
}

.deep-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.jump-card {
  text-align: left;
  padding: 20px;
  border-radius: 24px;
  border: none;
  background: rgba(247, 244, 237, 0.88);
  cursor: pointer;
}

.jump-badge {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: #326d5a;
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.jump-meta {
  margin-top: 12px;
  color: #a57d43;
  font-weight: 600;
}

.jump-card p {
  margin: 0;
  color: #7b8594;
  line-height: 1.75;
}

@media (max-width: 980px) {
  .page-shell {
    width: min(1240px, calc(100% - 20px));
  }

  .detail-layout,
  .mode-switcher,
  .explain-grid,
  .deep-grid {
    grid-template-columns: 1fr;
  }

  .hero-image-wrap,
  .hero-image {
    min-height: 340px;
  }

  .title {
    font-size: 40px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>