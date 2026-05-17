import { request, uploadFile } from './request.js'

const IMAGE_QUALITY = 82

function contentTypeFromPath(path = '') {
	const lower = path.split('?')[0].toLowerCase()
	if (lower.endsWith('.png')) return 'image/png'
	if (lower.endsWith('.webp')) return 'image/webp'
	return 'image/jpeg'
}

function filenameFromPath(path = '', contentType = 'image/jpeg') {
	const raw = path.split('?')[0].split('/').pop() || `image_${Date.now()}`
	if (/\.[a-z0-9]+$/i.test(raw)) return raw
	const ext = contentType === 'image/png' ? 'png' : contentType === 'image/webp' ? 'webp' : 'jpg'
	return `${raw}.${ext}`
}

function getFileSize(filePath) {
	return new Promise((resolve) => {
		uni.getFileInfo({
			filePath,
			success: (res) => resolve(Number(res.size || 0)),
			fail: () => resolve(0),
		})
	})
}

function compressImage(filePath) {
	return new Promise((resolve) => {
		uni.compressImage({
			src: filePath,
			quality: IMAGE_QUALITY,
			success: (res) => resolve(res.tempFilePath || filePath),
			fail: () => resolve(filePath),
		})
	})
}

function uploadToOss(policy, filePath, contentType) {
	return new Promise((resolve, reject) => {
		uni.uploadFile({
			url: policy.host,
			filePath,
			name: 'file',
			formData: {
				key: policy.object_key,
				policy: policy.policy,
				OSSAccessKeyId: policy.access_key_id,
				Signature: policy.signature,
				success_action_status: '200',
				'Content-Type': contentType,
			},
			success(res) {
				if (res.statusCode >= 200 && res.statusCode < 300) {
					resolve()
					return
				}
				reject(new Error(`OSS上传失败(${res.statusCode})`))
			},
			fail(err) {
				reject(new Error(err.errMsg || 'OSS上传失败'))
			},
		})
	})
}

export async function uploadImageDirect(filePath, scene) {
	const compressedPath = await compressImage(filePath)
	const contentType = contentTypeFromPath(compressedPath || filePath)
	const size = await getFileSize(compressedPath)
	const policy = await request({
		url: '/common/upload/oss-policy',
		method: 'POST',
		data: {
			scene,
			filename: filenameFromPath(compressedPath || filePath, contentType),
			content_type: contentType,
			size,
		},
	})
	await uploadToOss(policy, compressedPath, contentType)
	return {
		scene,
		object_key: policy.object_key,
		file_url: policy.file_url,
	}
}

export { uploadFile }
