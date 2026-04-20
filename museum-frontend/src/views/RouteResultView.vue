<template>
  <div class="page-shell">
    <div class="top-bar">
      <div class="top-actions">
        <el-button @click="goHome">返回首页</el-button>
        <el-button type="warning" @click="goReplan">重新规划</el-button>
        <el-button type="success" plain @click="goCreative">去做文创</el-button>
      </div>
      <el-button type="danger" plain @click="clearResult">清空结果</el-button>
    </div>

    <template v-if="routeResult">
      <section class="hero-area surface-card mb20">
        <div class="hero-main">
          <div class="eyebrow">ROUTE RESULT</div>
          <h1 class="title">{{ routeResult.route_title || '智能导览路线' }}</h1>

          <div class="tag-row">
            <el-tag v-if="routeResult.source" type="info" size="small">
              {{ routeResult.source }}
            </el-tag>
            <el-tag v-if="hallList.length" type="success" size="small">
              {{ hallList.length }} 个展区
            </el-tag>
            <el-tag v-if="dedupedExhibitList.length" type="warning" size="small">
              {{ dedupedExhibitList.length }} 件推荐展品
            </el-tag>
          </div>

          <p v-if="routeResult.route_theme" class="route-theme">
            {{ routeResult.route_theme }}
          </p>

          <p class="summary">{{ routeResult.route_summary || '暂无路线摘要' }}</p>
        </div>

        <div class="hero-side">
          <div class="metric-card">
            <span class="metric-label">路线定位</span>
            <strong>{{ routeResult.target_fit_reason || '暂无说明' }}</strong>
          </div>
          <div class="metric-card">
            <span class="metric-label">排序逻辑</span>
            <strong>{{ routeResult.order_logic || '暂无说明' }}</strong>
          </div>
        </div>
      </section>

      <section class="section-grid mb20">
        <el-card shadow="never" class="surface-card">
          <template #header>
            <div class="card-head">
              <span>推荐展区</span>
              <span class="head-tip">建议先从馆区主线进入</span>
            </div>
          </template>

          <div v-if="hallList.length" class="hall-list">
            <div
              v-for="(hall, index) in hallList"
              :key="getHallKey(hall)"
              class="hall-card"
            >
              <div class="hall-index">{{ index + 1 }}</div>
              <div class="hall-content">
                <h3>{{ hall.name || hall.hall_name || `展区 ${hall.id ?? ''}` }}</h3>
                <p v-if="hall.summary">{{ hall.summary }}</p>
                <div class="hall-meta">
                  <el-tag v-if="hall.recommended_duration_min" type="warning" effect="plain">
                    建议 {{ hall.recommended_duration_min }} 分钟
                  </el-tag>
                  <el-tag v-if="hall.theme" type="success" effect="plain">
                    {{ hall.theme }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无展区数据" />
        </el-card>

        <el-card shadow="never" class="surface-card">
          <template #header>
            <div class="card-head">
              <span>路线收束与时间策略</span>
              <span class="head-tip">适合答辩时解释方案的合理性</span>
            </div>
          </template>

          <div class="strategy-list">
            <div class="strategy-card">
              <h4>时间不够怎么办</h4>
              <p>{{ routeResult.skip_strategy || '暂无缩减建议' }}</p>
            </div>
            <div class="strategy-card">
              <h4>这条路线最后如何收束</h4>
              <p>{{ routeResult.route_closing || '暂无收束说明' }}</p>
            </div>
          </div>
        </el-card>
      </section>

      <el-card class="surface-card mb20" shadow="never">
        <template #header>
          <div class="card-head">
            <span>逐站导览</span>
            <span class="head-tip">每一站都讲清楚看什么、为什么现在看</span>
          </div>
        </template>

        <div v-if="stopGuideList.length" class="stop-guide-list">
          <div
            v-for="(item, index) in stopGuideList"
            :key="`${item.hall_id}-${index}`"
            class="stop-guide-card"
          >
            <div class="stop-line"></div>
            <div class="stop-index">{{ index + 1 }}</div>

            <div class="stop-content">
              <div class="stop-header">
                <div>
                  <h3 class="stop-title">{{ item.hall_name || '未命名展区' }}</h3>
                  <p v-if="item.hall_theme" class="stop-theme">{{ item.hall_theme }}</p>
                </div>

                <el-tag v-if="item.time_budget_min" type="warning">
                  建议 {{ item.time_budget_min }} 分钟
                </el-tag>
              </div>

              <div class="stop-grid">
                <div class="stop-section" v-if="item.focus">
                  <h4>这一站重点抓什么</h4>
                  <p>{{ item.focus }}</p>
                </div>

                <div class="stop-section" v-if="item.why_here">
                  <h4>为什么这一站放在这里</h4>
                  <p>{{ item.why_here }}</p>
                </div>
              </div>

              <div class="stop-section" v-if="item.key_exhibits && item.key_exhibits.length">
                <h4>这一站重点展品</h4>
                <div class="mini-tag-wrap">
                  <el-tag
                    v-for="(name, idx) in item.key_exhibits"
                    :key="`${name}-${idx}`"
                    class="mini-tag"
                    size="small"
                    effect="plain"
                  >
                    {{ name }}
                  </el-tag>
                </div>
              </div>

              <div class="stop-section" v-if="item.transition_to_next">
                <h4>下一站怎么接</h4>
                <p>{{ item.transition_to_next }}</p>
              </div>
            </div>
          </div>
        </div>

        <el-empty v-else description="暂无逐站导览信息" />
      </el-card>

      <el-card shadow="never" class="surface-card">
        <template #header>
          <div class="card-head">
            <span>推荐展品</span>
            <span class="head-tip">可直接进入详情、图谱与文创链路</span>
          </div>
        </template>

        <div v-if="dedupedExhibitList.length" class="grid">
          <article
            v-for="item in dedupedExhibitList"
            :key="getExhibitKey(item)"
            class="exhibit-card"
          >
            <div class="exhibit-top">
              <div>
                <h3 class="exhibit-title">{{ item.name || item.exhibit_name || '未命名展品' }}</h3>
                <div class="exhibit-tags">
                  <el-tag v-if="item.era" size="small">{{ item.era }}</el-tag>
                  <el-tag v-if="item.category" size="small" type="success">
                    {{ item.category }}
                  </el-tag>
                </div>
              </div>
            </div>

            <p class="exhibit-intro">
              {{ item.short_intro || item.description || item.deep_intro || '暂无简介' }}
            </p>

            <div class="exhibit-meta" v-if="item.material || item.craft || item.usage_desc">
              <p v-if="item.material"><span>材质：</span>{{ item.material }}</p>
              <p v-if="item.craft"><span>工艺：</span>{{ item.craft }}</p>
              <p v-if="item.usage_desc"><span>用途：</span>{{ item.usage_desc }}</p>
            </div>

            <div class="card-actions multi-actions">
              <el-button type="primary" @click="goDetail(item)">查看讲解</el-button>
              <el-button @click="goGraph(item)">关系图谱</el-button>
              <el-button type="success" plain @click="goCreative(item)">做文创</el-button>
            </div>
          </article>
        </div>
        <el-empty v-else description="暂无推荐展品" />
      </el-card>
    </template>

    <el-empty v-else description="暂无路线结果，请先返回首页生成路线">
      <el-button type="primary" @click="goHome">去首页</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useRouteStore } from '../stores/routeStore'

