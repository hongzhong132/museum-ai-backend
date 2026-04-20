import { request } from './request'

export function generateRoute(data) {
	return request({
		url: '/api/route/generate',
		method: 'POST',
		data
	})
}

export function replanRoute(data) {
	return request({
		url: '/api/route/replan',
		method: 'POST',
		data
	})
}
