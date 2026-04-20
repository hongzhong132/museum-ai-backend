<template>
  <div class="page-shell">
    <div class="top-bar">
      <div class="top-actions">
        <el-button @click="goDetail">返回详情页</el-button>
        <el-button @click="goHome">回首页</el-button>
      </div>
      <div class="top-actions">
        <el-button type="success" plain @click="goCreative">做文创</el-button>
      </div>
    </div>

    <el-card class="surface-card mb20" shadow="never" v-loading="loading">
      <template #header>
        <div class="card-head">
          <span>知识图谱</span>
          <span class="head-tip">把图谱单独放出去，三个部分都能看见</span>
        </div>
      </template>

      <template v-if="graph">
        <section class="hero-card">
          <div class="eyebrow">KNOWLEDGE GRAPH</div>
          <h1 class="title">{{ graph.exhibit_name }}</h1>
          <p class="subline">
            {{ graph.center_node?.hall_name || '未命名专题' }}
            <span v-if="graph.center_node?.era"> · {{ graph.center_node.era }}</span>
            <span v-if="graph.center_node?.category"> · {{ graph.center_node.category }}</span>
          </p>
          <p class="summary">{{ graph.graph_summary || graph.center_node?.core_value || graph.center_node?.short_intro }}</p>
        </section>

        <div class="tab-row">
          <button
            v-for="item in tabs"
            :key="item.value"
            class="tab-chip"
            :class="{ 'is-active': activeTab === item.value }"
            type="button"
            @click="activeTab = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <section v-if="activeTab === 'network'" class="graph-section">
          <div class="section-title">关联网络</div>

          <div class="network-shell">
            <article class="center-card">
              <div class="node-badge">中心文物</div>
              <h3>{{ graph.center_node?.name }}</h3>
              <p>{{ graph.center_node?.hall_name }}<span v-if="graph.center_node?.era"> · {{ graph.center_node.era }}</span><span v-if="graph.center_node?.category"> · {{ graph.center_node.category }}</span></p>
            </article>

            <div class="related-grid">
              <button
                v-for="item in graph.related_nodes"
                :key="item.id"
                class="related-card"
                type="button"
                @click="goNode(item.id)"
              >
                <h4>{{ item.name }}</h4>
                <p>{{ relationLabel(item) }}</p>
              </button>
            </div>
          </div>

          <div v-if="graph.relation_type_stats?.length" class="stat-row">
            <el-tag
              v-for="item in graph.relation_type_stats"
              :key="`${item.type}-${item.count}`"
              effect="plain"
            >
              {{ item.label }} {{ item.count }}
            </el-tag>
          </div>
        </section>

        <section v-if="activeTab === 'timeline'" class="graph-section">
          <div class="section-title">时间线视图</div>
          <div class="timeline-list">
            <article
              v-for="item in graph.timeline_nodes"
              :key="`${item.id}-${item.name}`"
              class="timeline-card"
            >
              <div class="timeline-time">{{ item.time_label || '时间未标注' }}</div>
              <div class="timeline-body">
                <h4>{{ item.name }}</h4>
                <p v-if="item.subtitle" class="timeline-subtitle">{{ item.subtitle }}</p>
                <p>{{ item.summary || '暂无说明' }}</p>
              </div>
            </article>
          </div>
        </section>

        <section v-if="activeTab === 'craft'" class="graph-section">
          <div class="section-title">工艺视图</div>
          <div class="craft-list">
            <article
              v-for="section in graph.craft_sections"
              :key="section.key"
              class="craft-card"
            >
              <div class="craft-head">
                <div>
                  <h4>{{ section.title }}</h4>
                  <p v-if="section.subtitle">{{ section.subtitle }}</p>
                </div>
              </div>

              <p class="craft-desc">{{ section.description || '暂无说明' }}</p>

              <div v-if="section.tags?.length" class="tag-row">
                <el-tag v-for="tag in section.tags" :key="tag" effect="plain">{{ tag }}</el-tag>
              </div>

              <div v-if="section.related_nodes?.length" class="mini-grid">
                <button
                  v-for="node in section.related_nodes"
                  :key="node.id"
                  class="mini-node"
                  type="button"
                  @click="goNode(node.id)"
                >
                  <strong>{{ node.name }}</strong>
                  <span>{{ relationLabel(node) }}</span>
                </button>
              </div>
            </article>
          </div>
        </section>

        <section v-if="graph.hall_chain?.next_halls?.length" class="graph-section hall-section">
          <div class="section-title">馆区承接</div>
          <div class="hall-grid">
            <article class="hall-card current-card">
              <h4>{{ graph.hall_chain.current_hall?.name || '当前馆区' }}</h4>
              <p>{{ graph.hall_chain.current_hall?.summary || '暂无摘要' }}</p>
            </article>

            <article
              v-for="hall in graph.hall_chain.next_halls"
              :key="hall.hall_id"
              class="hall-card"
            >
              <h4>{{ hall.name }}</h4>
              <p v-if="hall.relation_label">{{ hall.relation_label }} · {{ hall.relation_summary }}</p>
              <p v-else>{{ hall.summary || '暂无说明' }}</p>
              <div v-if="hall.key_exhibits?.length" class="tag-row">
                <el-tag v-for="item in hall.key_exhibits" :key="item" effect="plain">{{ item }}</el-tag>
              </div>
            </article>
          </div>
        </section>
      </template>

      <el-empty v-else description="暂无图谱数据" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getExhibitGraph } from '../api/exhibit'

