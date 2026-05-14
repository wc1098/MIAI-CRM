import { mpLogin, mpMe } from '../api/mpAuth.js'
import { getPerson, getToken, setSession } from './storage.js'

let sessionPromise = null

function wxLoginCode() {
	return new Promise((resolve) => {
		uni.login({
			provider: 'weixin',
			success: (res) => resolve(res.code || ''),
			fail: () => resolve('mock:dev-openid'),
		})
	})
}

export async function ensureMpSession(options = {}) {
	const force = Boolean(options.force)
	if (!force && getToken()) {
		if (getPerson()) {
			return { is_registered: true, person: getPerson() }
		}
		try {
			const me = await mpMe()
			setSession(me)
			return me
		} catch (error) {
			// token 失效时继续走静默登录。
		}
	}
	if (!sessionPromise || force) {
		sessionPromise = (async () => {
			const code = await wxLoginCode()
			const result = await mpLogin({ code })
			setSession(result)
			return result
		})().finally(() => {
			sessionPromise = null
		})
	}
	return sessionPromise
}

export async function ensureRegisteredSession() {
	const result = await ensureMpSession()
	if (result && result.person) return result
	return null
}
