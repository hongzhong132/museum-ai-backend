import request from './request'

export function createCreativePoster(data) {
  return request({
    url: '/api/exhibits/creative/poster',
    method: 'post',
    data
  })
}