const route = useRoute()
const router = useRouter()

const exhibitId = ref(route.params.id)
const graph = ref(null)
const loading = ref(false)
const activeTab = ref('network')

const tabs = [
  { label: '关联网络', value: 'network' },
  { label: '时间线视图', value: 'timeline' },
  { label: '工艺视图', value: 'craft' }
]

function relationLabel(item) {
  return item?.relation_summary || item?.relation_type || '关联节点'
}

async function loadGraph() {
  loading.value = true
  try {
    graph.value = await getExhibitGraph(exhibitId.value)
  } catch (error) {
    ElMessage.error(error.message || '获取图谱失败')
  } finally {
    loading.value = false
  }
}

function goDetail() {
  router.push(`/exhibit/${exhibitId.value}`)
}

function goHome() {
  router.push('/')
}

function goCreative() {
  router.push({
    path: '/creative',
    query: {
      exhibitId: exhibitId.value,
      exhibitName: graph.value?.exhibit_name || ''
    }
  })
}

function goNode(id) {
  if (!id) return
  router.push(`/exhibit/${id}`)
}

onMounted(loadGraph)

watch(
  () => route.params.id,
  async (newId) => {
    exhibitId.value = newId
    graph.value = null
    activeTab.value = 'network'
    await loadGraph()
  }
)
</script>

<style scoped>
.page-shell {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
  padding: 26px 0 42px;
}

.top-bar,
.top-actions,
.tab-row,
.tag-row {
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

.hero-card {
  padding: 6px 0 4px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(50, 109, 90, 0.1);
  color: #5f7a72;
  font-size: 12px;
  font-weight: 700;
}

.title {
  margin: 14px 0 10px;
  font-size: clamp(34px, 4vw, 46px);
  line-height: 1.1;
  color: #2e5f52;
}

.subline {
  margin: 0;
  color: #9a8e7c;
  font-size: 18px;
}

.summary {
  margin: 16px 0 0;
  color: #5d6778;
  line-height: 1.85;
}

.tab-row {
  margin: 22px 0 18px;
}

.tab-chip {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  border: none;
  background: rgba(244, 239, 232, 0.92);
  color: #a18252;
  cursor: pointer;
  font-weight: 700;
}

.tab-chip.is-active {
  background: #326d5a;
  color: #fff;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #8c5b2d;
  margin-bottom: 14px;
}

.graph-section + .graph-section,
.graph-section + .hall-section {
  margin-top: 20px;
}

.network-shell {
  padding: 18px;
  border-radius: 26px;
  background: rgba(247, 244, 237, 0.85);
}

.center-card {
  padding: 18px;
  border-radius: 22px;
  background: #fff;
  border: 1px solid rgba(19, 24, 36, 0.08);
}

.node-badge {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(50, 109, 90, 0.1);
  color: #326d5a;
  font-size: 12px;
  font-weight: 700;
}

.center-card h3,
.related-card h4,
.timeline-card h4,
.craft-card h4,
.hall-card h4 {
  margin: 12px 0 8px;
  color: #2e5f52;
}

.center-card p,
.related-card p,
.timeline-card p,
.craft-card p,
.hall-card p,
.mini-node span {
  margin: 0;
  color: #8b93a2;
  line-height: 1.75;
}

.related-grid,
.hall-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.related-card,
.mini-node {
  text-align: left;
  padding: 18px;
  border-radius: 20px;
  border: none;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 6px 14px rgba(23, 28, 38, 0.04);
}

.stat-row {
  margin-top: 14px;
}

.timeline-list,
.craft-list {
  display: grid;
  gap: 14px;
}

.timeline-card,
.craft-card,
.hall-card {
  padding: 18px;
  border-radius: 22px;
  background: rgba(247, 244, 237, 0.85);
}

.timeline-card {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 16px;
}

.timeline-time {
  font-weight: 700;
  color: #326d5a;
}

.timeline-subtitle {
  color: #a18252 !important;
  margin-bottom: 10px !important;
}

.craft-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.craft-head p,
.craft-desc {
  color: #8b93a2;
}

.craft-desc {
  margin: 8px 0 14px;
  line-height: 1.8;
}

.mini-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.current-card {
  background: rgba(50, 109, 90, 0.08);
}

@media (max-width: 900px) {
  .page-shell {
    width: min(1120px, calc(100% - 20px));
  }

  .related-grid,
  .hall-grid,
  .mini-grid,
  .timeline-card {
    grid-template-columns: 1fr;
  }

  .timeline-card {
    display: block;
  }
}
</style>