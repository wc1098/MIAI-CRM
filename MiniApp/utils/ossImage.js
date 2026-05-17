const OSS_HOST_RE = /(^https?:\/\/.*\.oss-[^/]+\.aliyuncs\.com\/)|(^https?:\/\/.*aliyuncs\.com\/.*\/uploads\/)/i

function shouldProcess(url) {
	if (!url || typeof url !== 'string') return false
	if (!/^https?:\/\//i.test(url)) return false
	if (url.includes('x-oss-process=')) return false
	return OSS_HOST_RE.test(url)
}

function appendProcess(url, process) {
	if (!shouldProcess(url)) return url
	const separator = url.includes('?') ? '&' : '?'
	return `${url}${separator}x-oss-process=${encodeURIComponent(process)}`
}

export function ossImage(url, options = {}) {
	const width = Number(options.width || options.w || 300)
	const height = Number(options.height || options.h || width)
	const quality = Number(options.quality || options.q || 75)
	const mode = options.mode || 'fill'
	const format = options.format || 'webp'
	const resize = mode === 'lfit' ? `m_lfit,w_${width}` : `m_fill,w_${width},h_${height}`
	const process = `image/resize,${resize}/quality,q_${quality}/format,${format}`
	return appendProcess(url, process)
}

export function ossPreview(url, options = {}) {
	const width = Number(options.width || options.w || 1200)
	const quality = Number(options.quality || options.q || 85)
	const format = options.format || 'webp'
	return appendProcess(url, `image/resize,m_lfit,w_${width}/quality,q_${quality}/format,${format}`)
}

export function ossImageList(urls, options = {}) {
	return (urls || []).map((url) => ossPreview(url, options))
}
