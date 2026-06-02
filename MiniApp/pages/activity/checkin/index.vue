<template>
	<view class="page">
		<view class="card">
			<text class="kicker">活动现场签到</text>
			<text class="title">{{ event.title || '扫码签到' }}</text>
			<text class="meta">{{ event.store_name || '活动门店' }}｜{{ timeText(event.start_time) }}</text>
			<text class="location">{{ event.location || '现场地址待确认' }}</text>
			<view v-if="participant" class="status success">
				<text>已完成签到</text>
				<text>{{ participant.onsite_no }}</text>
			</view>
			<view v-else class="status">
				<text>{{ registrationText }}</text>
				<text>请确认是本人现场操作</text>
			</view>
			<button class="confirm-btn" :disabled="!!participant || submitting" :class="{ disabled: !!participant || submitting }" @tap="confirmCheckin">
				{{ participant ? '已签到' : '确认签到' }}
			</button>
		</view>
	</view>
</template>

<script>
import { checkinScan, checkinScene } from '../../../api/mpEvent.js'
import { ensureRegisteredSession } from '../../../utils/mpSession.js'

export default {
	data() {
		return {
			scene: '',
			event: {},
			registration: null,
			participant: null,
			submitting: false,
		}
	},
	computed: {
		registrationText() {
			if (!this.registration) return '现场用户可直接签到'
			if (this.registration.registration_status === 'pending_payment') return '报名待支付，暂不能签到'
			if (this.registration.registration_status === 'registered') return '已报名，确认后完成签到'
			return `报名状态：${this.registration.registration_status}`
		},
	},
	onLoad(options) {
		this.scene = decodeURIComponent(options.scene || '')
		if (!this.scene && options.q) {
			this.scene = this.extractScene(decodeURIComponent(options.q))
		}
		if (!this.scene) {
			uni.showToast({ title: '签到码无效', icon: 'none' })
			return
		}
		this.load()
	},
	methods: {
		extractScene(value) {
			const match = String(value || '').match(/[?&]scene=([^&#]+)/)
			return match ? decodeURIComponent(match[1]) : ''
		},
		async load() {
			try {
				const data = await checkinScene(this.scene)
				this.event = data.event || {}
				this.registration = data.registration || null
				this.participant = data.participant || null
				if (this.participant) {
					this.enterLive()
				}
			} catch (error) {
				uni.showToast({ title: error.message || '签到码无效', icon: 'none' })
			}
		},
		enterLive() {
			uni.redirectTo({ url: `/pages/activity/live/index?scene=${encodeURIComponent(this.scene)}` })
		},
		async confirmCheckin() {
			if (this.participant || this.submitting) return
			try {
				const session = await ensureRegisteredSession()
				if (!session) {
					uni.navigateTo({ url: `/pages/register/index?redirect=${encodeURIComponent(`/pages/activity/checkin/index?scene=${this.scene}`)}` })
					return
				}
			} catch (error) {
				uni.showToast({ title: error.message || '微信登录失败', icon: 'none' })
				return
			}
			this.submitting = true
			try {
				const data = await checkinScan(this.scene)
				this.participant = {
					id: data.participant_id,
					onsite_no: data.onsite_no,
					participant_status: data.participant_status,
				}
				uni.showToast({ title: '签到成功', icon: 'success' })
				this.enterLive()
			} catch (error) {
				uni.showToast({ title: error.message || '签到失败', icon: 'none' })
			} finally {
				this.submitting = false
			}
		},
		timeText(value) {
			return value ? `${String(value).slice(5, 10)} ${String(value).slice(11, 16)}` : '时间待定'
		},
	},
}
</script>

<style>
.page {
	min-height: 100vh;
	background: #f7f1ea;
	padding: 40rpx 26rpx;
	box-sizing: border-box;
}
.card {
	border: 1rpx solid #eadcd2;
	border-radius: 24rpx;
	background: #fffaf6;
	padding: 34rpx;
	box-shadow: 0 14rpx 34rpx rgba(101, 62, 48, 0.08);
}
.kicker,
.title,
.meta,
.location,
.status text {
	display: block;
}
.kicker {
	color: #c15b65;
	font-size: 24rpx;
	font-weight: 900;
}
.title {
	margin-top: 18rpx;
	color: #2e2522;
	font-size: 44rpx;
	font-weight: 900;
	line-height: 1.25;
}
.meta,
.location {
	margin-top: 14rpx;
	color: #81746d;
	font-size: 27rpx;
	line-height: 1.5;
}
.status {
	margin-top: 34rpx;
	border-radius: 20rpx;
	background: #fff1df;
	padding: 24rpx;
	color: #7d3439;
	font-size: 28rpx;
	font-weight: 800;
}
.status.success {
	background: #e1f3ea;
	color: #2f7152;
}
.status text + text {
	margin-top: 8rpx;
	font-size: 24rpx;
	opacity: 0.76;
}
.confirm-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 92rpx;
	margin-top: 36rpx;
	border: 0;
	border-radius: 999rpx;
	background: #c15b65;
	color: #fff;
	font-size: 30rpx;
	font-weight: 900;
}
.confirm-btn.disabled {
	background: #d8d0ca;
	color: #8d7f78;
}
button::after {
	border: 0;
}
</style>
