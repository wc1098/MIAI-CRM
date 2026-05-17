import { request } from '../utils/request.js'

export function getPartnerPreference() {
	return request({
		url: '/mp/profile/preference',
	})
}

export function savePartnerPreference(data) {
	return request({
		url: '/mp/profile/preference',
		method: 'PUT',
		data,
	})
}
