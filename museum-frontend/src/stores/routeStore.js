import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

function getSavedRouteResult() {
  try {
    const raw = localStorage.getItem('routeResult')
    return raw ? JSON.parse(raw) : null
  } catch (error) {
    console.error('读取本地路线缓存失败：', error)
    return null
  }
}

export const useRouteStore = defineStore('route', () => {
  const routeResult = ref(getSavedRouteResult())

  const hasRouteResult = computed(() => Boolean(routeResult.value))

  function setRouteResult(data) {
    routeResult.value = data
    localStorage.setItem('routeResult', JSON.stringify(data))
  }

  function clearRouteResult() {
    routeResult.value = null
    localStorage.removeItem('routeResult')
  }

  return {
    routeResult,
    hasRouteResult,
    setRouteResult,
    clearRouteResult
  }
})
