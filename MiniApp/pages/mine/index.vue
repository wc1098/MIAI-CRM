<template>
	<view class="page mine-page">
		<view v-if="!registered" class="guest-card">
			<view class="brand-row">
				<view class="brand">
					<text class="brand-mark">我</text>
					<text>觅AI 个人中心</text>
				</view>
			</view>
			<text class="guest-title">先完成注册资料</text>
			<text class="guest-desc">补齐真实资料后，可以使用喜欢、收藏、认证、活动和订阅推荐。</text>
			<button class="primary-btn" @tap="goRegister">立即注册</button>
		</view>

		<template v-else>
			<view class="hero-card">
				<image class="avatar" :src="thumb(profileAvatar, 220, 220) || '/static/logo.png'" mode="aspectFill"></image>
				<view class="hero-info">
					<view class="name-row">
						<text class="name">{{ displayName }}</text>
						<text class="cert">{{ certificationLabel }}</text>
					</view>
					<text class="meta">ID {{ person.display_no || '-' }} · {{ maskedMobile }}</text>
					<text class="privacy" :class="{ on: user.is_invisible }">{{ user.is_invisible ? '已隐身' : '正常展示' }}</text>
				</view>
			</view>

			<view class="completion-card" @tap="goProfile">
				<view class="section-head">
					<view>
						<text class="section-title">资料完整度 {{ completion.percent || 0 }}%</text>
						<text class="section-desc">{{ missingText }}</text>
					</view>
					<text class="link">去完善</text>
				</view>
				<view class="progress"><view class="progress-bar" :style="{ width: `${completion.percent || 0}%` }"></view></view>
			</view>

			<view class="stats-grid">
				<view class="stat" @tap="goRelations('received')"><text class="stat-num">{{ stats.likes_received || 0 }}</text><text class="stat-label">喜欢我的</text></view>
				<view class="stat" @tap="goRelations('sent')"><text class="stat-num">{{ stats.likes_sent || 0 }}</text><text class="stat-label">我喜欢的</text></view>
				<view class="stat" @tap="goRelations('favorites')"><text class="stat-num">{{ stats.favorites || 0 }}</text><text class="stat-label">我的收藏</text></view>
				<view class="stat" @tap="goUnlocks"><text class="stat-num">{{ stats.unlocks || 0 }}</text><text class="stat-label">已解锁</text></view>
				<view class="stat wide" @tap="goCertification"><text class="stat-num">{{ stats.coupon_count || 0 }}</text><text class="stat-label">联系方式解锁券</text></view>
			</view>

			<view v-if="todos.length" class="guide-card">
				<view class="section-head">
					<view>
						<text class="section-title">下一步建议</text>
						<text class="section-desc">按当前状态给你排好优先级</text>
					</view>
				</view>
				<view v-for="item in todos" :key="item.type" class="todo-row" @tap="openUrl(item.url)">
					<view>
						<text class="todo-title">{{ item.title }}</text>
						<text class="todo-desc">{{ item.desc }}</text>
					</view>
					<text class="arrow">›</text>
				</view>
			</view>

			<view class="menu-card">
				<view class="section-head">
					<text class="section-title">常用功能</text>
					<text class="section-desc">资料、互动和服务都放在这里</text>
				</view>
				<view class="menu-grid">
					<view v-for="item in menus" :key="item.title" class="menu-item" @tap="openMenu(item)">
						<text class="menu-icon">{{ item.icon }}</text>
						<text class="menu-title">{{ item.title }}</text>
						<text class="menu-desc">{{ item.desc }}</text>
					</view>
				</view>
			</view>
		</template>
	</view>
</template>

<script>
import { mineCenter } from '../../api/mpProfile.js'
import { ensureMpSession } from '../../utils/mpSession.js'
import { ossImage } from '../../utils/ossImage.js'

