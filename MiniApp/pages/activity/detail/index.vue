<template>
	<view class="page">
		<view class="hero" :class="{ 'hero-empty': !event.cover_url }">
			<image v-if="event.cover_url" class="hero-img" :src="event.cover_url" mode="aspectFill" />
			<view class="hero-mask"></view>
			<view class="hero-content">
				<view class="hero-tags">
					<text class="hero-tag">{{ typeLabel(event.event_type) }}</text>
					<text class="hero-tag primary">{{ eventStatusText }}</text>
				</view>
				<text class="hero-title">{{ event.title || '活动详情' }}</text>
				<text v-if="event.subtitle" class="hero-subtitle">{{ event.subtitle }}</text>
			</view>
		</view>

		<view class="body">
			<view class="intro-card">
				<view class="brand-row">
					<view class="brand">
						<text class="brand-mark">觅</text>
						<text>觅AI 活动详情</text>
					</view>
					<text class="brand-meta">{{ event.store_name || '精选活动' }}</text>
				</view>
				<text class="intro-title">把心动，带到真实见面里</text>
				<text class="intro-desc">精选线下活动、主题沙龙与相亲局，报名后现场签到参与互动。</text>
			</view>

			<view class="section">
				<view class="section-head">
					<text class="section-title">核心信息</text>
				</view>
				<view class="info-grid">
					<view class="info-cell">
						<text class="info-label">时 活动时间</text>
						<text class="info-value">{{ fullTimeText }}</text>
					</view>
					<view class="info-cell">
						<text class="info-label">地 活动地点</text>
						<text class="info-value">{{ locationText }}</text>
					</view>
					<view class="info-cell">
						<text class="info-label">费 报名费用</text>
						<text class="info-value accent">{{ feeLabel(event) }}</text>
					</view>
					<view class="info-cell">
						<text class="info-label">额 剩余名额</text>
						<text class="info-value">男 {{ remainingText(event.male_remaining) }} / 女 {{ remainingText(event.female_remaining) }}</text>
					</view>
					<view class="info-cell">
						<text class="info-label">止 报名截止</text>
						<text class="info-value">{{ deadlineText }}</text>
					</view>
					<view class="info-cell">
						<text class="info-label">签 报名要求</text>
						<text class="info-value">{{ requireText }}</text>
					</view>
				</view>
			</view>
			<view class="section share-card">
				<view>
					<text class="section-title">分享给同样认真生活的朋友</text>
					<text class="share-desc">分享活动只展示公开活动介绍，不展示个人报名信息。</text>
				</view>
				<button class="share-btn" open-type="share">分享活动</button>
			</view>
			<view class="section quota-card">
				<view class="count-row">
					<view>
						<text class="count-num">{{ totalRegistered }}</text>
						<text class="count-label"> 人已报名</text>
					</view>
					<text class="status-pill" :class="eventStatusClass">{{ eventStatusText }}</text>
				</view>
				<view class="quota-lines">
					<view class="quota-line">
						<text>男生</text>
						<view class="bar"><view class="bar-inner" :style="{ width: maleProgress }"></view></view>
						<text class="quota-num">{{ maleRegistered }}/{{ maleQuota }}</text>
					</view>
					<view class="quota-line">
						<text>女生</text>
						<view class="bar"><view class="bar-inner" :style="{ width: femaleProgress }"></view></view>
						<text class="quota-num">{{ femaleRegistered }}/{{ femaleQuota }}</text>
					</view>
				</view>
			</view>

			<view v-if="myRegistration" class="section registration-card">
				<view class="section-head">
					<text class="section-title">我的报名</text>
					<text class="status-pill success">{{ registrationLabel(myRegistration.registration_status) }}</text>
				</view>
				<view class="ticket">
					<view class="ticket-main">
						<text class="ticket-title">{{ registrationTitle }}</text>
						<text v-if="myRegistration.registration_no" class="ticket-desc">报名编号：{{ myRegistration.registration_no }}</text>
						<text v-if="myRegistration.payment_expire_at" class="ticket-desc">支付截止：{{ myRegistration.payment_expire_at }}</text>
					</view>
					<button class="small-btn" @tap="checkin">现场签到</button>
				</view>
			</view>
			<view class="section">
				<view class="section-head">
					<text class="section-title">{{ contentTitle }}</text>
				</view>
				<view class="rich-content">
					<rich-text v-if="displayNodes" :nodes="displayNodes" />
					<text v-else class="empty-detail">暂无活动详情</text>
				</view>
			</view>
		</view>

		<view class="bottom-bar">
			<button class="bottom-btn primary" :class="{ disabled: actionDisabled }" :disabled="actionDisabled" @tap="registerOrPay">{{ actionText }}</button>
		</view>
	</view>
