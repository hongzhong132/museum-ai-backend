import App from './App'

// #ifndef VUE3
import Vue from 'vue'
import './uni.promisify.adaptor'

Vue.config.productionTip = false
App.mpType = 'app'

// #ifdef MP-WEIXIN
if (wx.cloud) {
  wx.cloud.init({
    env: 'chuyun-guide-d7gszfnoffd3c151c',
    traceUser: true
  })
} else {
  console.error('当前微信基础库不支持 wx.cloud，请升级微信开发者工具或基础库版本')
}
// #endif

const app = new Vue({
  ...App
})
app.$mount()
// #endif

// #ifdef VUE3
import { createSSRApp } from 'vue'

export function createApp() {
  // #ifdef MP-WEIXIN
  if (wx.cloud) {
    wx.cloud.init({
      env: 'chuyun-guide-d7gszfnoffd3c151c',
      traceUser: true
    })
  } else {
    console.error('当前微信基础库不支持 wx.cloud，请升级微信开发者工具或基础库版本')
  }
  // #endif

  const app = createSSRApp(App)
  return {
    app
  }
}
// #endif