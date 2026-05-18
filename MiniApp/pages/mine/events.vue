<template>
	<view class="page events-page">
		<view class="header-card">
			<text class="title">我的活动</text>
			<text class="desc">报名、支付和签到状态都在这里。</text>
		</view>

		<view v-if="loading && !items.length" class="empty-state"><text class="empty-title">正在加载...</text></view>
		<view v-else-if="!items.length" class="empty-state">
			<text class="empty-title">还没有活动报名</text>
			<text class="empty-desc">线下活动会让相识更具体，也更容易判断合不合适。</text>
			<button class="reset-btn" @tap="goActivity">看看近期活动</button>
		</view>

		<view v-else>
			<view v-for="item in items" :key="item.registration.id" class="event-card" @tap="goDetail(item.event.id)">
				<image v-if="item.event.cover_url" class="cover" :src="coverThumb(item.event.cover_url)" mode="aspectFill" />
				<view v-else class="cover empty"></view>
				<view class="body">
					<view class="top"><text class="event-title">{{ item.event.title }}</text><text class="status">{{ statusLabel(item.registration.registration_status) }}</text></view>
					<text class="meta">{{ timeText(item.event.start_time) }}</text>
					<text class="meta">{{ item.event.location || item.event.store_name || '地点待公布' }}</text>
					<button v-if="item.registration.registration_status === 'pending_payment'" class="pay-btn" :loading="payingId === item.registration.id" @tap.stop="continuePay(item)">继续支付</button>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { continueEventPay } from '../../api/mpEvent.js'
import { mineEvents } from '../../api/mpProfile.js'
import { ensureRegisteredSession } from '../../utils/mpSession.js'
import { ossImage } from '../../utils/ossImage.js'

export default {
	data() {
		return { items: [], pageNo: 1, pageSize: 20, hasNext: false, loading: false, payingId: null }
	},
	onShow() { this.reload() },
	onPullDownRefresh() { this.reload().finally(() => uni.stopPullDownRefresh()) },
	onReachBottom() { if (this.hasNext && !this.loading) this.load(false) },
	methods: {
		coverThumb(url) { return ossImage(url, { width: 240, height: 180 }) },
		async reload() { this.pageNo = 1; this.items = []; await this.load(true) },
		async load(reset) {
			this.loading = true
			try {
				await ensureRegisteredSession()
				const data = await mineEvents({ page_no: this.pageNo, page_size: this.pageSize })
				const list = data.items || []
				this.items = reset ? list : this.items.concat(list)
				this.hasNext = !!data.has_next
				if (this.hasNext) this.pageNo += 1
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		statusLabel(status) {
			return ({ pending_payment: '待支付', registered: '已报名', checked_in: '已签到', timeout: '已超时', cancelled: '已取消' }[status]) || status || '未知'
		},
		timeText(value) {
			if (!value) return '时间待公布'
			return String(value).replace('T', ' ').slice(0, 16)
		},
		goDetail(id) {
			uni.navigateTo({ url: `/pages/activity/detail/index?id=${id}` })
		},
		goActivity() {
			uni.switchTab({ url: '/pages/activity/index' })
		},
		async continuePay(item) {
			this.payingId = item.registration.id
			try {
				const result = await continueEventPay(item.registration.id)
				if (result.payment && result.payment.paid) {
					uni.showToast({ title: '支付已确认', icon: 'success' })
					this.reload()
				} else if (result.payment) {
					await this.requestPayment(result.payment.wechat_pay || result.payment.pay_payload)
					this.reload()
				} else {
					uni.showToast({ title: '报名已更新', icon: 'success' })
					this.reload()
				}
			} catch (error) {
				uni.showToast({ title: error.message || '支付失败', icon: 'none' })
			} finally {
				this.payingId = null
			}
		},
		requestPayment(payload) {
			return new Promise((resolve) => {
				let source = payload
				if (typeof source === 'string') {
					try {
						source = JSON.parse(source)
					} catch (error) {
						source = null
					}
				}
				if (!source || typeof source !== 'object') {
					uni.showToast({ title: '订单已创建，请稍后继续支付', icon: 'none' })
					resolve(false)
					return
				}
				const rawPayData = source.pay_info || source.payData || source.wechat_pay || source
				const payData = {
					timeStamp: rawPayData.timeStamp || rawPayData.time_stamp,
					nonceStr: rawPayData.nonceStr || rawPayData.nonce_str,
					package: rawPayData.package || rawPayData.package_info,
					signType: rawPayData.signType || rawPayData.sign_type,
					paySign: rawPayData.paySign || rawPayData.pay_sign,
				}
				if (!payData.timeStamp || !payData.nonceStr || !payData.package || !payData.signType || !payData.paySign) {
					uni.showToast({ title: '订单已创建，请稍后继续支付', icon: 'none' })
					resolve(false)
					return
				}
				uni.requestPayment({
					...payData,
					success: () => {
						uni.showToast({ title: '支付完成', icon: 'success' })
						resolve(true)
					},
					fail: () => {
						uni.showToast({ title: '支付未完成', icon: 'none' })
						resolve(false)
					},
				})
			})
		},
	},
}
</script>

<style>
.events-page { min-height: 100vh; background: #f7f4ef; padding: 24rpx; box-sizing: border-box; }
.header-card, .event-card, .empty-state { background: #fffaf3; border-radius: 28rpx; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); padding: 26rpx; margin-bottom: 18rpx; }
.title, .desc, .empty-title, .empty-desc, .meta { display: block; }
.title { color: #3f2d28; font-size: 38rpx; font-weight: 900; }
.desc, .empty-desc, .meta { color: #8d7f78; font-size: 25rpx; line-height: 1.6; margin-top: 8rpx; }
.event-card { display: flex; gap: 20rpx; }
.cover { width: 170rpx; height: 140rpx; border-radius: 22rpx; background: #eadbd0; flex-shrink: 0; }
.cover.empty { background: linear-gradient(135deg, #eadbd0, #f5e7d4); }
.body { flex: 1; min-width: 0; }
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12rpx; }
.event-title { color: #4b342d; font-size: 30rpx; font-weight: 900; line-height: 1.35; flex: 1; }
.status { border-radius: 999rpx; background: #eef5ec; color: #4e865e; font-size: 21rpx; font-weight: 800; padding: 6rpx 12rpx; white-space: nowrap; }
.pay-btn { width: 160rpx; height: 60rpx; line-height: 60rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 24rpx; margin: 14rpx 0 0; }
.empty-title { color: #4b342d; font-size: 34rpx; font-weight: 900; }
.reset-btn { margin-top: 24rpx; height: 76rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 28rpx; }
</style>
