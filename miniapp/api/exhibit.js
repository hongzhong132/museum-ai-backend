import { request } from './request'

export function getExhibitDetail(id) {
	return request({
		url: `/api/exhibits/${id}`,
		method: 'GET',
		timeout: 10000
	})
}

export function getExhibitAssets(id) {
	return request({
		url: `/api/exhibits/${id}/assets`,
		method: 'GET',
		timeout: 10000
	})
}

export function getExhibitGraph(id) {
	return request({
		url: `/api/exhibits/${id}/graph`,
		method: 'GET',
		timeout: 10000
	})
}

export function explainExhibit(id, data = {}) {
	return request({
		url: `/api/exhibits/${id}/explain`,
		method: 'POST',
		data,
		timeout: 15000
	})
}
