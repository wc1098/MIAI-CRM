import { request } from '../utils/request.js'

export function plazaList(params = {}) {
	return request({
		url: '/mp/plaza/list',
		data: params,
	})
}
