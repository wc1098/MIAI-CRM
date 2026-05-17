<template>
	<view class="page contact-page">
		<view class="card">
			<image class="avatar" :src="avatarUrl(target.avatar_url)" mode="aspectFill"></image>
			<text class="name">{{ target.display_name || '觅AI用户' }}</text>
			<text class="meta">ID {{ target.display_no }}</text>
			<text class="phone">{{ mobile }}</text>
			<text class="tip">{{ copy.contact || '请真诚沟通，尊重对方意愿；若对方明确拒绝，请停止打扰。' }}</text>
			<button class="primary-btn" @tap="copyPhone">复制手机号</button>
			<button class="call-btn" @tap="callPhone">拨打电话</button>
		</view>
	</view>
</template>

<script>
import { unlockContact } from '../../../api/mpPlaza.js'
import { ossImage } from '../../../utils/ossImage.js'

export default {
	data() {
		return { displayNo: '', data: {} }
	},
	computed: {
		target() { return this.data.target || {} },
		copy() { return this.data.copy || {} },
		mobile() { return this.data.mobile || '' },
	},
	onLoad(options) {
		this.displayNo = options.display_no || ''
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		avatarUrl(url) {
			return ossImage(url, { width: 180, height: 180 }) || '/static/logo.png'
		},
		async load() {
			if (!this.displayNo) return
			try {
				this.data = await unlockContact(this.displayNo)
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			}
		},
		copyPhone() {
			if (!this.mobile) return
			uni.setClipboardData({ data: this.mobile })
		},
		callPhone() {
			if (!this.mobile) return
			uni.makePhoneCall({ phoneNumber: this.mobile })
		},
	},
}
</script>

<style>
page { background: #f7f1e8; }
.contact-page { min-height: 100vh; padding: 56rpx 28rpx; color: #3f2f2a; }
.card { padding: 38rpx 32rpx; border-radius: 34rpx; background: #fffaf3; text-align: center; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); }
.avatar { width: 150rpx; height: 150rpx; border-radius: 32rpx; }
.name { display: block; margin-top: 18rpx; font-size: 38rpx; font-weight: 700; }
.meta { display: block; margin-top: 8rpx; color: #8a776a; font-size: 26rpx; }
.phone { display: block; margin: 42rpx 0 20rpx; font-size: 58rpx; font-weight: 800; color: #c95d65; letter-spacing: 2rpx; }
.tip { display: block; color: #7d6a5e; font-size: 27rpx; line-height: 1.7; }
.primary-btn, .call-btn { height: 88rpx; margin-top: 24rpx; border-radius: 999rpx; font-size: 28rpx; font-weight: 700; }
.primary-btn { color: #fff; background: #c95d65; }
.call-btn { color: #6d7e60; background: #edf3e6; }
</style>
