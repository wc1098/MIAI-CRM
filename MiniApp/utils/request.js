import { getToken } from './storage.js'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const API_BASE_URL_KEY = 'MIAI_MP_API_BASE_URL'
const REQUEST_TIMEOUT = 20000

export function getBaseUrl() {
	return uni.getStorageSync(API_BASE_URL_KEY) || DEFAULT_BASE_URL
}

export function setBaseUrl(url) {
	uni.setStorageSync(API_BASE_URL_KEY, url)
}

export function request(options) {
	const token = getToken()
	const url = `${getBaseUrl()}${options.url}`
	return new Promise((resolve, reject) => {
		uni.request({
			url,
			method: options.method || 'GET',
			data: options.data || {},
			timeout: options.timeout || REQUEST_TIMEOUT,
			header: {
				'Content-Type': 'application/json',
				...(token ? { Authorization: `Bearer ${token}` } : {}),
				...(options.header || {}),
			},
			success(res) {
				const body = res.data || {}
				if (res.statusCode >= 200 && res.statusCode < 300 && (body.code === 0 || body.code === 200)) {
					resolve(body.data)
					return
				}
				reject(new Error(body.msg || body.message || `请求失败(${res.statusCode})`))
			},
			fail(err) {
				console.error('[MiniApp request failed]', {
					url,
					method: options.method || 'GET',
					errMsg: err.errMsg,
				})
				reject(new Error(err.errMsg || '网络请求失败'))
			},
		})
	})
}

export function uploadFile(options) {
	const token = getToken()
	const url = `${getBaseUrl()}${options.url}`
	return new Promise((resolve, reject) => {
		uni.uploadFile({
			url,
			filePath: options.filePath,
			name: options.name || 'file',
			formData: options.formData || {},
			timeout: options.timeout || REQUEST_TIMEOUT,
			header: {
				...(token ? { Authorization: `Bearer ${token}` } : {}),
				...(options.header || {}),
			},
			success(res) {
				let body = {}
				try {
					body = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data || {})
				} catch (error) {
					reject(new Error('上传响应解析失败'))
					return
				}
				if (res.statusCode >= 200 && res.statusCode < 300 && (body.code === 0 || body.code === 200)) {
					resolve(body.data)
					return
				}
				reject(new Error(body.msg || body.message || `上传失败(${res.statusCode})`))
			},
			fail(err) {
				console.error('[MiniApp upload failed]', {
					url,
					errMsg: err.errMsg,
				})
				reject(new Error(err.errMsg || '上传失败'))
			},
		})
	})
}