export default {
	data() {
		return {
			loading: false,
			registered: false,
			user: {},
			person: {},
			completion: { percent: 0, missing_fields: [] },
			stats: {},
			todos: [],
			menus: [
				{ title: '个人资料', desc: '照片和基础情况', icon: '资', url: '/pages/mine/profile' },
				{ title: '择偶要求', desc: '推荐筛选条件', icon: '择', url: '/pages/mine/preference' },
				{ title: '认证中心', desc: '真实等级背书', icon: '认', url: '/pages/certification/index', tab: true },
				{ title: '喜欢收藏', desc: '互动关系', icon: '喜', url: '/pages/mine/relations' },
				{ title: '解锁记录', desc: '已解锁联系方式', icon: '联', url: '/pages/mine/unlocks' },
				{ title: '我的活动', desc: '报名和签到', icon: '活', url: '/pages/mine/events' },
				{ title: '订阅推荐', desc: '专属推荐服务', icon: '订', url: '/pages/subscription/index', tab: true },
				{ title: '隐私设置', desc: '隐身展示控制', icon: '隐', url: '/pages/mine/privacy' },
			],
		}
	},
	computed: {
		displayName() {
			return this.user.nickname || this.person.name || '觅AI用户'
		},
		profileAvatar() {
			const photos = this.person.photo_urls || []
			return this.user.avatar_url || photos[0]
		},
		maskedMobile() {
			const mobile = this.person.primary_mobile || this.user.mobile || ''
			if (!mobile || mobile.length < 7) return mobile || ''
			return `${mobile.slice(0, 3)}****${mobile.slice(-4)}`
		},
		certificationLabel() {
			return this.person.certification_level_name || ({ basic: '基础认证', advanced: '高级认证', premium: '尊享认证' }[this.person.certification_level]) || '未认证'
		},
		missingText() {
			const missing = this.completion.missing_fields || []
			if (!missing.length) return '资料已经比较完整，保持更新就好'
			return `还缺：${missing.slice(0, 4).join('、')}`
		},
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		thumb(url, width, height) {
			return ossImage(url, { width, height })
		},
		async load() {
			this.loading = true
			try {
				await ensureMpSession()
				const data = await mineCenter()
				this.registered = !!data.is_registered
				this.user = data.user || {}
				this.person = data.person || {}
				this.completion = data.profile_completion || { percent: 0, missing_fields: [] }
				this.stats = data.stats || {}
				this.todos = data.todos || []
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		goRegister() {
			uni.navigateTo({ url: '/pages/register/index' })
		},
		goProfile() {
			uni.navigateTo({ url: '/pages/mine/profile' })
		},
		goCertification() {
			uni.switchTab({ url: '/pages/certification/index' })
		},
		goUnlocks() {
			uni.navigateTo({ url: '/pages/mine/unlocks' })
		},
		goRelations(tab) {
			uni.navigateTo({ url: `/pages/mine/relations?tab=${tab}` })
		},
		openUrl(url) {
			if (!url) return
			if (url === '/pages/certification/index' || url === '/pages/subscription/index') {
				uni.switchTab({ url })
				return
			}
			uni.navigateTo({ url })
		},
		openMenu(item) {
			if (item.tab) {
				uni.switchTab({ url: item.url })
				return
			}
			uni.navigateTo({ url: item.url })
		},
	},
}
</script>

<style>
.mine-page { min-height: 100vh; padding: 24rpx; background: #f7f4ef; box-sizing: border-box; }
.guest-card, .hero-card, .completion-card, .guide-card, .menu-card { background: #fffaf3; border-radius: 28rpx; box-shadow: 0 12rpx 32rpx rgba(95, 70, 50, .08); padding: 28rpx; margin-bottom: 24rpx; }
.brand-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 22rpx; }
.brand { color: #7a594b; font-size: 26rpx; font-weight: 700; display: flex; align-items: center; gap: 12rpx; }
.brand-mark { width: 44rpx; height: 44rpx; border-radius: 50%; background: #c95d65; color: #fff; display: inline-flex; align-items: center; justify-content: center; text-align: center; line-height: 44rpx; }
.guest-title { display: block; color: #3f2d28; font-size: 42rpx; font-weight: 800; }
.guest-desc, .section-desc, .todo-desc, .menu-desc, .meta { display: block; color: #8d7f78; font-size: 24rpx; line-height: 1.6; margin-top: 8rpx; }
.primary-btn { margin-top: 30rpx; height: 88rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 30rpx; font-weight: 700; }
.hero-card { display: flex; align-items: center; background: linear-gradient(135deg, #fff7eb, #fffaf3 58%, #f6eadc); }
.avatar { width: 136rpx; height: 136rpx; border-radius: 32rpx; background: #eadbd0; flex-shrink: 0; }
.hero-info { flex: 1; margin-left: 24rpx; min-width: 0; }
.name-row { display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap; }
.name { color: #3f2d28; font-size: 38rpx; font-weight: 800; }
.cert, .privacy { border-radius: 999rpx; font-size: 22rpx; font-weight: 700; padding: 8rpx 16rpx; }
.cert { background: #eef5ec; color: #4e865e; }
.privacy { display: inline-block; margin-top: 12rpx; background: #f0e7dc; color: #8a6d5c; }
.privacy.on { background: #fbe7ea; color: #b94f5c; }
.section-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20rpx; }
.section-title { display: block; color: #4b342d; font-size: 32rpx; font-weight: 800; }
.link { color: #c95d65; font-size: 26rpx; font-weight: 700; white-space: nowrap; }
.progress { height: 16rpx; border-radius: 999rpx; background: #efe5dc; margin-top: 24rpx; overflow: hidden; }
.progress-bar { height: 100%; border-radius: 999rpx; background: linear-gradient(90deg, #c95d65, #e3a066); }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14rpx; margin-bottom: 24rpx; }
.stat { background: #fffaf3; border-radius: 24rpx; box-shadow: 0 8rpx 24rpx rgba(95, 70, 50, .06); padding: 22rpx 10rpx; text-align: center; }
.stat.wide { grid-column: span 4; display: flex; justify-content: center; gap: 16rpx; align-items: baseline; }
.stat-num { display: block; color: #c95d65; font-size: 36rpx; font-weight: 900; }
.stat-label { color: #806f66; font-size: 22rpx; margin-top: 6rpx; }
.todo-row { display: flex; justify-content: space-between; align-items: center; padding: 22rpx 0; border-top: 1rpx solid rgba(91, 68, 58, .08); }
.todo-title { display: block; color: #4b342d; font-size: 28rpx; font-weight: 800; }
.arrow { color: #c95d65; font-size: 48rpx; }
.menu-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16rpx; margin-top: 24rpx; }
.menu-item { background: #fff; border: 1rpx solid rgba(91, 68, 58, .08); border-radius: 22rpx; padding: 22rpx; min-height: 128rpx; }
.menu-icon { width: 46rpx; height: 46rpx; border-radius: 16rpx; background: #f6e6dc; color: #b85c67; display: block; text-align: center; line-height: 46rpx; font-size: 24rpx; font-weight: 800; margin-bottom: 14rpx; }
.menu-title { display: block; color: #4b342d; font-size: 28rpx; font-weight: 800; }
</style>
