import request from './request'

export function generateRoute(data) {
  return request({
    url: '/api/route/generate',
    method: 'post',
    data
  })
}

export function replanRoute(data) {
  return request({
    url: '/api/route/replan',
    method: 'post',
    data
  })
}
