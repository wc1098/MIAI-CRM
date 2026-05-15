<template>
	<view class="page final-page">
		<view class="card">
			<image class="avatar" :src="target.avatar_url || '/static/logo.png'" mode="aspectFill"></image>
			<text class="title">最后一步</text>
			<text class="desc">{{ copy.final || '解锁后可查看对方手机号，本次解锁后可重复查看，不重复收费。' }}</text>
			<view class="score">{{ progress.score || 0 }}/{{ progress.target_score || 100 }}</view>
			<text class="hint">今日剩余解锁 {{ daily.remaining || 0 }} 次</text>
		</view>

		<view class="actions">
			<button v-if="data.is_unlocked" class="primary-btn" @tap="goContact">查看手机号</button>
			<button v-else-if="coupon.available" class="primary-btn" @tap="unlockCoupon">使用免费券解锁</button>
			<button v-else-if="progress.free_unlock_eligible" class="primary-btn" @tap="unlockTask">用心动值解锁</button>
			<button v-else-if="payment.allow_paid_boost" class="pay-btn" @tap="unlockPay">付费直接解锁 ¥{{ payment.price || '0.00' }}</button>
			<button class="ghost-btn" @tap="backProgress">继续提升心动值</button>
		</view>
	</view>
</template>

<script>
import { finalCouponUnlock, finalPayUnlock, finalTaskFreeUnlock, unlockProgress } from '../../../api/mpPlaza.js'

export default {
	data() {
		return { displayNo: '', data: {} }
	},
	computed: {
		target() { return this.data.target || {} },
		progress() { return this.data.progress || {} },
		coupon() { return this.data.coupon || {} },
		payment() { return this.data.payment || {} },
		daily() { return this.data.daily_unlock || {} },
		copy() { return this.data.copy || {} },
	},
	onLoad(options) {
		this.displayNo = options.display_no || ''
	},
	onShow() {
		this.load()
	},
	methods: {
		async load() {
			if (!this.displayNo) return
			this.data = await unlockProgress(this.displayNo)
		},
		async unlockTask() {
			try {
				await finalTaskFreeUnlock(this.displayNo)
				this.goContact()
			} catch (error) {
				uni.showToast({ title: error.message || '解锁失败', icon: 'none' })
			}
		},
		async unlockCoupon() {
			try {
				await finalCouponUnlock(this.displayNo)
				this.goContact()
			} catch (error) {
				uni.showToast({ title: error.message || '解锁失败', icon: 'none' })
			}
		},
		async unlockPay() {
			try {
				const result = await finalPayUnlock(this.displayNo)
				if (result.payment && result.payment.paid) {
					this.goContact()
					return
				}
				if (result.payment) {
					const paid = await this.requestPayment(result.payment.wechat_pay || result.payment.pay_payload)
					if (paid) {
						this.goContact()
					} else {
						uni.showToast({ title: '支付未完成，可稍后继续', icon: 'none' })
					}
				}
			} catch (error) {
				uni.showToast({ title: error.message || '发起支付失败', icon: 'none' })
			}
		},
		requestPayment(payload) {
			return new Promise((resolve) => {
				let source = payload
				if (typeof source === 'string') {
					try { source = JSON.parse(source) } catch (error) { source = null }
				}
				const raw = source && (source.pay_info || source.payData || source.wechat_pay || source)
				const payData = {
					timeStamp: raw && (raw.timeStamp || raw.time_stamp),
					nonceStr: raw && (raw.nonceStr || raw.nonce_str),
					package: raw && (raw.package || raw.package_info),
					signType: raw && (raw.signType || raw.sign_type),
					paySign: raw && (raw.paySign || raw.pay_sign),
				}
				if (!payData.timeStamp || !payData.nonceStr || !payData.package || !payData.signType || !payData.paySign) {
					uni.showToast({ title: '订单已创建，请稍后继续支付', icon: 'none' })
					resolve(false)
					return
				}
				uni.requestPayment({ ...payData, success: () => resolve(true), fail: () => resolve(false) })
			})
		},
		goContact() {
			uni.redirectTo({ url: `/pages/plaza/unlock/contact?display_no=${this.displayNo}` })
		},
		backProgress() {
			uni.navigateBack()
		},
	},
}
</script>

<style>
page { background: #f7f1e8; }
.final-page { min-height: 100vh; padding: 48rpx 28rpx; color: #3f2f2a; }
.card, .actions { padding: 34rpx; border-radius: 32rpx; background: #fffaf3; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); text-align: center; }
.avatar { width: 150rpx; height: 150rpx; border-radius: 32rpx; }
.title { display: block; margin-top: 22rpx; font-size: 42rpx; font-weight: 700; }
.desc, .hint { display: block; margin-top: 18rpx; color: #7d6a5e; font-size: 27rpx; line-height: 1.7; }
.score { margin: 30rpx auto 8rpx; width: 220rpx; height: 220rpx; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 38rpx; font-weight: 700; background: linear-gradient(135deg, #c95d65, #8ea078); }
.actions { margin-top: 26rpx; }
.primary-btn, .pay-btn, .ghost-btn { height: 88rpx; margin-top: 18rpx; border-radius: 999rpx; font-size: 28rpx; font-weight: 700; }
.primary-btn { color: #fff; background: #c95d65; }
.pay-btn { color: #6d7e60; background: #edf3e6; }
.ghost-btn { color: #6d5a50; background: #f1e7dc; }
</style>
