<template>
	<view class="page subscription-page">
		<view class="header">
			<view class="brand"><text class="brand-mark">觅</text><text>觅AI 精准推荐</text></view>
			<text class="title">{{ hasActive ? '我的订阅推荐' : '订阅' }}</text>
			<text class="desc">{{ hasActive ? '已开放的推荐可进入详情，未开放的推荐会按日期陆续解锁。' : '觅AI会综合你的真实资料、择偶要求与画像特征，为你筛选更值得认真了解的人' }}</text>
			<view v-if="!hasActive && !loading" class="status-note">
				<text>{{ isRegistered ? '已注册未订阅 · 可随时开通' : '游客可浏览 · 购买前完成注册' }}</text>
			</view>
		</view>

		<view v-if="loading" class="empty-card">
			<text>正在加载订阅信息...</text>
		</view>

		<view v-else-if="hasActive" class="active-wrap">
			<view class="summary-card">
				<view>
					<text class="summary-title">{{ subscription.plan && subscription.plan.plan_name }}</text>
					<text class="summary-desc">已开放 {{ subscription.used_quota || 0 }}/{{ subscription.total_quota || 0 }} 位</text>
				</view>
				<text class="summary-date">至 {{ dateText(subscription.expired_at) }}</text>
			</view>

			<view v-if="!preferenceHint.completed" class="section-card preference-card active-preference-card">
				<view class="preference-copy">
					<text class="notice-title">先补充择偶要求</text>
					<text class="notice-desc">订阅已经生效。为了避免盲目推荐，请先填写你期待的年龄、地区、学历、婚况等条件，觅AI会据此开始匹配。</text>
					<text class="notice-tip">{{ preferenceHint.message }}</text>
				</view>
				<button class="ghost-btn" @tap="goPreference">{{ preferenceHint.completed ? '去修改' : '去填写' }}</button>
			</view>

			<view class="slot-list">
				<view v-for="slot in slots" :key="slot.id" class="slot-card" :class="slot.status" @tap="openSlot(slot)">
					<template v-if="slot.target">
						<image class="slot-photo" :src="slot.target.avatar_url || '/static/logo.png'" mode="aspectFill" />
						<view class="slot-content">
							<view class="slot-head">
								<text class="slot-name">{{ slot.target.nickname || displayName(slot.target) }}</text>
								<text class="score">{{ slot.match_score || 0 }}%</text>
							</view>
							<text class="slot-id">ID {{ slot.target.display_no }} · {{ ageText(slot.target.age) }} · {{ heightText(slot.target.height_cm) }}</text>
							<text class="slot-meta">{{ slot.target.residence || '常驻地待补充' }} · {{ slot.target.occupation || '职业待补充' }}</text>
							<text class="reason">{{ slot.match_reason || '你们在基础条件和相处期待上有一定匹配度。' }}</text>
							<view class="slot-foot">
								<text>{{ slot.status === 'viewed' ? '已查看手机号' : '已开放' }}</text>
								<text>{{ dateText(slot.unlock_at) }}</text>
							</view>
						</view>
					</template>
					<template v-else>
						<view class="placeholder-photo"><view class="blur-block"></view></view>
						<view class="slot-content">
							<view class="slot-head">
								<text class="slot-name">{{ slotTitle(slot) }}</text>
								<text class="locked-tag">{{ slotStatus(slot) }}</text>
							</view>
							<text class="slot-id">第 {{ slot.recommend_index }} 位推荐</text>
							<text class="slot-meta">{{ slotMeta(slot) }}</text>
							<text class="reason">{{ slotReason(slot) }}</text>
						</view>
					</template>
				</view>
			</view>
		</view>

		<view v-else class="plan-wrap">
			<view class="section-card">
				<text class="notice-title">订阅推荐怎么工作</text>
				<text class="notice-desc">每一次推荐，都会按你当下的资料、择偶要求和匹配画像重新匹配。不强行凑数，优先保证推荐质量。</text>
				<view class="steps">
					<view class="step-item">
						<text class="step-no">1</text>
						<view>
							<text class="step-title">购买订阅</text>
							<text class="step-desc">支付成功后立即开放第 1 位推荐。</text>
						</view>
					</view>
					<view class="step-item">
						<text class="step-no accent">2</text>
						<view>
							<text class="step-title">持续匹配</text>
							<text class="step-desc">后续推荐按周期平均开放，开放当天重新匹配。</text>
						</view>
					</view>
					<view class="step-item">
						<text class="step-no green">3</text>
						<view>
							<text class="step-title">解锁联系方式</text>
							<text class="step-desc">推荐开放后，可直接查看手机号。</text>
						</view>
					</view>
				</view>
			</view>

			<view class="section-card preference-card">
				<view class="preference-copy">
					<text class="notice-title">让推荐更贴近你</text>
					<text class="notice-desc">完善择偶要求后，系统会更清楚你期待遇见什么样的人。</text>
					<text class="notice-tip">{{ preferenceHint.message }}</text>
				</view>
				<button class="ghost-btn" @tap="goPreference">{{ preferenceHint.completed ? '修改择偶要求' : '完善择偶要求' }}</button>
			</view>

			<view class="section-card compact">
				<text class="notice-title">选择订阅套餐</text>
				<text class="notice-desc">订阅有效期内，新的推荐会按节奏陆续开放。</text>
			</view>

			<view v-for="plan in plans" :key="plan.id" class="plan-card" :class="{ selected: selectedPlanId === plan.id }" @tap="selectPlan(plan)">
				<text v-if="plan.pay_period === 'quarter'" class="corner">推荐</text>
				<view class="plan-head">
					<view class="plan-name-box">
						<text class="plan-name">{{ plan.plan_name }}</text>
						<text class="plan-desc">{{ plan.period_days }}天权益</text>
					</view>
					<view class="price-box">
						<text class="price"><text class="currency">¥</text>{{ priceNumber(plan.price) }}</text>
					</view>
				</view>
				<view class="meta-grid">
					<view class="meta-box">
						<text class="meta-label">推荐数量</text>
						<text class="meta-value">{{ plan.total_quota }} 位推荐</text>
					</view>
					<view class="meta-box">
						<text class="meta-label">开放节奏</text>
						<text class="meta-value">{{ rhythmText(plan) }}</text>
					</view>
				</view>
				<view class="benefit-line">
					<text class="benefit-dot"></text>
					<text>{{ plan.benefit_desc || '开放后可直接查看手机号' }}</text>
				</view>
			</view>

			<!-- <view class="fineprint">
				<text>游客也可以浏览本页，点击购买时会先引导完成注册。订阅推荐是 AI 推荐辅助，不承诺一定匹配成功。</text>
			</view> -->

			<view class="purchase-bar">
				<view class="selected-summary">
					<text class="summary-label">当前选择</text>
					<text class="summary-plan">{{ selectedPlanText }}</text>
				</view>
				<button class="purchase-btn" :loading="payingPlanId === selectedPlanId" @tap="buySelected">购买订阅</button>
			</view>
		</view>
	</view>
