import { request } from '../utils/request.js'

export function plazaList(params = {}) {
	return request({
		url: '/mp/plaza/list',
		data: params,
	})
}

export function plazaDetail(displayNo) {
	return request({
		url: `/mp/plaza/detail/${displayNo}`,
	})
}

export function likeProfile(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/like`,
		method: 'POST',
	})
}

export function unlikeProfile(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/like`,
		method: 'DELETE',
	})
}

export function favoriteProfile(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/favorite`,
		method: 'POST',
	})
}

export function unfavoriteProfile(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/favorite`,
		method: 'DELETE',
	})
}

export function unlockByHeartbeat(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/heartbeat`,
		method: 'POST',
	})
}

export function unlockProgress(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/progress`,
	})
}

export function completeUnlockTask(displayNo, taskCode) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/task/${taskCode}`,
		method: 'POST',
	})
}

export function unlockQuestions(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/questions`,
	})
}

export function answerUnlockQuestion(displayNo, questionId, answerValue) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/questions/${questionId}/answer`,
		method: 'POST',
		data: { answer_value: answerValue },
	})
}

export function unlockByCoupon(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/coupon`,
		method: 'POST',
	})
}

export function unlockByPay(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/pay`,
		method: 'POST',
	})
}

export function finalTaskFreeUnlock(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/final/task-free`,
		method: 'POST',
	})
}

export function finalCouponUnlock(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/final/coupon`,
		method: 'POST',
	})
}

export function finalPayUnlock(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/final/pay`,
		method: 'POST',
	})
}

export function unlockContact(displayNo) {
	return request({
		url: `/mp/plaza/${displayNo}/unlock/contact`,
	})
}

export function continueUnlockPay(orderId) {
	return request({
		url: `/mp/plaza/unlock/pay/${orderId}/continue`,
		method: 'POST',
	})
}
