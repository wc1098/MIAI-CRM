import { request, uploadFile } from '../utils/request.js'

export function mpLogin(data) {
	return request({
		url: '/mp/auth/login',
		method: 'POST',
		data,
	})
}

export function mpRegister(data) {
	return request({
		url: '/mp/auth/register',
		method: 'POST',
		data,
	})
}

export function mpRegisterOptions() {
	return request({
		url: '/mp/auth/register-options',
	})
}

export function uploadRegisterPhoto(filePath) {
	return uploadFile({
		url: '/mp/auth/register-photo/upload',
		filePath,
	})
}

export function mpMe() {
	return request({
		url: '/mp/auth/me',
	})
}
