import { request, uploadFile } from '../utils/request.js'
import { uploadImageDirect } from '../utils/upload.js'

export function certificationCenter() {
	return request({
		url: '/certification/mp/center',
	})
}

export function createCertificationOrder(packageId) {
	return request({
		url: '/certification/mp/orders',
		method: 'POST',
		data: { package_id: packageId },
	})
}

export function continueCertificationPay(orderId) {
	return request({
		url: `/certification/mp/orders/${orderId}/continue-pay`,
		method: 'POST',
	})
}

export function certificationOrder(orderId) {
	return request({
		url: `/certification/mp/orders/${orderId}`,
	})
}

export function certificationApplication(applicationId) {
	return request({
		url: `/certification/mp/applications/${applicationId}`,
	})
}

export function submitRealName(data) {
	return request({
		url: '/certification/mp/real-name',
		method: 'POST',
		data,
	})
}

export async function uploadCertificationMaterial(itemCode, filePath) {
	let payload
	try {
		payload = await uploadImageDirect(filePath, 'certification_material')
	} catch (error) {
		return uploadFile({
			url: `/certification/mp/materials/${itemCode}/upload`,
			filePath,
		})
	}
	return request({
			url: `/certification/mp/materials/${itemCode}/confirm`,
			method: 'POST',
			data: payload,
		})
}

export function submitManualCertification(itemCode, payload = {}) {
	return request({
		url: '/certification/mp/manual',
		method: 'POST',
		data: { item_code: itemCode, payload },
	})
}
