import request from './request'

export function getExhibits() {
  return request({
    url: '/api/exhibits/',
    method: 'get'
  })
}

export function getExhibitDetail(id) {
  return request({
    url: `/api/exhibits/${id}`,
    method: 'get'
  })
}

export function getExhibitAssets(id) {
  return request({
    url: `/api/exhibits/${id}/assets`,
    method: 'get'
  })
}

export function getExhibitGraph(id) {
  return request({
    url: `/api/exhibits/${id}/graph`,
    method: 'get'
  })
}

export function getRelatedExhibits(id) {
  return request({
    url: `/api/exhibits/${id}/related`,
    method: 'get'
  })
}

export function explainExhibit(
  id,
  data = {
    mode: 'normal',
    current_context_exhibit_id: null
  }
) {
  return request({
    url: `/api/exhibits/${id}/explain`,
    method: 'post',
    data
  })
}