const router = useRouter()
const routeStore = useRouteStore()

const routeResult = computed(() => routeStore.routeResult)
const hallList = computed(() => routeResult.value?.selected_halls || [])
const exhibitList = computed(() => routeResult.value?.featured_exhibits || [])
const stopGuideList = computed(() => routeResult.value?.stop_guides || [])

const dedupedExhibitList = computed(() => {
  const raw = exhibitList.value || []
  const seen = new Set()

  return raw.filter((item) => {
    const key = `${item.name || item.exhibit_name || ''}-${item.hall_id || ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})

function getHallKey(hall) {
  return hall.id ?? hall.hall_id ?? hall.name
}

function getExhibitKey(item) {
  return item.id ?? item.exhibit_id ?? `${item.name}-${item.hall_id ?? ''}`
}

function goHome() {
  router.push('/')
}

function goReplan() {
  router.push('/replan')
}

function goDetail(item) {
  const id = item.id ?? item.exhibit_id
  if (!id) return
  router.push(`/exhibit/${id}`)
}

function goGraph(item) {
  const id = item.id ?? item.exhibit_id
  if (!id) return
  router.push(`/exhibit/${id}/graph`)
}

function goCreative(item) {
  const id = item?.id ?? item?.exhibit_id
  if (id) {
    router.push({ path: '/creative', query: { exhibitId: String(id) } })
    return
  }
  router.push('/creative')
}

async function clearResult() {
  await ElMessageBox.confirm('确定要清空当前路线结果吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
  routeStore.clearRouteResult()
  router.push('/')
}
</script>

<style scoped>
.page-shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.top-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mb20 {
  margin-bottom: 20px;
}

.hero-area {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 18px;
  padding: 24px;
}

.hero-main,
.hero-side {
  min-width: 0;
}

.eyebrow {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(217, 181, 116, 0.12);
  color: var(--brand-600);
  font-size: 12px;
  letter-spacing: 0.08em;
  font-weight: 700;
}

.title {
  margin: 14px 0 12px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.18;
  color: var(--ink-900);
}

.tag-row,
.exhibit-tags,
.hall-meta,
.mini-tag-wrap {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.route-theme {
  margin: 0 0 12px;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.8;
  color: var(--brand-600);
}

.summary {
  margin: 0;
  color: var(--ink-600);
  line-height: 1.95;
  white-space: pre-wrap;
}

.hero-side {
  display: grid;
  gap: 14px;
}

.metric-card,
.strategy-card,
.stop-guide-card,
.exhibit-card,
.hall-card {
  border-radius: 20px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 247, 244, 0.94));
  border: 1px solid rgba(19, 24, 36, 0.06);
}

.metric-card {
  min-height: 120px;
}

.metric-label {
  display: block;
  margin-bottom: 10px;
  color: var(--ink-500);
  font-size: 13px;
}

.metric-card strong,
.strategy-card p,
.stop-section p,
.exhibit-intro,
.exhibit-meta p,
.hall-content p {
  line-height: 1.85;
}

.section-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  font-weight: 700;
  color: var(--ink-900);
}

.head-tip {
  font-size: 13px;
  color: var(--ink-500);
  font-weight: 500;
}

.hall-list,
.strategy-list,
.stop-guide-list {
  display: grid;
  gap: 14px;
}

.hall-card {
  display: grid;
  grid-template-columns: 46px 1fr;
  gap: 14px;
  align-items: start;
}

.hall-index,
.stop-index {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--brand-500), var(--brand-700));
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.hall-content h3,
.stop-title,
.exhibit-title {
  margin: 0 0 8px;
  color: var(--ink-900);
}

.stop-guide-card {
  position: relative;
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 16px;
}

.stop-line {
  position: absolute;
  top: 20px;
  left: 38px;
  bottom: -14px;
  width: 2px;
  background: linear-gradient(180deg, rgba(140, 91, 45, 0.24), rgba(140, 91, 45, 0.02));
}

.stop-guide-card:last-child .stop-line {
  display: none;
}

.stop-header,
.exhibit-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.stop-theme,
.exhibit-meta,
.exhibit-intro,
.hall-content p,
.strategy-card p {
  color: var(--ink-600);
}

.stop-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.stop-section h4,
.strategy-card h4 {
  margin: 0 0 8px;
  color: var(--ink-900);
}

.stop-section + .stop-section {
  margin-top: 10px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.exhibit-title {
  font-size: 20px;
  line-height: 1.35;
}

.exhibit-intro {
  min-height: 86px;
  margin: 0 0 12px;
}

.exhibit-meta span {
  font-weight: 700;
  color: var(--ink-900);
}

.card-actions {
  display: flex;
  justify-content: flex-end;
}

.multi-actions {
  justify-content: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .hero-area,
  .section-grid,
  .stop-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-shell {
    width: min(1180px, calc(100% - 24px));
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .metric-card,
  .strategy-card,
  .stop-guide-card,
  .exhibit-card,
  .hall-card {
    padding: 16px;
  }
}
</style>
