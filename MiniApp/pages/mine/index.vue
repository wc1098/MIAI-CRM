<template>
	<view class="page">
		<view v-if="person" class="card profile-card">
			<image class="avatar" :src="user.avatar_url || '/static/logo.png'" mode="aspectFill"></image>
			<view class="profile-info">
				<text class="name">{{ user.nickname || person.name }}</text>
				<text class="meta">{{ maskedMobile }}</text>
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
	},
	onShow() {
		this.loadMe()
	},
	methods: {
		goRegister() {
			uni.navigateTo({ url: '/pages/register/index' })
		},
		async loadMe() {
			try {
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

.desc {
	line-height: 1.6;
	margin-bottom: 28rpx;
}
</style>
