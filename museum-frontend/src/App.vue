<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="site-header__inner">
        <button class="brand-block" type="button" @click="goHome">
          <div class="brand-mark">楚</div>
          <div>
            <div class="brand-title">楚韵引航</div>
            <div class="brand-subtitle">湖北省博物馆 AI 智慧导览 Web 端</div>
          </div>
        </button>

        <nav class="site-nav">
          <button
            class="nav-link"
            :class="{ 'is-active': route.path === '/' }"
            type="button"
            @click="goHome"
          >
            首页
          </button>
          <button
            class="nav-link"
            :class="{ 'is-active': route.path.startsWith('/route-result') }"
            type="button"
            @click="goRouteResult"
          >
            路线结果
          </button>
          <button
            class="nav-link"
            :class="{ 'is-active': route.path.startsWith('/replan') }"
            type="button"
            @click="goReplan"
          >
            重规划
          </button>
          <button
            class="nav-link"
            :class="{ 'is-active': route.path.startsWith('/creative') }"
            type="button"
            @click="goCreative"
          >
            AI 文创
          </button>
        </nav>
      </div>
    </header>

    <main class="main-shell">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

function goHome() {
  router.push('/')
}

function goRouteResult() {
  router.push('/route-result')
}

function goReplan() {
  router.push('/replan')
}

function goCreative() {
  router.push('/creative')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 30;
  backdrop-filter: blur(14px);
  background: rgba(56, 64, 79, 0.9);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.site-header__inner {
  width: min(1240px, calc(100% - 32px));
  margin: 0 auto;
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 12px 0;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 14px;
  background: transparent;
  border: none;
  color: #fff;
  padding: 0;
  cursor: pointer;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #d2a858, #8c5b2d);
  color: #fff;
  box-shadow: 0 10px 24px rgba(140, 91, 45, 0.28);
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.brand-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.nav-link {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.84);
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-link:hover,
.nav-link.is-active {
  color: #fff;
  border-color: rgba(217, 181, 116, 0.55);
  background: rgba(217, 181, 116, 0.14);
}

.main-shell {
  width: 100%;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 900px) {
  .site-header__inner {
    width: min(1240px, calc(100% - 20px));
    align-items: flex-start;
    flex-direction: column;
  }

  .site-nav {
    width: 100%;
  }
}
</style>