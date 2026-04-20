import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import RouteResultView from '../views/RouteResultView.vue'
import ExhibitDetailView from '../views/ExhibitDetailView.vue'
import ExhibitGraphView from '../views/ExhibitGraphView.vue'
import ExhibitRelatedView from '../views/ExhibitRelatedView.vue'
import CreativeView from '../views/CreativeView.vue'
import ReplanView from '../views/ReplanView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { title: '楚韵引航｜生成路线' }
  },
  {
    path: '/route-result',
    name: 'route-result',
    component: RouteResultView,
    meta: { title: '楚韵引航｜路线结果' }
  },
  {
    path: '/exhibit/:id',
    name: 'exhibit-detail',
    component: ExhibitDetailView,
    props: true,
    meta: { title: '楚韵引航｜展品详情' }
  },
  {
    path: '/exhibit/:id/graph',
    name: 'exhibit-graph',
    component: ExhibitGraphView,
    props: true,
    meta: { title: '楚韵引航｜知识图谱' }
  },
  {
    path: '/exhibit/:id/related',
    name: 'exhibit-related',
    component: ExhibitRelatedView,
    props: true,
    meta: { title: '楚韵引航｜相关文物' }
  },
  {
    path: '/creative',
    name: 'creative',
    component: CreativeView,
    meta: { title: '楚韵引航｜AI 文创' }
  },
  {
    path: '/replan',
    name: 'replan',
    component: ReplanView,
    meta: { title: '楚韵引航｜重规划' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0, behavior: 'smooth' }
  }
})

router.afterEach((to) => {
  document.title = to.meta?.title || '楚韵引航'
})

export default router