</template>

<script>
import { createSubscriptionOrder, subscriptionMe, subscriptionPlans } from '../../api/mpSubscription.js'
import { ensureMpSession } from '../../utils/mpSession.js'
import { getPerson } from '../../utils/storage.js'

export default {
	data() {
		return {
			loading: false,
			payingPlanId: 0,
			plans: [],
			subscription: {},
			slots: [],
			preferenceHint: {},
			isRegistered: false,
			hasActive: false,
			selectedPlanId: 0,
		}
	},
	computed: {
		selectedPlan() {
			return this.plans.find((item) => item.id === this.selectedPlanId) || this.plans[0] || null
		},
		selectedPlanText() {
			if (!this.selectedPlan) return '请选择订阅套餐'
			return `${this.selectedPlan.plan_name} · ¥${this.selectedPlan.price}`
		},
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		async load() {
			this.loading = true
			try {
				const session = await ensureMpSession().catch(() => null)
				this.isRegistered = Boolean((session && session.person) || getPerson())
				const [plansRes, meRes] = await Promise.all([subscriptionPlans(), subscriptionMe().catch(() => ({ has_active_subscription: false }))])
				this.plans = plansRes.plans || []
				if (!this.selectedPlanId && this.plans.length) {
					const recommended = this.plans.find((item) => item.pay_period === 'quarter')
					this.selectedPlanId = (recommended || this.plans[0]).id
				}
				this.hasActive = Boolean(meRes.has_active_subscription)
				this.subscription = meRes.subscription || {}
				this.slots = meRes.slots || []
				this.preferenceHint = (this.hasActive ? meRes.preference_hint : plansRes.preference_hint) || plansRes.preference_hint || {}
			} finally {
				this.loading = false
			}
		},
		needRegister() {
			if (this.isRegistered) return false
			uni.navigateTo({ url: `/pages/register/index?redirect=${encodeURIComponent('/pages/subscription/index')}` })
			return true
		},
		selectPlan(plan) {
			this.selectedPlanId = plan.id
		},
		buySelected() {
			if (!this.selectedPlan) {
				uni.showToast({ title: '请选择订阅套餐', icon: 'none' })
				return
			}
			this.buy(this.selectedPlan)
		},
		async buy(plan) {
			if (this.needRegister()) return
			this.payingPlanId = plan.id
			try {
				const result = await createSubscriptionOrder(plan.id)
				if (result.already_active) {
					uni.showToast({ title: '订阅已生效', icon: 'success' })
					await this.load()
					return
				}
				const pay = result.payment || {}
				if (pay.wechat_pay) {
					await new Promise((resolve, reject) => {
						uni.requestPayment({ ...pay.wechat_pay, success: resolve, fail: reject })
					})
				}
				uni.showToast({ title: pay.paid ? '订阅已生效' : '支付已发起', icon: 'success' })
				setTimeout(() => this.load(), 800)
			} catch (error) {
				uni.showToast({ title: error.message || '购买失败', icon: 'none' })
			} finally {
				this.payingPlanId = 0
			}
		},
		openSlot(slot) {
			if (this.needRegister()) return
			if (slot.target && slot.target.display_no) {
				uni.navigateTo({ url: `/pages/plaza/detail/index?display_no=${slot.target.display_no}` })
				return
			}
			uni.showToast({ title: slot.status === 'waiting_candidate' ? '正在为你寻找' : '还未到开放时间', icon: 'none' })
		},
		goPreference() {
			if (this.needRegister()) return
			uni.navigateTo({ url: '/pages/mine/preference' })
		},
		priceNumber(value) {
			const text = String(value || '0')
			return text.endsWith('.00') ? text.slice(0, -3) : text
		},
		rhythmText(plan) {
			if (plan.pay_period === 'month') return '立即开放第1位'
			if (plan.pay_period === 'quarter') return '推荐节奏更稳定'
			if (plan.pay_period === 'year') return '长期认真寻找'
			return '按周期开放'
		},
		dateText(value) {
			if (!value) return '-'
			return String(value).replace('T', ' ').slice(0, 16)
		},
		ageText(value) {
			return value ? `${value}岁` : '年龄待补充'
		},
		heightText(value) {
			return value ? `${value}cm` : '身高待补充'
		},
		displayName(target) {
			return target.gender === '0' ? '先生' : '女士'
		},
		slotTitle(slot) {
			if (!this.preferenceHint.completed && slot.status === 'waiting_candidate') return '待完善择偶要求'
			return slot.status === 'waiting_candidate' ? '持续为你寻找' : '即将开放'
		},
		slotStatus(slot) {
			if (!this.preferenceHint.completed && slot.status === 'waiting_candidate') return '待填写'
			return slot.status === 'waiting_candidate' ? '匹配中' : '未开放'
		},
		slotMeta(slot) {
			if (!this.preferenceHint.completed && slot.status === 'waiting_candidate') return '填写择偶要求后，系统会开始为这个槽位匹配。'
			if (slot.status === 'waiting_candidate') return '优先保证质量，不强行凑数。系统会持续为你寻找。'
			return `预计 ${this.dateText(slot.unlock_at)} 开放`
		},
		slotReason(slot) {
			if (!this.preferenceHint.completed && slot.status === 'waiting_candidate') return slot.last_error || '没有择偶要求时不会盲目推荐。'
			return '推荐会在开放时按你的最新资料和择偶要求重新匹配。'
		},
	},
}
</script>

