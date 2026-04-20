import axios from 'axios'

const envBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9000'
const normalizedBaseUrl = envBaseUrl.replace(/\/$/, '')

const request = axios.create({
  baseURL: normalizedBaseUrl,
  timeout: 180000
})

request.interceptors.request.use(
  (config) => {
    console.log('发起请求：', config.method, config.url, config.data)
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    console.log('响应成功：', response.config.url, response.data)
    return response.data
  },
  (error) => {
    console.error('响应失败：', error)

    let message = '请求失败'
    const detail = error?.response?.data?.detail

    if (Array.isArray(detail)) {
      message = detail
        .map((item) => {
          const field = item?.loc?.join(' -> ') || 'unknown'
          const msg = item?.msg || 'invalid'
          return `${field}: ${msg}`
        })
        .join('；')
    } else if (typeof detail === 'string' && detail.trim()) {
      message = detail
    } else if (error?.code === 'ECONNABORTED') {
      message = '请求超时：路线生成或 AI 讲解耗时较长，请稍后重试'
    } else if (error?.response?.status) {
      message = `请求失败：HTTP ${error.response.status}`
    } else if (error?.message) {
      message = error.message
    }

    return Promise.reject(new Error(message))
  }
)

export default request
