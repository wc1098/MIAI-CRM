<template>
	<view class="page">
		<view v-if="person" class="card profile-card">
			<image class="avatar" :src="avatarUrl(user.avatar_url)" mode="aspectFill"></image>
			<view class="profile-info">
				<text class="name">{{ user.nickname || person.name }}</text>
				<text class="meta">{{ maskedMobile }}</text>
				<text class="cert">{{ certificationLabel }}</text>
			</view>
		</view>

		<view v-if="person" class="card menu-card">
			<view class="menu-head">
				<text class="title">个人信息维护</text>
				<text class="desc">完善资料后，后续订阅推荐会更贴近你的期待。</text>
			</view>
			<view class="menu-row" @tap="goPreference">
				<view>
					<text class="menu-title">择偶要求</text>
					<text class="menu-desc">年龄、地区、学历、婚况等偏好</text>
				</view>
				<text class="arrow">›</text>
			</view>
			<view class="menu-row" @tap="goCertification">
				<view>
					<text class="menu-title">认证中心</text>
					<text class="menu-desc">实名、真人照片和资料认证</text>
				</view>
				<text class="arrow">›</text>
			</view>
			<view class="menu-row disabled">
				<view>
					<text class="menu-title">个人资料</text>
					<text class="menu-desc">基础资料维护暂未开放</text>
				</view>
				<text class="pill">占位</text>
			</view>
			<view class="menu-row disabled">
				<view>
					<text class="menu-title">隐身设置</text>
					<text class="menu-desc">后续在设置中统一维护</text>
				</view>
				<text class="pill">占位</text>
			</view>
		</view>

		<view v-else class="card">
			<text class="title">还未注册</text>
			<text class="desc">完成完整资料后，系统会同步生成 CRM 线索，方便门店及时跟进。</text>
			<button class="primary-btn" @click="goRegister">立即注册</button>
		</view>
	</view>
</template>

<script>
import { getPerson, getUser, setSession } from '../../utils/storage.js'
import { mpMe } from '../../api/mpAuth.js'
import { ensureMpSession } from '../../utils/mpSession.js'
import { ossImage } from '../../utils/ossImage.js'

export default {
	data() {
		return {
			user: getUser() || {},
			person: getPerson(),
		}
	},
	computed: {
		maskedMobile() {
			const mobile = this.person && this.person.primary_mobile
			if (!mobile || mobile.length < 7) return mobile || ''
			return `${mobile.slice(0, 3)}****${mobile.slice(-4)}`
		},
		certificationLabel() {
			const level = this.person && this.person.certification_level
			return ({ basic: '基础认证', advanced: '高级认证', premium: '尊享认证' }[level]) || '未认证'
		},
	},
	onShow() {
		this.loadMe()
	},
	onPullDownRefresh() {
		this.loadMe().finally(() => {
			uni.stopPullDownRefresh()
		})
	},
	methods: {
		avatarUrl(url) {
			return ossImage(url, { width: 180, height: 180 }) || '/static/logo.png'
		},
		goRegister() {
			uni.navigateTo({ url: '/pages/register/index' })
		},
		goPreference() {
			uni.navigateTo({ url: '/pages/mine/preference' })
		},
		goCertification() {
			uni.switchTab({ url: '/pages/certification/index' })
		},
		async loadMe() {
			try {
				await ensureMpSession()
				const result = await mpMe()
				setSession(result)
				this.user = result.user || {}
				this.person = result.person || null
			} catch (error) {
				this.user = getUser() || {}
				this.person = getPerson()
			}
		},
	},
}
</script>

<style>
.profile-card {
	align-items: center;
	display: flex;
}

.avatar {
	border-radius: 50%;
	height: 116rpx;
	width: 116rpx;
}

.profile-info {
	margin-left: 24rpx;
}

.name,
.meta,
.cert,
.title,
.desc {
	display: block;
}

.name,
.title {
	font-size: 36rpx;
	font-weight: 700;
}

.meta,
.desc {
	color: #7a6f69;
	font-size: 28rpx;
	margin-top: 12rpx;
}

.cert {
	display: inline-block;
	margin-top: 12rpx;
	border-radius: 999rpx;
	background: #eef5ec;
	color: #4e865e;
	font-size: 22rpx;
	font-weight: 800;
	padding: 8rpx 16rpx;
}

.desc {
	line-height: 1.6;
	margin-bottom: 28rpx;
}

.menu-card {
	margin-top: 24rpx;
}

.menu-head {
	border-bottom: 1rpx solid rgba(91, 68, 58, 0.1);
	padding-bottom: 18rpx;
}

.menu-row {
	align-items: center;
	border-bottom: 1rpx solid rgba(91, 68, 58, 0.08);
	display: flex;
	justify-content: space-between;
	min-height: 112rpx;
}

.menu-row:last-child {
	border-bottom: 0;
}

.menu-row.disabled {
	opacity: 0.58;
}

.menu-title,
.menu-desc {
	display: block;
}

.menu-title {
	color: #4b342d;
	font-size: 30rpx;
	font-weight: 700;
}

.menu-desc {
	color: #8d7f78;
	font-size: 24rpx;
	margin-top: 8rpx;
}

.arrow {
	color: #b85c67;
	font-size: 52rpx;
	line-height: 1;
}

.pill {
	background: #f3eee7;
	border-radius: 999rpx;
	color: #9a8a7f;
	font-size: 22rpx;
	padding: 8rpx 18rpx;
}
</style>
