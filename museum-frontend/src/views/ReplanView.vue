<template>
  <div class="page-shell">
    <section class="intro-row mb20">
      <div class="intro-copy surface-card">
        <div class="eyebrow">REPLAN YOUR VISIT</div>
        <h1>根据现场位置和剩余时间，快速重规划后半程路线</h1>
        <p>
          这个页面适合展示系统不是“一次性生成就结束”，而是可以在参观过程中根据位置变化和新目标继续调整。
        </p>
      </div>

      <el-card class="surface-card summary-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span>当前路线摘要</span>
          </div>
        </template>

        <template v-if="routeResult">
          <h3 class="summary-title">{{ routeResult.route_title || '当前路线' }}</h3>
          <p class="summary-theme" v-if="routeResult.route_theme">{{ routeResult.route_theme }}</p>
          <p class="summary-text">{{ routeResult.route_summary || '暂无摘要' }}</p>
        </template>
        <el-empty v-else description="还没有初始路线" />
      </el-card>
    </section>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span>导览重规划</span>
          <div class="header-actions">
            <el-button @click="goBack">返回路线结果</el-button>
            <el-button @click="goHome">回首页</el-button>
          </div>
        </div>
      </template>

      <template v-if="hallOptions.length">
        <el-form :model="form" label-position="top">
          <div class="form-grid form-grid--two">
            <el-form-item label="当前所在展区">
              <el-select
                v-model="form.current_hall_id"
                placeholder="请选择当前展区"
                style="width: 100%"
              >
                <el-option
                  v-for="hall in hallOptions"
                  :key="hall.id ?? hall.hall_id ?? hall.name"
                  :label="hall.name || hall.hall_name"
                  :value="hall.id ?? hall.hall_id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="剩余时间">
              <el-input-number
                v-model="form.remaining_minutes"
                :min="10"
                :max="240"
                :step="10"
                style="width: 100%"
              />
            </el-form-item>
          </div>

          <el-form-item label="已访问展区">
            <el-select
              v-model="form.visited_hall_ids"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择已经逛过的展区"
              style="width: 100%"
            >
              <el-option
                v-for="hall in hallOptions"
                :key="hall.id ?? hall.hall_id ?? hall.name"
                :label="hall.name || hall.hall_name"
                :value="hall.id ?? hall.hall_id"
              />
            </el-select>
          </el-form-item>

          <div class="hall-preview">
            <span class="preview-label">当前路线包含展区：</span>
            <div class="preview-tags">
              <el-tag
                v-for="hall in hallOptions"
                :key="`preview-${hall.id ?? hall.hall_id ?? hall.name}`"
                effect="plain"
              >
                {{ hall.name || hall.hall_name }}
              </el-tag>
            </div>
          </div>

          <el-form-item label="新目标">
            <el-input
              v-model="form.updated_goal"
              type="textarea"
              :rows="5"
              resize="none"
              placeholder="例如：我想把重点放到曾侯乙和青铜器，不想走太远，希望内容更集中"
            />
          </el-form-item>

          <div class="tips-panel">
            <div class="tip-card">
              <strong>适合什么场景</strong>
              <p>时间突然变短、现场想改重点、已经看过部分馆区，都可以直接在这里重规划。</p>
            </div>
            <div class="tip-card">
              <strong>推荐答辩说法</strong>
              <p>这体现了系统并非静态路线推荐，而是能根据用户状态变化做实时导览调整。</p>
            </div>
          </div>

          <div class="action-row">
            <el-button type="primary" size="large" :loading="loading" @click="handleReplan">
              生成新路线
            </el-button>
            <el-button size="large" @click="goBack">返回路线结果</el-button>
          </div>
        </el-form>
      </template>

      <el-empty v-else description="当前没有可用于重规划的路线数据，请先生成初始路线">
        <el-button type="primary" @click="goHome">去首页生成路线</el-button>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup>
import { computed, reactive, watchEffect, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { replanRoute } from '../api/route'
import { useRouteStore } from '../stores/routeStore'

const router = useRouter()
const routeStore = useRouteStore()
const loading = ref(false)

const routeResult = computed(() => routeStore.routeResult)
const hallOptions = computed(() => routeResult.value?.selected_halls || [])

const form = reactive({
  current_hall_id: null,
  visited_hall_ids: [],
  remaining_minutes: 60,
  updated_goal: ''
})

watchEffect(() => {
  if (!form.current_hall_id && hallOptions.value.length) {
    const firstHall = hallOptions.value[0]
    form.current_hall_id = firstHall.id ?? firstHall.hall_id ?? null
  }
})

function goBack() {
  router.push('/route-result')
}

function goHome() {
  router.push('/')
}

async function handleReplan() {
  if (!form.current_hall_id) {
    ElMessage.warning('请先选择当前所在展区')
    return
  }

  loading.value = true
  try {
    const payload = {
      current_hall_id: form.current_hall_id,
      visited_hall_ids: form.visited_hall_ids,
      remaining_minutes: form.remaining_minutes,
      updated_goal: form.updated_goal
    }

    const res = await replanRoute(payload)
    routeStore.setRouteResult(res)
    ElMessage.success('重规划成功')
    router.push('/route-result')
  } catch (error) {
    ElMessage.error(error.message || '重规划失败，请检查接口字段')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}

.mb20 {
  margin-bottom: 20px;
}

.intro-row {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 20px;
}

.intro-copy {
  padding: 28px;
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

.intro-copy h1 {
  margin: 16px 0 12px;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.25;
  color: var(--ink-900);
}

.intro-copy p,
.summary-text,
.tip-card p {
  margin: 0;
  line-height: 1.9;
  color: var(--ink-600);
}

.summary-card {
  min-height: 100%;
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

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-title {
  margin: 0 0 10px;
  color: var(--ink-900);
  font-size: 22px;
}

.summary-theme {
  margin: 0 0 10px;
  color: var(--brand-700);
  line-height: 1.8;
  font-weight: 600;
}

.form-grid {
  display: grid;
  gap: 16px;
}

.form-grid--two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.hall-preview {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 18px;
  background: #f8f7f4;
  border: 1px solid rgba(19, 24, 36, 0.06);
}

.preview-label {
  display: block;
  margin-bottom: 10px;
  color: var(--ink-700);
  font-weight: 600;
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tips-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.tip-card {
  padding: 18px;
  border-radius: 18px;
  background: #f8f7f4;
  border: 1px solid rgba(19, 24, 36, 0.06);
}

.tip-card strong {
  display: block;
  margin-bottom: 10px;
  color: var(--ink-900);
}

.action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 1024px) {
  .intro-row,
  .form-grid--two,
  .tips-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-shell {
    width: min(1180px, calc(100% - 24px));
    padding: 20px 0 28px;
  }

  .intro-copy {
    padding: 20px;
  }
}
</style>
