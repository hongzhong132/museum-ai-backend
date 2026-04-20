<template>
  <div class="home-page">
    <section class="home-shell surface-card">
      <div class="intro-block">
        <div class="eyebrow">HUBEI PROVINCIAL MUSEUM · AI GUIDE</div>
        <h1>输入参观需求，直接生成路线</h1>
        <p>
          这一页只保留真正要用的内容：时间、兴趣、目标。先把路线主链跑通，再进入讲解、图谱和文创。
        </p>
      </div>

      <el-form :model="form" label-position="top" class="smart-form">
        <div class="form-grid form-grid--two">
          <el-form-item label="可用时间">
            <el-input-number
              v-model="form.available_minutes"
              :min="30"
              :max="300"
              :step="30"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item label="是否首次参观">
            <div class="switch-box">
              <span>{{ form.first_visit ? '是，想先抓主线' : '不是，想更有针对性' }}</span>
              <el-switch v-model="form.first_visit" />
            </div>
          </el-form-item>
        </div>

        <el-form-item label="兴趣方向">
          <el-select
            v-model="form.interests"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择兴趣方向"
            style="width: 100%"
          >
            <el-option
              v-for="option in interestOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <div class="quick-tags">
          <button
            v-for="option in interestOptions"
            :key="`quick-${option.value}`"
            class="quick-tag"
            :class="{ 'is-active': form.interests.includes(option.value) }"
            type="button"
            @click="toggleInterest(option.value)"
          >
            {{ option.label }}
          </button>
        </div>

        <el-form-item label="参观目标">
          <el-input
            v-model="form.goal"
            type="textarea"
            :rows="6"
            resize="none"
            placeholder="例如：我只有 1 小时，想优先看最有代表性的楚文化文物，希望路线不要太绕"
          />
        </el-form-item>

        <div class="action-row">
          <el-button type="primary" size="large" :loading="loading" @click="handleGenerate">
            生成路线
          </el-button>
          <el-button size="large" @click="handleReset">重置</el-button>
          <el-button
            v-if="hasHistory"
            type="success"
            plain
            size="large"
            @click="goLastResult"
          >
            查看上次结果
          </el-button>
        </div>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { generateRoute } from '../api/route'
import { useRouteStore } from '../stores/routeStore'

const router = useRouter()
const routeStore = useRouteStore()
const loading = ref(false)

const interestOptions = [
  { label: '曾侯乙', value: '曾侯乙' },
  { label: '楚文化', value: '楚文化' },
  { label: '青铜器', value: '青铜器' },
  { label: '漆木器', value: '漆木器' },
  { label: '越王勾践剑专题', value: '越王勾践剑专题' }
]

const form = reactive({
  available_minutes: 90,
  interests: ['楚文化'],
  first_visit: true,
  goal: ''
})

const hasHistory = computed(() => routeStore.hasRouteResult)

function handleReset() {
  form.available_minutes = 90
  form.interests = ['楚文化']
  form.first_visit = true
  form.goal = ''
}

function goLastResult() {
  router.push('/route-result')
}

function toggleInterest(value) {
  if (form.interests.includes(value)) {
    form.interests = form.interests.filter((item) => item !== value)
    return
  }
  form.interests = [...form.interests, value]
}

async function handleGenerate() {
  if (!form.interests.length) {
    ElMessage.warning('请至少选择一个兴趣方向')
    return
  }

  loading.value = true
  try {
    const payload = {
      available_minutes: form.available_minutes,
      interest: form.interests.join('、'),
      first_visit: form.first_visit,
      visit_goal: form.goal
    }

    const res = await generateRoute(payload)
    routeStore.setRouteResult(res)
    ElMessage.success('导览路线生成成功')
    router.push('/route-result')
  } catch (error) {
    ElMessage.error(error.message || '生成失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home-page {
  min-height: calc(100vh - 74px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 16px;
}

.home-shell {
  width: min(760px, 100%);
  padding: 28px;
}

.intro-block {
  margin-bottom: 18px;
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

h1 {
  margin: 14px 0 12px;
  font-size: clamp(34px, 4vw, 48px);
  line-height: 1.14;
  color: #1f2937;
}

p {
  margin: 0;
  color: #5d6778;
  line-height: 1.8;
}

.smart-form {
  margin-top: 18px;
}

.form-grid {
  display: grid;
  gap: 16px;
}

.form-grid--two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.switch-box {
  min-height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  background: rgba(244, 239, 232, 0.84);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #5d6778;
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: -4px 0 18px;
}

.quick-tag {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(180, 122, 61, 0.18);
  background: rgba(255, 255, 255, 0.72);
  color: #5d6778;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-tag:hover,
.quick-tag.is-active {
  border-color: rgba(180, 122, 61, 0.42);
  background: rgba(180, 122, 61, 0.12);
  color: #8c5b2d;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 768px) {
  .home-page {
    padding: 18px 12px;
  }

  .home-shell {
    padding: 20px;
  }

  h1 {
    font-size: 34px;
  }

  .form-grid--two {
    grid-template-columns: 1fr;
  }

  .action-row :deep(.el-button) {
    width: 100%;
    margin-left: 0 !important;
  }
}
</style>