</template>

<script>
import { checkinEvent, continueEventPay, eventDetail, myEventRegistration, registerEvent } from '../../../api/mpEvent.js'
import { getToken } from '../../../utils/storage.js'
import { ensureMpSession, ensureRegisteredSession } from '../../../utils/mpSession.js'

export default {
	name: 'ActivityDetail',
	data() {
		return {
			id: '',
			event: {
				title: '',
				subtitle: '',
				event_type: '',
				cover_url: '',
				location: '',
				store_name: '',
				start_time: '',
				end_time: '',
				register_deadline: '',
				detail_html: '',
				effect_html: '',
				display_html: '',
				event_status: '',
				male_fee: 0,
				female_fee: 0,
				male_quota: 0,
				female_quota: 0,
				male_remaining: 0,
				female_remaining: 0,
				require_realname: true,
				min_age: null,
				max_age: null,
			},
			myRegistration: null,
			submitting: false,
		}
	},
	computed: {
		fullTimeText() {
			const start = this.formatDateTime(this.event.start_time)
			const end = this.event.end_time ? String(this.event.end_time).slice(11, 16) : ''
			if (!start) return '时间待定'
			return end ? `${start}-${end}` : start
		},
		deadlineText() {
			return this.formatDateTime(this.event.register_deadline) || '待公布'
		},
		locationText() {
			return this.event.location || this.event.store_name || '地点待公布'
		},
		ageText() {
			if (this.event.min_age && this.event.max_age) return `${this.event.min_age}-${this.event.max_age}岁`
			if (this.event.min_age) return `${this.event.min_age}岁以上`
			if (this.event.max_age) return `${this.event.max_age}岁以下`
			return '年龄不限'
		},
		requireText() {
			const realname = this.event.require_realname ? '需实名资料' : '不强制实名'
			return `${realname} · ${this.ageText}`
		},
		maleQuota() {
			return Number(this.event.male_quota || 0)
		},
		femaleQuota() {
			return Number(this.event.female_quota || 0)
		},
		maleRemaining() {
			return Math.max(Number(this.event.male_remaining || 0), 0)
		},
		femaleRemaining() {
			return Math.max(Number(this.event.female_remaining || 0), 0)
		},
		maleRegistered() {
			return Math.max(this.maleQuota - this.maleRemaining, 0)
		},
		femaleRegistered() {
			return Math.max(this.femaleQuota - this.femaleRemaining, 0)
		},
		totalRegistered() {
			return this.maleRegistered + this.femaleRegistered
		},
		maleProgress() {
			return this.percentText(this.maleRegistered, this.maleQuota)
		},
		femaleProgress() {
			return this.percentText(this.femaleRegistered, this.femaleQuota)
		},
		isFull() {
			return this.maleRemaining + this.femaleRemaining <= 0 && this.maleQuota + this.femaleQuota > 0
		},
		isDeadlinePassed() {
			const deadline = this.parseTime(this.event.register_deadline)
			return deadline ? deadline <= Date.now() : false
		},
		eventStatusText() {
			if (this.event.event_status === 'finished') return '已结束'
			if (this.isFull) return '名额已满'
			if (this.isDeadlinePassed) return '报名截止'
			return '可报名'
		},
		eventStatusClass() {
			if (this.event.event_status === 'finished') return 'muted'
			if (this.isFull || this.isDeadlinePassed) return 'warn'
			return 'success'
		},
		actionText() {
			if (this.event.event_status === 'finished') return '已结束'
			if (!this.myRegistration) {
				if (this.isFull) return '名额已满'
				if (this.isDeadlinePassed) return '报名截止'
				return '立即报名'
			}
			if (this.myRegistration.registration_status === 'pending_payment') return '继续支付'
			if (this.myRegistration.registration_status === 'checked_in') return '已签到'
			if (this.myRegistration.registration_status === 'registered') return '已报名'
			if (this.myRegistration.registration_status === 'timeout') return '重新支付'
			return '立即报名'
		},
		actionDisabled() {
			const status = this.myRegistration ? this.myRegistration.registration_status : ''
			if (status === 'registered' || status === 'checked_in') return true
			if (status === 'pending_payment' || status === 'timeout') return false
			return this.event.event_status === 'finished' || this.isFull || this.isDeadlinePassed
		},
		registrationTitle() {
			if (!this.myRegistration) return ''
			const status = this.myRegistration.registration_status
			if (status === 'pending_payment') return '报名待支付'
			if (status === 'checked_in') return '已完成现场签到'
			if (status === 'registered') return '报名成功'
			if (status === 'timeout') return '支付已超时'
			return this.registrationLabel(status)
		},
		contentTitle() {
			return this.event.event_status === 'finished' ? '活动效果' : '活动详情'
		},
		displayNodes() {
			return this.event.display_html || (this.event.event_status === 'finished' ? this.event.effect_html : this.event.detail_html) || ''
		},
	},
	onLoad(options) {
		this.id = options.id
	},
	onShow() {
		this.fetchDetail()
	},
	onPullDownRefresh() {
		this.fetchDetail().finally(() => {
			uni.stopPullDownRefresh()
		})
	},
	onShareAppMessage() {
		return {
			title: this.event.title || '觅AI 活动详情',
			path: `/pages/activity/detail/index?id=${this.id}`,
			imageUrl: this.event.cover_url || undefined,
		}
	},
	methods: {
		async fetchDetail() {
			try {
				this.event = await eventDetail(this.id)
				await ensureMpSession().catch(() => null)
				if (getToken()) {
					try {
						this.myRegistration = await myEventRegistration(this.id)
					} catch (error) {
						this.myRegistration = null
					}
				}
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			}
		},
		async ensureRegistered() {
			try {
				const session = await ensureRegisteredSession()
				if (session) return true
			} catch (error) {
				uni.showToast({ title: error.message || '微信登录失败', icon: 'none' })
				return false
			}
			uni.navigateTo({ url: `/pages/register/index?redirect=${encodeURIComponent(`/pages/activity/detail/index?id=${this.id}`)}` })
			return false
		},
		async registerOrPay() {
			if (this.submitting || this.actionDisabled) return
			if (!(await this.ensureRegistered())) return
			const registrationStatus = this.myRegistration ? this.myRegistration.registration_status : ''
			if (registrationStatus === 'registered' || registrationStatus === 'checked_in') return
			this.submitting = true
			try {
				const result = registrationStatus === 'pending_payment'
					? await continueEventPay(this.myRegistration.id)
					: await registerEvent(this.id, { payload: { scene: 'activity_detail' } })
				this.myRegistration = result.registration || this.myRegistration
				if (result.payment && result.payment.paid) {
					uni.showToast({ title: '支付已确认', icon: 'success' })
				} else if (result.payment) {
					await this.requestPayment(result.payment.wechat_pay || result.payment.pay_payload)
				} else {
					uni.showToast({ title: '报名成功', icon: 'success' })
				}
				await this.fetchDetail()
			} catch (error) {
				uni.showToast({ title: error.message || '报名失败', icon: 'none' })
			} finally {
				this.submitting = false
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
		async checkin() {
			if (!(await this.ensureRegistered())) return
			try {
				await checkinEvent(this.id, { registration_id: this.myRegistration ? this.myRegistration.id : undefined, payload: { scene: 'activity_detail' } })
				uni.showToast({ title: '签到成功', icon: 'success' })
				await this.fetchDetail()
			} catch (error) {
				uni.showToast({ title: error.message || '签到失败', icon: 'none' })
			}
		},
		typeLabel(value) {
			return { matchmaking: '相亲会', salon: '主题沙龙', outdoor: '户外活动', festival: '节日活动' }[value] || value || '活动'
		},
		feeLabel(item) {
			const male = Number(item.male_fee || 0)
			const female = Number(item.female_fee || 0)
			if (!male && !female) return '免费参加'
			if (male === female) return `报名费用 ¥${male.toFixed(0)}`
			return `男 ¥${male.toFixed(0)} / 女 ¥${female.toFixed(0)}`
		},
		registrationLabel(value) {
			return { pending_payment: '待支付', registered: '已报名', checked_in: '已签到', timeout: '已超时', cancelled: '已取消' }[value] || value
		},
		remainingText(value) {
			const num = Number(value)
			return Number.isFinite(num) ? String(Math.max(num, 0)) : '-'
		},
		parseTime(value) {
			if (!value) return null
			const time = new Date(String(value).replace(/-/g, '/')).getTime()
			return Number.isNaN(time) ? null : time
		},
		formatDateTime(value) {
			const text = value ? String(value) : ''
			if (!text) return ''
			const monthDay = text.slice(5, 10).replace('-', '月') + '日'
			const hm = text.slice(11, 16)
			return hm ? `${monthDay} ${hm}` : monthDay
		},
		percentText(used, total) {
			if (!total) return '0%'
			const percent = Math.min(Math.max((used / total) * 100, 0), 100)
			return `${percent.toFixed(0)}%`
		},
	},
}
</script>

<style>
.page {
	min-height: 100vh;
	background: #f7f1ea;
	padding-bottom: 230rpx;
	box-sizing: border-box;
}
.hero {
	position: relative;
	height: 470rpx;
	overflow: hidden;
	background: linear-gradient(135deg, #7a3438 0%, #c76366 48%, #d5a94e 100%);
}
.hero-empty::before {
	content: "";
	position: absolute;
	top: 0;
	right: 0;
	bottom: 0;
	left: 0;
	background:
		radial-gradient(circle at 18% 20%, rgba(255, 238, 211, 0.4), transparent 34%),
		radial-gradient(circle at 82% 18%, rgba(255, 255, 255, 0.24), transparent 28%),
		linear-gradient(135deg, #7a3438 0%, #c76366 52%, #d5a94e 100%);
}
.hero-img,
.hero-mask,
.hero-content {
	position: absolute;
	left: 0;
	right: 0;
}
.hero-img {
	top: 0;
	width: 100%;
	height: 100%;
}
.hero-mask {
	top: 0;
	bottom: 0;
	background: linear-gradient(180deg, rgba(34, 21, 18, 0.08) 0%, rgba(34, 21, 18, 0.76) 100%);
}
.hero-content {
	bottom: 0;
	padding: 0 34rpx 42rpx;
	box-sizing: border-box;
}
.hero-tags,
.brand-row,
.brand,
.section-head,
.count-row,
.quota-line,
.ticket,
.share-card,
.checkin-card,
.bottom-bar {
	display: flex;
	align-items: center;
}
.hero-tags {
	gap: 12rpx;
	margin-bottom: 18rpx;
}
.hero-tag,
.status-pill,
.rule-tag {
	border-radius: 999rpx;
	font-size: 23rpx;
	font-weight: 800;
}
.hero-tag {
	color: #fff8ee;
	background: rgba(255, 255, 255, 0.2);
	padding: 8rpx 18rpx;
}
.hero-tag.primary {
	color: #7c3438;
	background: #fff1df;
}
.hero-title,
.hero-subtitle,
.intro-title,
.intro-desc,
.section-title,
.info-label,
.info-value,
.count-num,
.count-label,
.notice-title,
.notice-desc,
.ticket-title,
.ticket-desc,
.share-desc,
.rule-desc,
.empty-detail {
	display: block;
}
.hero-title {
	color: #fffaf4;
	font-size: 50rpx;
	font-weight: 900;
	line-height: 1.16;
	text-shadow: 0 4rpx 18rpx rgba(34, 21, 18, 0.2);
}
.hero-subtitle {
	margin-top: 14rpx;
	color: rgba(255, 250, 244, 0.88);
	font-size: 28rpx;
	line-height: 1.5;
}
.body {
	position: relative;
	margin-top: -26rpx;
	padding: 0 24rpx 28rpx;
	box-sizing: border-box;
}
.intro-card,
.section {
	border: 1rpx solid #eadcd2;
	border-radius: 20rpx;
	background: #fffaf6;
	box-shadow: 0 14rpx 34rpx rgba(101, 62, 48, 0.08);
}
.intro-card {
	padding: 24rpx;
}
.brand-row,
.section-head,
.count-row,
.ticket,
.share-card,
.checkin-card {
	justify-content: space-between;
	gap: 18rpx;
}
.brand {
	gap: 10rpx;
	color: #7d3439;
	font-size: 24rpx;
	font-weight: 800;
}
.brand-mark {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 38rpx;
	height: 38rpx;
	border-radius: 12rpx;
	color: #fff;
	background: #be5a62;
	font-weight: 900;
}
.brand-meta {
	color: #8f8178;
	font-size: 23rpx;
}
.intro-title {
	margin-top: 20rpx;
	color: #2e2522;
	font-size: 36rpx;
	font-weight: 900;
	line-height: 1.32;
}
.intro-desc,
.share-desc,
.rule-desc,
.notice-desc,
.ticket-desc {
	color: #81746d;
	font-size: 25rpx;
	line-height: 1.55;
}
.intro-desc {
	margin-top: 8rpx;
}
.section {
	margin-top: 22rpx;
	padding: 24rpx;
}
.section-title {
	color: #2e2522;
	font-size: 31rpx;
	font-weight: 900;
	line-height: 1.35;
}
.info-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 18rpx;
}
.info-cell {
	min-height: 132rpx;
	border: 1rpx solid #efe4db;
	border-radius: 18rpx;
	background: #fff;
	padding: 18rpx;
	box-sizing: border-box;
}
.info-label {
	color: #92827a;
	font-size: 22rpx;
	font-weight: 800;
}
.info-value {
	margin-top: 10rpx;
	color: #332925;
	font-size: 27rpx;
	font-weight: 800;
	line-height: 1.42;
	word-break: break-all;
}
.info-value.accent {
	color: #c15b65;
}
.quota-card {
	background: #fff8f3;
}
.count-num {
	display: inline;
	color: #7d3439;
	font-size: 48rpx;
	font-weight: 900;
}
.count-label {
	display: inline;
	color: #7a6d66;
	font-size: 25rpx;
	font-weight: 750;
}
.status-pill {
	color: #7d3439;
	background: #f4dedb;
	padding: 8rpx 18rpx;
}
.status-pill.success {
	color: #2f7152;
	background: #e1f3ea;
}
.status-pill.warn {
	color: #98631a;
	background: #fff1d6;
}
.status-pill.muted {
	color: #8d7f78;
	background: #eee7e1;
}
.quota-lines {
	margin-top: 20rpx;
}
.quota-line {
	gap: 16rpx;
	min-height: 54rpx;
	color: #75675f;
	font-size: 24rpx;
	font-weight: 800;
}
.quota-line text:first-child {
	width: 70rpx;
}
.bar {
	flex: 1;
	height: 14rpx;
	overflow: hidden;
	border-radius: 999rpx;
	background: #eadfd6;
}
.bar-inner {
	height: 100%;
	border-radius: 999rpx;
	background: linear-gradient(90deg, #c15b65, #d7a84f);
}
.quota-num {
	width: 88rpx;
	text-align: right;
	color: #332925;
}
.notice {
	margin-top: 18rpx;
	border: 1rpx solid #ecd9b4;
	border-radius: 18rpx;
	background: #fff4db;
	padding: 18rpx;
}
.notice-title {
	color: #7d3439;
	font-size: 26rpx;
	font-weight: 900;
}
.notice-desc {
	margin-top: 6rpx;
}
.registration-card {
	border-color: #cde8da;
	background: #f7fffa;
}
.ticket {
	margin-top: 18rpx;
	border: 1rpx dashed #9bd1b7;
	border-radius: 18rpx;
	background: #fff;
	padding: 18rpx;
}
.ticket-main {
	flex: 1;
	min-width: 0;
}
.ticket-title {
	color: #263d32;
	font-size: 29rpx;
	font-weight: 900;
}
.ticket-desc {
	margin-top: 6rpx;
}
.small-btn,
.share-btn,
.bottom-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	border: 0;
	border-radius: 999rpx;
	font-weight: 900;
	line-height: 1;
}
.small-btn {
	flex: 0 0 auto;
	height: 66rpx;
	padding: 0 22rpx;
	color: #5b4d47;
	background: #f4eee8;
	font-size: 24rpx;
}
.small-btn.primary {
	color: #fff;
	background: #c15b65;
}
.share-card,
.checkin-card {
	align-items: flex-start;
}
.share-card > view,
.checkin-card > view {
	flex: 1;
	min-width: 0;
}
.share-desc {
	margin-top: 8rpx;
}
.share-btn {
	flex: 0 0 auto;
	height: 72rpx;
	padding: 0 26rpx;
	color: #fff;
	background: #7d3439;
	font-size: 25rpx;
}
.rich-content {
	margin-top: 18rpx;
	color: #4a3d37;
	font-size: 28rpx;
	line-height: 1.75;
}
.empty-detail {
	color: #8d7f78;
	font-size: 25rpx;
}
.rules {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 18rpx;
}
.rule-tag {
	border: 1rpx solid #eadfd6;
	color: #75675f;
	background: #fff;
	padding: 10rpx 18rpx;
}
.rule-tag.strong {
	border-color: #e6c3be;
	color: #7d3439;
	background: #f6e4e2;
}
.rule-desc {
	margin-top: 18rpx;
}
.bottom-bar {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	z-index: 20;
	gap: 16rpx;
	border-top: 1rpx solid #eadfd6;
	background: rgba(255, 250, 246, 0.96);
	box-shadow: 0 -16rpx 34rpx rgba(82, 54, 45, 0.1);
	padding: 20rpx 24rpx calc(28rpx + env(safe-area-inset-bottom));
	box-sizing: border-box;
}
.bottom-btn {
	height: 88rpx;
	margin: 0;
	font-size: 29rpx;
}
.bottom-btn.primary {
	flex: 1;
	color: #fff;
	background: #c15b65;
	box-shadow: 0 12rpx 24rpx rgba(193, 91, 101, 0.22);
}
.bottom-btn.disabled {
	color: #9a8d86;
	background: #eee7e1;
	box-shadow: none;
}
button::after {
	border: 0;
}
</style>
