import { request } from '../utils/request.js'

export function subscriptionPlans() {
	return request({ url: '/mp/subscription/plans' })
}

export function subscriptionMe() {
	return request({ url: '/mp/subscription/me' })
}

export function createSubscriptionOrder(planId) {
	return request({
		url: '/mp/subscription/orders',
		method: 'POST',
		data: { plan_id: planId },
	})
}

export function continueSubscriptionPay(orderId) {
	return request({
		url: `/mp/subscription/orders/${orderId}/pay`,
		method: 'POST',
	})
}

export function subscriptionContact(recommendationId) {
	return request({ url: `/mp/subscription/recommendations/${recommendationId}/contact` })
}
