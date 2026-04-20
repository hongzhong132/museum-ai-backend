const USE_REMOTE_BACKEND = true

const REMOTE_BASE_URL = 'https://museum-api-248476-6-1423637015.sh.run.tcloudbase.com'
const LOCAL_BASE_URL = 'http://10.110.62.221:9000'
const DEFAULT_TIMEOUT = 60000

const BASE_URL = USE_REMOTE_BACKEND ? REMOTE_BASE_URL : LOCAL_BASE_URL

export function request({ url, method = 'GET', data = {}, header = {}, timeout = DEFAULT_TIMEOUT }) {
	return new Promise((resolve, reject) => {
		uni.request({
			url: `${BASE_URL}${url}`,
			method,
			data,
			timeout,
			header: {
				'Content-Type': 'application/json',
				...header
			},
			success: (res) => {
				const { statusCode, data: resData } = res
				if (statusCode >= 200 && statusCode < 300) {
					resolve(resData)
				} else {
					reject({
						message: `请求失败，状态码：${statusCode}`,
						response: res,
						data: resData
					})
				}
			},
			fail: (err) => {
				reject({
					message:
						err?.errMsg?.includes('timeout')
							? '请求超时，请稍后重试'
							: '网络请求失败，请检查后端是否启动，或检查地址是否可访问',
					error: err
				})
			}
		})
	})
}