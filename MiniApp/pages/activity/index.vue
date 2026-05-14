<template>
	<view class="page">
		<view class="header">
			<view class="brand-row">
				<view class="brand">
					<text class="brand-mark">觅</text>
					<text>本地优质相识活动</text>
				</view>
				<text class="city">本地</text>
			</view>
			<text class="title">近期活动</text>
			<text class="desc">发现适合你的线下相识机会</text>
		</view>

		<scroll-view class="filters" scroll-x :show-scrollbar="false">
			<view class="filter-row">
				<view
					v-for="item in filters"
					:key="item.value"
					class="chip"
					:class="{ active: activeFilter === item.value }"
					@tap="activeFilter = item.value"
				>
					{{ item.label }}
				</view>
			</view>
		</scroll-view>

		<view class="state-panel">
			<text class="state-title">{{ stateTitle }}</text>
			<text class="state-desc">{{ stateDesc }}</text>
		</view>

		<view v-if="loading" class="empty-state">
			<text class="empty-title">活动加载中...</text>
			<text class="empty-desc">正在同步最新发布的活动</text>
		</view>

		<view v-else-if="!filteredEvents.length" class="empty-state">
			<text class="empty-title">暂无匹配活动</text>
			<text class="empty-desc">当前筛选条件下还没有可展示的活动</text>
			<button v-if="activeFilter !== 'all'" class="reset-btn" @tap="activeFilter = 'all'">查看全部活动</button>
		</view>

		<view v-else class="list">
			<view v-for="(item, index) in filteredEvents" :key="item.id" class="event-card" @tap="goDetail(item.id)">
				<view class="cover-wrap">
					<image v-if="item.cover_url" class="cover-img" :src="item.cover_url" mode="aspectFill" />
					<view v-else class="cover-empty" :class="coverClass(item, index)"></view>
					<view class="cover-shade"></view>
					<text class="cover-label">{{ coverLabel(item) }}</text>
				</view>

				<view class="card-body">
					<view class="topline">
						<text class="event-title">{{ item.title }}</text>
						<text class="tag">{{ typeLabel(item.event_type) }}</text>
					</view>

					<view class="meta">
						<view class="meta-row">
							<text class="ico">时</text>
							<text class="meta-text">{{ eventTimeText(item) }}</text>
						</view>
						<view class="meta-row">
							<text class="ico">地</text>
							<text class="meta-text">{{ item.location || item.store_name || '待公布' }}</text>
						</view>
						<view class="meta-row">
							<text class="ico">费</text>
							<text class="fee" :class="{ free: isFree(item) }">{{ feeLabel(item) }}</text>
						</view>
					</view>

					<view class="quota">
						<view class="quota-box">
							<text>男生剩余名额</text>
							<text class="quota-num">{{ remainingText(item.male_remaining) }}</text>
						</view>
						<view class="quota-box">
							<text>女生剩余名额</text>
							<text class="quota-num">{{ remainingText(item.female_remaining) }}</text>
						</view>
					</view>

					<view class="actions">
						<text class="status-badge" :class="statusClass(item)">{{ statusLabel(item) }}</text>
						<button class="action-btn" :class="{ secondary: !canRegister(item), disabled: isRegistered(item) }" :disabled="isRegistered(item)" @tap.stop="goDetail(item.id)">
							{{ actionLabel(item) }}
						</button>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { eventList } from '../../api/mpEvent.js'

