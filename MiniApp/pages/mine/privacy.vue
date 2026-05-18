<template>
	<view class="page privacy-page">
		<view class="hero-card">
			<text class="title">隐私设置</text>
			<text class="desc">开启隐身后，你不会进入广场推荐和上墙类展示；后台仍可正常维护资料。</text>
		</view>

		<view class="setting-card">
			<view>
				<text class="setting-title">隐身模式</text>
				<text class="setting-desc">{{ isInvisible ? '当前已隐藏公开展示' : '当前资料可正常展示' }}</text>
			</view>
			<switch :checked="isInvisible" color="#c95d65" @change="onSwitch" />
		</view>

		<button class="save-btn" :loading="saving" @tap="submit">保存设置</button>
	</view>
</template>

<script>
import { mineCenter, saveMinePrivacy } from '../../api/mpProfile.js'
import { ensureRegisteredSession } from '../../utils/mpSession.js'

export default {
	data() {
		return { isInvisible: false, saving: false }
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		async load() {
			try {
				await ensureRegisteredSession()
				const data = await mineCenter()
				this.isInvisible = !!(data.user && data.user.is_invisible)
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			}
		},
		onSwitch(event) {
			this.isInvisible = !!event.detail.value
		},
		async submit() {
			this.saving = true
			try {
				await saveMinePrivacy({ is_invisible: this.isInvisible })
				uni.showToast({ title: '已保存', icon: 'success' })
				setTimeout(() => uni.navigateBack(), 500)
			} catch (error) {
				uni.showToast({ title: error.message || '保存失败', icon: 'none' })
			} finally {
				this.saving = false
			}
		},
	},
}
</script>

<style>
.privacy-page { min-height: 100vh; background: #f7f4ef; padding: 24rpx; box-sizing: border-box; }
.hero-card, .setting-card { background: #fffaf3; border-radius: 28rpx; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); padding: 28rpx; margin-bottom: 22rpx; }
.title, .desc, .setting-title, .setting-desc { display: block; }
.title { color: #3f2d28; font-size: 40rpx; font-weight: 900; }
.desc, .setting-desc { color: #8d7f78; font-size: 26rpx; line-height: 1.6; margin-top: 10rpx; }
.setting-card { display: flex; align-items: center; justify-content: space-between; gap: 24rpx; }
.setting-title { color: #4b342d; font-size: 32rpx; font-weight: 900; }
.save-btn { height: 88rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 30rpx; font-weight: 800; margin-top: 36rpx; }
</style>
