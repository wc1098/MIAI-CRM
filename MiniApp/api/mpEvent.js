import { request } from '../utils/request.js'

export function eventList(params = {}) {
	return request({
		url: '/mp/event/list',
		data: params,
	})
}

export function eventDetail(id) {
	return request({
		url: `/mp/event/detail/${id}`,
	})
}

export function myEventRegistration(id) {
	return request({
		url: `/mp/event/my-registration/${id}`,
	})
}

export function registerEvent(id, data = {}) {
	return request({
		url: `/mp/event/register/${id}`,
		method: 'POST',
		data,
	})
}

export function continueEventPay(registrationId) {
	return request({
		url: `/mp/event/pay/${registrationId}`,
		method: 'POST',
	})
}

export function checkinEvent(id, data = {}) {
	return request({
		url: `/mp/event/checkin/${id}`,
		method: 'POST',
		data,
	})
}