export default {
	data() {
		return {
			loading: false,
			events: [],
			activeFilter: 'all',
			filters: [
				{ label: '全部', value: 'all' },
				{ label: '报名中', value: 'registering' },
				{ label: '即将开始', value: 'soon' },
				{ label: '可免费参加', value: 'free' },
			],
		}
	},
	computed: {
		filteredEvents() {
			const list = Array.isArray(this.events) ? this.events : []
			if (this.activeFilter === 'registering') {
				return list.filter((item) => this.canRegister(item))
			}
			if (this.activeFilter === 'soon') {
				return list.filter((item) => this.isSoon(item))
			}
			if (this.activeFilter === 'free') {
				return list.filter((item) => this.isFree(item))
			}
			return list
		},
		stateTitle() {
			const count = this.filteredEvents.length
			if (this.loading) return '正在获取最新活动'
			if (this.activeFilter === 'all') return `共 ${count} 场可选 · 已按时间和空位排序`
			const current = this.filters.find((item) => item.value === this.activeFilter)
			return `${current ? current.label : '筛选'} ${count} 场 · 保留当前条件`
		},
		stateDesc() {
			if (!this.events.length && !this.loading) return '活动发布后会在这里展示，广场页面仍保持占位。'
			return '筛选无结果时可切回全部活动查看，不影响活动详情与报名流程。'
		},
	},
	onShow() {
		this.fetchEvents()
	},
	methods: {
		async fetchEvents() {
			this.loading = true
			try {
				const data = await eventList({ page_no: 1, page_size: 50 })
				this.events = data.items || []
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		goDetail(id) {
			uni.navigateTo({
				url: `/pages/activity/detail/index?id=${id}`,
				fail: (error) => {
					console.error('打开活动详情失败', error)
					uni.showToast({ title: '活动详情页打开失败', icon: 'none' })
				},
			})
		},
		typeLabel(value) {
			return { matchmaking: '相亲会', salon: '主题沙龙', outdoor: '户外活动', festival: '节日活动' }[value] || value || '活动'
		},
		parseTime(value) {
			if (!value) return null
			const time = new Date(String(value).replace(/-/g, '/')).getTime()
			return Number.isNaN(time) ? null : time
		},
		dateParts(value) {
			const text = value ? String(value) : ''
			if (!text) return { monthDay: '时间待定', hm: '' }
			return {
				monthDay: text.slice(5, 10).replace('-', '月') + '日',
				hm: text.slice(11, 16),
			}
		},
		eventTimeText(item) {
			const start = this.dateParts(item.start_time)
			const end = this.dateParts(item.end_time)
			if (!start.hm) return start.monthDay
			return `${start.monthDay} ${start.hm}${end.hm ? `-${end.hm}` : ''}`
		},
		feeLabel(item) {
			const male = Number(item.male_fee || 0)
			const female = Number(item.female_fee || 0)
			if (!male && !female) return '免费参加'
			if (male === female) return `报名费用 ¥${male.toFixed(0)}`
			return `男 ¥${male.toFixed(0)} / 女 ¥${female.toFixed(0)}`
		},
		isFree(item) {
			return Number(item.male_fee || 0) === 0 && Number(item.female_fee || 0) === 0
		},
		remainingTotal(item) {
			return Number(item.male_remaining || 0) + Number(item.female_remaining || 0)
		},
		isFull(item) {
			return this.remainingTotal(item) <= 0
		},
		isDeadlinePassed(item) {
			const deadline = this.parseTime(item.register_deadline)
			return deadline ? deadline <= Date.now() : false
		},
		isSoon(item) {
			const start = this.parseTime(item.start_time)
			if (!start) return false
			const diff = start - Date.now()
			return diff > 0 && diff <= 48 * 60 * 60 * 1000
		},
		canRegister(item) {
			return !this.isRegistered(item) && !this.isFull(item) && !this.isDeadlinePassed(item)
		},
		registrationStatus(item) {
			return item && item.my_registration ? item.my_registration.registration_status : ''
		},
		isRegistered(item) {
			const status = this.registrationStatus(item)
			return status === 'registered' || status === 'checked_in'
		},
		statusLabel(item) {
			if (this.isRegistered(item)) return '已报名'
			if (this.isFull(item)) return '名额已满'
			if (this.isDeadlinePassed(item)) return '报名截止'
			if (this.isSoon(item)) return '即将开始'
			return '报名中'
		},
		statusClass(item) {
			if (this.isRegistered(item)) return 'joined'
			if (this.isFull(item)) return 'full'
			if (this.isDeadlinePassed(item)) return 'closed'
			if (this.isSoon(item)) return 'soon'
			return ''
		},
		actionLabel(item) {
			if (this.isRegistered(item)) return '已报名'
			if (this.registrationStatus(item) === 'pending_payment') return '继续支付'
			return this.canRegister(item) ? '立即报名' : '查看详情'
		},
		remainingText(value) {
			const num = Number(value)
			return Number.isFinite(num) ? String(num) : '-'
		},
		coverLabel(item) {
			const total = Number(item.male_quota || 0) + Number(item.female_quota || 0)
			return `${this.typeLabel(item.event_type)} · ${total > 0 ? `${total} 人` : '限席'}`
		},
		coverClass(item, index) {
			const styles = ['cover-cafe', 'cover-gallery', 'cover-dinner', 'cover-hike', 'cover-salon', 'cover-brunch']
			return styles[index % styles.length]
		},
	},
}
</script>

<style>
.page {
	min-height: 100vh;
	background: #f7f4ef;
	padding: 36rpx 28rpx 132rpx;
	box-sizing: border-box;
}
.header {
	padding: 10rpx 4rpx 24rpx;
}
.brand-row,
.brand,
.topline,
.meta-row,
.actions {
	display: flex;
	align-items: center;
}
.brand-row {
	justify-content: space-between;
	margin-bottom: 28rpx;
}
.brand {
	gap: 14rpx;
	color: #7c716a;
	font-size: 24rpx;
	font-weight: 650;
}
.brand-mark {
	width: 44rpx;
	height: 44rpx;
	border-radius: 16rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #ffffff;
	background: #5c8f68;
	font-size: 24rpx;
	font-weight: 800;
}
.city {
	color: #2f2723;
	font-size: 26rpx;
	font-weight: 650;
}
.title,
.desc,
.state-title,
.state-desc,
.empty-title,
.empty-desc,
.event-title,
.meta-text,
.quota-box text,
.cover-label {
	display: block;
}
.title {
	color: #2f2723;
	font-size: 68rpx;
	font-weight: 800;
	line-height: 1.12;
}
.desc {
	margin-top: 16rpx;
	color: #7c716a;
	font-size: 30rpx;
	line-height: 1.55;
}
.filters {
	width: 100%;
	white-space: nowrap;
	margin-bottom: 28rpx;
}
.filter-row {
	display: flex;
	gap: 16rpx;
}
.chip {
	flex: 0 0 auto;
	border: 1rpx solid #e4d9cf;
	border-radius: 999rpx;
	padding: 16rpx 26rpx;
	color: #7c716a;
	background: rgba(255, 255, 255, 0.76);
	font-size: 26rpx;
	font-weight: 650;
}
.chip.active {
	color: #ffffff;
	border-color: #5c8f68;
	background: #5c8f68;
}
.state-panel {
	margin-bottom: 28rpx;
	padding: 24rpx;
	border: 1rpx dashed #9fbea6;
	border-radius: 28rpx;
	background: #eef5ec;
}
.state-title {
	color: #2f2723;
	font-size: 26rpx;
	font-weight: 750;
}
.state-desc {
	margin-top: 8rpx;
	color: #7c716a;
	font-size: 24rpx;
	line-height: 1.5;
}
.empty-state {
	margin-top: 120rpx;
	padding: 42rpx 28rpx;
	border: 1rpx solid #eadfd6;
	border-radius: 28rpx;
	background: rgba(255, 255, 255, 0.78);
	text-align: center;
}
.empty-title {
	color: #2f2723;
	font-size: 30rpx;
	font-weight: 800;
}
.empty-desc {
	margin-top: 12rpx;
	color: #8a7d75;
	font-size: 24rpx;
}
.reset-btn {
	width: 260rpx;
	height: 76rpx;
	margin-top: 28rpx;
	border-radius: 999rpx;
	border: 0;
	background: #5c8f68;
	color: #ffffff;
	font-size: 26rpx;
	font-weight: 750;
	line-height: 76rpx;
}
.list {
	display: flex;
	flex-direction: column;
	gap: 28rpx;
}
.event-card {
	overflow: hidden;
	border: 1rpx solid #eadfd6;
	border-radius: 32rpx;
	background: #fffdfa;
	box-shadow: 0 18rpx 42rpx rgba(69, 48, 38, 0.08);
}
.cover-wrap {
	position: relative;
	height: 308rpx;
	overflow: hidden;
	background: #e5dbd1;
}
.cover-img,
.cover-empty,
.cover-shade {
	position: absolute;
	top: 0;
	right: 0;
	bottom: 0;
	left: 0;
	width: 100%;
	height: 100%;
}
.cover-shade {
	background: linear-gradient(180deg, rgba(0, 0, 0, 0) 42%, rgba(0, 0, 0, 0.38));
}
.cover-cafe {
	background: radial-gradient(circle at 20% 28%, #f1dfbd 0 9%, transparent 10%), radial-gradient(circle at 74% 34%, #d79a66 0 8%, transparent 9%), linear-gradient(135deg, #c8ad92, #846f60);
}
.cover-gallery {
	background: linear-gradient(90deg, transparent 0 22%, rgba(255, 255, 255, 0.34) 22% 24%, transparent 24% 58%, rgba(255, 255, 255, 0.26) 58% 60%, transparent 60%), linear-gradient(135deg, #cdd7b8, #789876);
}
.cover-dinner {
	background: radial-gradient(circle at 78% 24%, #d46f55 0 10%, transparent 11%), radial-gradient(circle at 28% 70%, #e8d4a6 0 16%, transparent 17%), linear-gradient(135deg, #b88574, #5c4039);
}
.cover-hike {
	background: linear-gradient(155deg, transparent 0 45%, #3f8a63 45% 67%, transparent 67%), linear-gradient(135deg, #a8d7dd, #7baa73);
}
.cover-salon {
	background: radial-gradient(circle at 35% 34%, #efd0ca 0 14%, transparent 15%), linear-gradient(135deg, #ddd0b7, #b8897d);
}
.cover-brunch {
	background: radial-gradient(circle at 70% 70%, #f3e8bd 0 15%, transparent 16%), linear-gradient(135deg, #e6d9b9, #c49c62);
}
.cover-label {
	position: absolute;
	left: 24rpx;
	bottom: 24rpx;
	z-index: 2;
	color: #ffffff;
	font-size: 24rpx;
	font-weight: 750;
	text-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.36);
}
.card-body {
	padding: 28rpx;
}
.topline {
	justify-content: space-between;
	align-items: flex-start;
	gap: 20rpx;
}
.event-title {
	flex: 1;
	color: #2f2723;
	font-size: 36rpx;
	font-weight: 800;
	line-height: 1.36;
}
.tag {
	flex: 0 0 auto;
	border-radius: 999rpx;
	padding: 10rpx 16rpx;
	color: #4e865e;
	background: #eef5ec;
	font-size: 22rpx;
	font-weight: 800;
}
.meta {
	display: flex;
	flex-direction: column;
	gap: 14rpx;
	margin: 22rpx 0 24rpx;
	color: #7c716a;
	font-size: 26rpx;
	line-height: 1.42;
}
.meta-row {
	gap: 14rpx;
	min-width: 0;
}
.ico {
	width: 36rpx;
	color: #6f625b;
	text-align: center;
	font-size: 26rpx;
	font-weight: 700;
}
.meta-text {
	flex: 1;
	min-width: 0;
}
.fee {
	color: #2f2723;
	font-size: 26rpx;
	font-weight: 800;
}
.fee.free {
	color: #5c8f68;
}
.quota {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 16rpx;
	margin-bottom: 24rpx;
}
.quota-box {
	padding: 18rpx 20rpx;
	border: 1rpx solid #eadfd6;
	border-radius: 24rpx;
	background: #fbf8f2;
}
.quota-box text:first-child {
	color: #8a7d75;
	font-size: 22rpx;
}
.quota-num {
	margin-top: 6rpx;
	color: #2f2723;
	font-size: 34rpx;
	font-weight: 800;
}
.actions {
	justify-content: space-between;
	gap: 24rpx;
	padding-top: 24rpx;
	border-top: 1rpx solid #eadfd6;
}
.status-badge {
	position: relative;
	flex: 0 0 auto;
	padding-left: 22rpx;
	color: #7c716a;
	font-size: 24rpx;
	font-weight: 750;
}
.status-badge::before {
	content: "";
	position: absolute;
	left: 0;
	top: 50%;
	width: 12rpx;
	height: 12rpx;
	margin-top: -6rpx;
	border-radius: 50%;
	background: #5c8f68;
}
.status-badge.soon::before {
	background: #c59a45;
}
.status-badge.joined::before {
	background: #8a7d75;
}
.status-badge.full::before,
.status-badge.closed::before {
	background: #8a7d75;
}
.action-btn {
	min-width: 216rpx;
	height: 80rpx;
	margin: 0;
	border: 0;
	border-radius: 999rpx;
	padding: 0 32rpx;
	color: #ffffff;
	background: #5c8f68;
	box-shadow: 0 14rpx 26rpx rgba(92, 143, 104, 0.22);
	font-size: 28rpx;
	font-weight: 800;
	line-height: 80rpx;
}
.action-btn.secondary {
	color: #2f2723;
	background: #efe9e1;
	box-shadow: none;
}
.action-btn.disabled {
	color: #8a7d75;
	background: #eee8e0;
	box-shadow: none;
}
.action-btn::after,
.reset-btn::after {
	border: 0;
}
</style>
