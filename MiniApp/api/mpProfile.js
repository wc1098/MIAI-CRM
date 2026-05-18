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

export function mineCenter() {
	return request({ url: '/mp/mine/center' })
}

export function mineProfile() {
	return request({ url: '/mp/mine/profile' })
}

export function saveMineProfile(data) {
	return request({
		url: '/mp/mine/profile',
		method: 'PUT',
		data,
	})
}

export function saveMinePrivacy(data) {
	return request({
		url: '/mp/mine/privacy',
		method: 'PUT',
		data,
	})
}

export function mineLikes(params = {}) {
	return request({
		url: '/mp/mine/likes',
		data: params,
	})
}

export function mineFavorites(params = {}) {
	return request({
		url: '/mp/mine/favorites',
		data: params,
	})
}

export function mineUnlocks(params = {}) {
	return request({
		url: '/mp/mine/unlocks',
		data: params,
	})
}

export function mineEvents(params = {}) {
	return request({
		url: '/mp/mine/events',
		data: params,
	})
}