<style>
.subscription-page {
	min-height: 100vh;
	padding: 28rpx 24rpx 72rpx;
	background: radial-gradient(circle at 92% 0%, rgba(214, 140, 120, 0.18), transparent 24%), #f7f0e7;
	box-sizing: border-box;
	color: #4d362b;
}
.brand,
.title,
.desc,
.status-note,
.summary-title,
.summary-desc,
.summary-date,
.slot-name,
.slot-id,
.slot-meta,
.reason,
.notice-title,
.notice-desc,
.notice-tip,
.step-title,
.step-desc,
.plan-name,
.plan-desc,
.price,
.meta-label,
.meta-value,
.benefit-line,
.summary-label,
.summary-plan,
.fineprint {
	display: block;
}
.header {
	padding: 16rpx 4rpx 24rpx;
}
.brand {
	display: flex;
	align-items: center;
	gap: 12rpx;
	width: fit-content;
	color: #806e63;
	font-size: 24rpx;
	font-weight: 800;
}
.brand-mark {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 48rpx;
	height: 48rpx;
	border-radius: 16rpx;
	background: #c96060;
	color: #fff;
	font-weight: 700;
}
.title {
	margin-top: 22rpx;
	font-family: "Songti SC", serif;
	font-size: 68rpx;
	font-weight: 800;
	line-height: 1.08;
}
.desc {
	max-width: 640rpx;
	margin-top: 10rpx;
	color: #806e63;
	font-size: 28rpx;
	line-height: 1.6;
}
.status-note {
	position: relative;
	width: fit-content;
	margin-top: 18rpx;
	padding: 15rpx 22rpx 15rpx 42rpx;
	border: 1rpx solid #dfcfaa;
	border-radius: 999rpx;
	background: #fff8ea;
	color: #61342e;
	font-size: 24rpx;
	font-weight: 800;
}
.status-note::before {
	content: "";
	position: absolute;
	left: 22rpx;
	top: 50%;
	width: 12rpx;
	height: 12rpx;
	margin-top: -6rpx;
	border-radius: 50%;
	background: #5d9a78;
}
.empty-card,
.summary-card,
.section-card,
.plan-card,
.slot-card {
	background: rgba(255, 252, 246, 0.96);
	border: 1rpx solid rgba(139, 104, 78, 0.13);
	border-radius: 24rpx;
	box-shadow: 0 16rpx 38rpx rgba(88, 60, 42, 0.07);
}
.empty-card {
	padding: 60rpx 24rpx;
	text-align: center;
	color: #8a7a70;
}
.section-card {
	padding: 28rpx;
	margin-bottom: 24rpx;
}
.section-card.compact {
	margin-bottom: 18rpx;
}
.notice-title,
.summary-title,
.plan-name {
	font-size: 34rpx;
	font-weight: 850;
	line-height: 1.35;
}
.notice-desc,
.notice-tip,
.summary-desc,
.summary-date,
.plan-desc,
.slot-meta,
.reason {
	margin-top: 10rpx;
	color: #806e63;
	font-size: 25rpx;
	line-height: 1.58;
}
.steps {
	display: flex;
	flex-direction: column;
	gap: 18rpx;
	margin-top: 24rpx;
}
.step-item {
	display: grid;
	grid-template-columns: 64rpx 1fr;
	gap: 18rpx;
	align-items: start;
	padding: 20rpx;
	border: 1rpx solid #e4d8ca;
	border-radius: 20rpx;
	background: #f3ece2;
}
.step-no {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 64rpx;
	height: 64rpx;
	border-radius: 18rpx;
	background: #67312f;
	color: #fff;
	font-size: 26rpx;
	font-weight: 900;
}
.step-no.accent {
	background: #c96060;
}
.step-no.green {
	background: #5d9a78;
}
.step-title {
	font-size: 28rpx;
	font-weight: 850;
}
.step-desc {
	margin-top: 8rpx;
	color: #806e63;
	font-size: 24rpx;
	line-height: 1.45;
}
.preference-card {
	display: grid;
	grid-template-columns: 1fr auto;
	gap: 20rpx;
	align-items: center;
	border-color: rgba(93, 154, 120, 0.25);
	background: linear-gradient(135deg, rgba(93, 154, 120, 0.07), rgba(255, 252, 246, 0.98));
}
.preference-copy {
	min-width: 0;
}
.ghost-btn {
	width: auto;
	height: 72rpx;
	margin: 0;
	padding: 0 24rpx;
	border: 1rpx solid rgba(93, 154, 120, 0.35);
	border-radius: 999rpx;
	background: #fffdf8;
	color: #5d9a78;
	font-size: 24rpx;
	font-weight: 850;
	white-space: nowrap;
}
.plan-card {
	position: relative;
	padding: 28rpx;
	margin-bottom: 22rpx;
	transition: transform 0.15s ease;
}
.plan-card.selected {
	border-color: rgba(201, 96, 96, 0.58);
	background: linear-gradient(135deg, rgba(248, 226, 220, 0.72), rgba(255, 252, 246, 0.98));
}
.corner {
	position: absolute;
	right: 24rpx;
	top: 24rpx;
	padding: 7rpx 17rpx;
	border: 1rpx solid #dfcfaa;
	border-radius: 999rpx;
	background: #fff7e4;
	color: #61342e;
	font-size: 22rpx;
	font-weight: 900;
}
.plan-head {
	display: flex;
	justify-content: space-between;
	gap: 20rpx;
	padding-right: 96rpx;
}
.plan-name-box {
	min-width: 0;
}
.price-box {
	flex: none;
	text-align: right;
}
.price {
	color: #61342e;
	font-family: "Songti SC", serif;
	font-size: 56rpx;
	font-weight: 900;
	line-height: 1;
}
.currency {
	font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
	font-size: 26rpx;
	vertical-align: 18rpx;
}
.meta-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16rpx;
	margin-top: 24rpx;
}
.meta-box {
	min-height: 98rpx;
	padding: 16rpx 18rpx;
	border: 1rpx solid #e4d8ca;
	border-radius: 20rpx;
	background: #f3ece2;
	box-sizing: border-box;
}
.meta-label {
	margin-bottom: 8rpx;
	color: #806e63;
	font-size: 22rpx;
	font-weight: 750;
}
.meta-value {
	font-size: 26rpx;
	font-weight: 850;
	line-height: 1.28;
}
.benefit-line {
	position: relative;
	margin-top: 20rpx;
	padding-left: 22rpx;
	color: #806e63;
	font-size: 24rpx;
	line-height: 1.45;
}
.benefit-dot {
	position: absolute;
	left: 0;
	top: 13rpx;
	width: 12rpx;
	height: 12rpx;
	border-radius: 50%;
	background: #5d9a78;
}
.fineprint {
	margin: 24rpx 0 16rpx;
	padding: 22rpx;
	border: 1rpx dashed rgba(201, 96, 96, 0.32);
	border-radius: 22rpx;
	background: rgba(248, 226, 220, 0.42);
	color: #806e63;
	font-size: 24rpx;
	line-height: 1.58;
}
.purchase-bar {
	display: grid;
	grid-template-columns: 1fr auto;
	gap: 18rpx;
	align-items: center;
	margin: 14rpx 0 0;
	padding: 20rpx 22rpx;
	border: 1rpx solid rgba(201, 96, 96, 0.24);
	border-radius: 28rpx;
	background: rgba(255, 252, 246, 0.94);
	box-shadow: 0 16rpx 38rpx rgba(88, 60, 42, 0.07);
}
.summary-label {
	color: #806e63;
	font-size: 22rpx;
	font-weight: 750;
}
.summary-plan {
	margin-top: 5rpx;
	font-size: 28rpx;
	font-weight: 850;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.purchase-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: auto;
	height: 88rpx;
	line-height: 88rpx;
	margin: 0;
	padding: 0 34rpx;
	border-radius: 999rpx;
	background: #c96060;
	color: #fff;
	font-size: 28rpx;
	font-weight: 900;
	box-shadow: 0 14rpx 28rpx rgba(201, 96, 96, 0.22);
	white-space: nowrap;
}
.summary-card {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 28rpx;
	margin-bottom: 24rpx;
}
.slot-list {
	display: flex;
	flex-direction: column;
	gap: 22rpx;
}
.slot-card {
	display: flex;
	gap: 22rpx;
	padding: 18rpx;
	overflow: hidden;
}
.slot-photo,
.placeholder-photo {
	width: 210rpx;
	height: 260rpx;
	border-radius: 20rpx;
	flex: none;
	overflow: hidden;
	background: #d9cfc2;
}
.blur-block {
	width: 100%;
	height: 100%;
	background: linear-gradient(135deg, #b9a493, #8fa17f 55%, #d4c7b8);
	filter: blur(10rpx);
	transform: scale(1.08);
}
.slot-content {
	flex: 1;
	min-width: 0;
	padding: 4rpx 0;
}
.slot-head,
.slot-foot {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16rpx;
}
.slot-name {
	font-size: 31rpx;
	font-weight: 850;
}
.score,
.locked-tag {
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	background: #c96060;
	color: #fff;
	font-size: 23rpx;
	font-weight: 800;
}
.locked-tag {
	background: #9cab88;
}
.slot-id {
	margin-top: 10rpx;
	color: #9b6a57;
	font-size: 23rpx;
}
.slot-foot {
	margin-top: 14rpx;
	color: #9cab88;
	font-size: 23rpx;
	font-weight: 800;
}
</style>
