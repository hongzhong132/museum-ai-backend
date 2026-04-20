<template>
  <div class="page-shell">
    <div class="top-bar">
      <div class="top-actions">
        <el-button @click="goHome">回首页</el-button>
        <el-button v-if="routeStore.hasRouteResult" @click="goRouteResult">回路线页</el-button>
      </div>
    </div>

    <div class="creative-layout">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span>AI 文创</span>
            <span class="head-tip">把路线主题和文物元素变成纪念海报</span>
          </div>
        </template>

        <el-form :model="form" label-position="top">
          <el-form-item label="风格">
            <el-radio-group v-model="form.style_mode">
              <el-radio-button label="楚风雅韵" />
              <el-radio-button label="青铜史诗" />
              <el-radio-button label="礼乐庄重" />
            </el-radio-group>
          </el-form-item>

          <el-form-item label="主角文物">
            <el-select
              v-model="form.exhibit_id"
              placeholder="请选择主角文物"
              style="width: 100%"
              filterable
            >
              <el-option
                v-for="item in exhibitOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="署名">
            <el-input v-model="form.visitor_name" placeholder="例如：阿良" />
          </el-form-item>

          <el-form-item label="日期">
            <el-input v-model="form.visit_date" placeholder="例如：2026.04.18" />
          </el-form-item>

          <el-form-item label="寄语">
            <el-input
              v-model="form.message"
              type="textarea"
              :rows="5"
              resize="none"
              placeholder="例如：把这次参观留在一张更安静、更有博物馆气质的海报里"
            />
          </el-form-item>

          <el-button type="primary" size="large" :loading="loading" @click="handleGenerate">
            生成文创海报
          </el-button>
        </el-form>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span>生成结果</span>
            <span class="head-tip">主视觉已经接后端真生图</span>
          </div>
        </template>

        <template v-if="poster">
          <div class="poster-wrap">
            <img
              v-if="posterImage"
              :src="posterImage"
              :alt="poster.title"
              class="poster-image"
            />
            <div v-else class="poster-empty">暂无图片</div>
          </div>

          <div class="poster-copy">
            <div class="eyebrow">{{ poster.style_mode }}</div>
            <h2>{{ poster.title }}</h2>
            <p class="subtitle">{{ poster.subtitle }}</p>
            <p class="body-copy">{{ poster.poster_copy || poster.commemorative_text }}</p>

            <div v-if="poster.visual_keywords?.length" class="tag-row">
              <el-tag v-for="item in poster.visual_keywords" :key="item" effect="plain">
                {{ item }}
              </el-tag>
            </div>

            <div v-if="poster.color_palette?.length" class="tag-row">
              <el-tag v-for="item in poster.color_palette" :key="item" type="success" effect="plain">
                {{ item }}
              </el-tag>
            </div>
          </div>
        </template>

        <el-empty v-else description="还没有生成海报" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createCreativePoster } from '../api/creative'
import { useRouteStore } from '../stores/routeStore'

const route = useRoute()
const router = useRouter()
const routeStore = useRouteStore()
const loading = ref(false)
const poster = ref(null)

const exhibitOptions = computed(() => routeStore.routeResult?.featured_exhibits || [])

const form = reactive({
  route_title: '',
  route_theme: '',
  route_summary: '',
  exhibit_id: null,
  exhibit_ids: [],
  visitor_name: '',
  visit_date: '',
  message: '',
  style_mode: '楚风雅韵'
})

const posterImage = computed(() => poster.value?.poster_image_url || poster.value?.fallback_cover_image_url || '')

function seedFormFromRoute() {
  const result = routeStore.routeResult
  form.route_title = result?.route_title || ''
  form.route_theme = result?.route_theme || ''
  form.route_summary = result?.route_summary || ''
  form.exhibit_ids = (result?.featured_exhibits || []).map((item) => item.id).filter(Boolean)

  const queryExhibitId = Number(route.query.exhibitId)
  if (Number.isFinite(queryExhibitId) && queryExhibitId > 0) {
    form.exhibit_id = queryExhibitId
  } else if (!form.exhibit_id && exhibitOptions.value.length) {
    form.exhibit_id = exhibitOptions.value[0].id
  }
}

async function handleGenerate() {
  loading.value = true
  try {
    poster.value = await createCreativePoster({
      route_title: form.route_title,
      route_theme: form.route_theme,
      route_summary: form.route_summary,
      exhibit_id: form.exhibit_id,
      exhibit_ids: form.exhibit_ids,
      visitor_name: form.visitor_name,
      visit_date: form.visit_date,
      message: form.message,
      style_mode: form.style_mode
    })
    ElMessage.success('文创海报生成成功')
  } catch (error) {
    ElMessage.error(error.message || '文创生成失败')
  } finally {
    loading.value = false
  }
}

function goHome() {
  router.push('/')
}

function goRouteResult() {
  router.push('/route-result')
}

onMounted(() => {
  seedFormFromRoute()
})
</script>

<style scoped>
.page-shell {
  width: min(1240px, calc(100% - 32px));
  margin: 0 auto;
  padding: 26px 0 42px;
}

.top-bar,
.top-actions,
.tag-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.top-bar {
  justify-content: space-between;
  margin-bottom: 16px;
}

.creative-layout {
  display: grid;
  grid-template-columns: minmax(0, 420px) minmax(0, 1fr);
  gap: 20px;
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

.poster-wrap {
  border-radius: 26px;
  overflow: hidden;
  background: rgba(237, 240, 239, 0.9);
  min-height: 560px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.poster-image {
  width: 100%;
  height: 100%;
  min-height: 560px;
  object-fit: cover;
}

.poster-empty {
  color: #8b93a2;
}

.poster-copy {
  margin-top: 18px;
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
}

.poster-copy h2 {
  margin: 14px 0 10px;
  font-size: 34px;
  color: #1f2937;
}

.subtitle {
  margin: 0;
  color: #a18252;
}

.body-copy {
  margin: 14px 0 0;
  color: #5d6778;
  line-height: 1.85;
}

@media (max-width: 980px) {
  .page-shell {
    width: min(1240px, calc(100% - 20px));
  }

  .creative-layout {
    grid-template-columns: 1fr;
  }

  .poster-wrap,
  .poster-image {
    min-height: 340px;
  }
}
</style>