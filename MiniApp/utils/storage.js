const TOKEN_KEY = 'MIAI_MP_TOKEN'
const USER_KEY = 'MIAI_MP_USER'
const PERSON_KEY = 'MIAI_MP_PERSON'

export function getToken() {
	return uni.getStorageSync(TOKEN_KEY) || ''
}

export function setSession(data) {
	if (data.token) {
		uni.setStorageSync(TOKEN_KEY, data.token)
	}
	if (data.user) {
		uni.setStorageSync(USER_KEY, data.user)
	}
	if (data.person) {
		uni.setStorageSync(PERSON_KEY, data.person)
	}
}

export function getUser() {
	return uni.getStorageSync(USER_KEY) || null
}

export function getPerson() {
	return uni.getStorageSync(PERSON_KEY) || null
}

export function clearSession() {
	uni.removeStorageSync(TOKEN_KEY)
	uni.removeStorageSync(USER_KEY)
	uni.removeStorageSync(PERSON_KEY)
}
