<template>
  <div class="page-shell">
    <div class="top-bar">
      <div class="top-actions">
        <el-button @click="goDetail">返回详情页</el-button>
        <el-button @click="goHome">回首页</el-button>
      </div>
    </div>

    <el-card class="surface-card" shadow="never" v-loading="loading">
      <template #header>
        <div class="card-head">
          <span>相关文物</span>
          <span class="head-tip">单独展开看，不堆在详情页里</span>
        </div>
      </template>

      <template v-if="items.length">
        <div class="related-grid">
          <article
            v-for="item in items"
            :key="`${item.id}-${item.name}`"
            class="related-card"
            @click="goNode(item.id)"
          >
            <div class="title-row">
              <h3>{{ item.name }}</h3>
              <el-tag v-if="item.relation_type" size="small" effect="plain">
                {{ item.relation_type }}
              </el-tag>
            </div>

            <div class="meta-row">
              <span v-if="item.era">{{ item.era }}</span>
              <span v-if="item.category">{{ item.category }}</span>
            </div>

            <p>{{ item.relation_summary || item.short_intro || item.usage_desc || '点击查看详情' }}</p>
          </article>
        </div>
      </template>

      <el-empty v-else description="暂无相关文物" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getRelatedExhibits } from '../api/exhibit'

const route = useRoute()
const router = useRouter()

const exhibitId = ref(route.params.id)
const items = ref([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    items.value = await getRelatedExhibits(exhibitId.value)
  } catch (error) {
    ElMessage.error(error.message || '获取相关文物失败')
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

function goNode(id) {
  if (!id) return
  router.push(`/exhibit/${id}`)
}

onMounted(loadData)

watch(
  () => route.params.id,
  async (newId) => {
    exhibitId.value = newId
    items.value = []
    await loadData()
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
.top-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.top-bar {
  justify-content: space-between;
  margin-bottom: 16px;
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

.related-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.related-card {
  padding: 20px;
  border-radius: 22px;
  background: rgba(247, 244, 237, 0.88);
  cursor: pointer;
  transition: transform 0.2s ease;
}

.related-card:hover {
  transform: translateY(-2px);
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.title-row h3 {
  margin: 0;
  color: #2f6b5a;
}

.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 10px 0;
  color: #a18252;
  font-size: 13px;
}

.related-card p {
  margin: 0;
  color: #6a7383;
  line-height: 1.8;
}

@media (max-width: 900px) {
  .page-shell {
    width: min(1120px, calc(100% - 20px));
  }

  .related-grid {
    grid-template-columns: 1fr;
  }
}
</style>