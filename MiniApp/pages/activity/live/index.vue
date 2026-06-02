<template>
	<view class="page" :style="pageStyle">
		<view class="notice">
			<view class="notice-icon">喇叭</view>
			<view class="notice-card">
				<text class="notice-title">系统消息</text>
				<text class="notice-text">{{ welcomeMessage }}</text>
			</view>
		</view>

		<view class="side-actions">
			<button class="side-btn" @tap="openPanel('barrage')">弹幕</button>
			<button class="side-btn disabled">霸屏</button>
			<button class="side-btn disabled">礼物</button>
			<button class="side-btn disabled">福利</button>
		</view>

		<view v-if="panel === 'barrage'" class="sheet-mask" @tap="closePanel">
			<view class="sheet" @tap.stop>
				<text class="sheet-title">普通弹幕</text>
				<textarea v-model="barrageContent" class="barrage-input" maxlength="50" placeholder="请输入弹幕内容" />
				<button class="send-btn" :disabled="!canSendBarrage" :class="{ disabled: !canSendBarrage }" @tap="sendBarrage">发送</button>
			</view>
		</view>

		<view class="bottom-bar">
			<button class="chat-btn" @tap="openPanel('barrage')">聊</button>
			<view class="input-placeholder" @tap="openPanel('barrage')">说点什么...</view>
			<button class="more-btn" @tap="openPanel('barrage')">▦</button>
		</view>
	</view>
</template>

<script>
import { checkinScene, sendEventBarrage } from '../../../api/mpEvent.js'
import { ensureRegisteredSession } from '../../../utils/mpSession.js'

export default {
	data() {
		return {
			scene: '',
			activityScreen: {},
			event: {},
			participant: null,
			panel: '',
			barrageContent: '',
			barrageSubmitting: false,
		}
	},
	computed: {
		welcomeMessage() {
			return this.activityScreen?.theme_config?.welcome_message || '欢迎来到觅爱互动大厅，倡导文明用语，共建快乐活动现场！'
		},
		pageStyle() {
			const bg = this.activityScreen?.theme_config?.mobile_background_url || ''
			return bg ? `background-image:url(${bg});` : 'background-color:#ffffff;'
		},
		canSendBarrage() {
			return !this.barrageSubmitting && Boolean(String(this.barrageContent || '').trim())
		},
	},
	onLoad(options) {
		this.scene = decodeURIComponent(options.scene || '')
		this.load()
	},
	methods: {
		async load() {
			if (!this.scene) {
				uni.showToast({ title: '活动入口无效', icon: 'none' })
				return
			}
			try {
				const data = await checkinScene(this.scene)
				this.activityScreen = data.activity_screen || {}
				this.event = data.event || {}
				this.participant = data.participant || null
				if (!this.participant) {
					uni.redirectTo({ url: `/pages/activity/checkin/index?scene=${encodeURIComponent(this.scene)}` })
				}
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			}
		},
		openPanel(name) {
			this.panel = name
		},
		closePanel() {
			this.panel = ''
		},
		async sendBarrage() {
			const content = this.barrageContent.trim()
			if (!content || this.barrageSubmitting) return
			try {
				const session = await ensureRegisteredSession()
				if (!session) {
					uni.navigateTo({ url: `/pages/register/index?redirect=${encodeURIComponent(`/pages/activity/live/index?scene=${this.scene}`)}` })
					return
				}
			} catch (error) {
				uni.showToast({ title: error.message || '微信登录失败', icon: 'none' })
				return
			}
			this.barrageSubmitting = true
			try {
				await sendEventBarrage(this.event.id, { content })
				this.barrageContent = ''
				this.closePanel()
				uni.showToast({ title: '已发送', icon: 'success' })
			} catch (error) {
				uni.showToast({ title: error.message || '发送失败', icon: 'none' })
			} finally {
				this.barrageSubmitting = false
			}
		},
	},
}
</script>

<style>
.page {
	position: relative;
	min-height: 100vh;
	overflow: hidden;
	background-color: #0a0d14;
	background-position: center;
	background-size: cover;
	color: #fff;
}
.page::before {
	position: absolute;
	inset: 0;
	background: rgba(0, 0, 0, 0.36);
	content: '';
}
.notice,
.side-actions,
.bottom-bar {
	position: relative;
	z-index: 1;
}
.notice {
	display: flex;
	gap: 18rpx;
	padding: 70rpx 34rpx 0;
}
.notice-icon {
	width: 68rpx;
	height: 68rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	background: #5863f4;
	font-size: 22rpx;
}
.notice-card {
	flex: 1;
	border-radius: 12rpx;
	background: rgba(0, 0, 0, 0.52);
	padding: 22rpx;
}
.notice-title,
.notice-text {
	display: block;
}
.notice-title {
	color: rgba(255, 255, 255, 0.62);
	font-size: 27rpx;
}
.notice-text {
	margin-top: 14rpx;
	color: #31fff3;
	font-size: 31rpx;
	line-height: 1.55;
}
.side-actions {
	position: absolute;
	right: 22rpx;
	top: 38vh;
	display: grid;
	gap: 22rpx;
}
.side-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 108rpx;
	height: 78rpx;
	padding: 0;
	box-sizing: border-box;
	border: 0;
	border-radius: 999rpx;
	background: rgba(88, 99, 244, 0.88);
	color: #fff;
	font-size: 24rpx;
	font-weight: 900;
	line-height: 1;
	white-space: nowrap;
}
.side-btn.disabled {
	background: rgba(255, 255, 255, 0.18);
	color: rgba(255, 255, 255, 0.58);
}
.bottom-bar {
	position: fixed;
	right: 24rpx;
	bottom: 28rpx;
	left: 24rpx;
	display: flex;
	align-items: center;
	gap: 18rpx;
}
.chat-btn,
.more-btn {
	width: 78rpx;
	height: 78rpx;
	border: 0;
	border-radius: 50%;
	background: rgba(0, 0, 0, 0.56);
	color: #fff;
	font-size: 34rpx;
}
.input-placeholder {
	flex: 1;
	height: 72rpx;
	border-radius: 999rpx;
	background: rgba(0, 0, 0, 0.52);
	color: rgba(255, 255, 255, 0.58);
	padding: 0 30rpx;
	line-height: 72rpx;
	font-size: 28rpx;
}
.sheet-mask {
	position: fixed;
	inset: 0;
	z-index: 3;
	display: flex;
	align-items: flex-end;
	background: rgba(0, 0, 0, 0.48);
}
.sheet {
	width: 100%;
	border-radius: 28rpx 28rpx 0 0;
	background: #050507;
	padding: 34rpx;
	box-sizing: border-box;
}
.sheet-title {
	display: block;
	text-align: center;
	font-size: 34rpx;
	font-weight: 900;
}
.barrage-input {
	width: 100%;
	height: 176rpx;
	margin-top: 30rpx;
	border-radius: 12rpx;
	background: #242424;
	padding: 22rpx;
	color: #fff;
	font-size: 30rpx;
	box-sizing: border-box;
}
.send-btn {
	width: 78%;
	height: 88rpx;
	margin: 34rpx auto 18rpx;
	border: 0;
	border-radius: 999rpx;
	background: #6571ef;
	color: #fff;
	font-size: 32rpx;
	font-weight: 900;
}
.send-btn.disabled {
	background: #3d4058;
}
button::after {
	border: 0;
}
</style>
