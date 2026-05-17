import { request, uploadFile } from '../utils/request.js'
import { uploadImageDirect } from '../utils/upload.js'

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

export async function uploadRegisterPhoto(filePath) {
	let payload
	try {
		payload = await uploadImageDirect(filePath, 'mp_register_photo')
	} catch (error) {
		return uploadFile({
			url: '/mp/auth/register-photo/upload',
			filePath,
		})
	}
	return request({
			url: '/mp/auth/register-photo/confirm',
			method: 'POST',
			data: payload,
		})
}

export function mpMe() {
	return request({
		url: '/mp/auth/me',
	})
}
