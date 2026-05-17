<template>
	<view class="page detail-page">
		<view v-if="loading" class="empty-state">
			<text class="empty-title">正在加载资料...</text>
		</view>

		<view v-else-if="!detail.visible" class="hidden-state">
			<text class="hidden-title">{{ detail.message || '该用户暂不可见' }}</text>
			<text class="hidden-desc">对方当前开启了隐身保护，暂时不能查看资料。</text>
		</view>

		<view v-else class="content">
			<view class="hero">
				<swiper class="photo-swiper" circular :indicator-dots="false" @change="onPhotoChange">
					<swiper-item v-for="item in photos" :key="item.key">
						<view class="photo-wrap">
							<image class="hero-photo" :class="{ blurred: item.blurred }" :src="item.displayUrl || '/static/logo.png'" mode="aspectFill"></image>
							<view v-if="item.blurred" class="blur-mask">
								<text>解锁后查看完整相册</text>
							</view>
						</view>
					</swiper-item>
				</swiper>
				<view v-if="photos.length > 1" class="photo-count">{{ currentPhotoIndex + 1 }}/{{ photos.length }}</view>
				<view v-if="photos.length > 1" class="photo-dots">
					<view v-for="(item, index) in photos" :key="item.key" class="photo-dot" :class="{ active: index === currentPhotoIndex }"></view>
				</view>
				<view class="hero-panel">
					<view>
						<view class="name-row">
							<text class="name">{{ displayName }}</text>
							<text class="display-id">ID {{ person.display_no }}</text>
						</view>
						<text class="meta">{{ ageText(person.age) }} · {{ heightText(person.height_cm) }}</text>
						<text class="meta">{{ person.residence || '常驻地待补充' }} · {{ person.occupation || '职业待补充' }}</text>
					</view>
					<view class="hero-actions">
						<button v-if="!detail.is_self" class="like-circle" :class="{ active: interaction.liked }" @tap.stop="toggleLike">{{ interaction.liked ? '♥' : '♡' }}</button>
						<text class="cert">{{ person.certification_status || '未认证' }}</text>
					</view>
				</view>
			</view>

			<view v-if="detail.is_self" class="self-tip">
				<text>这是你的资料预览。分享链接进入时可检查展示效果。</text>
			</view>

			<view v-if="!detail.is_self && !detail.is_unlocked" class="heartbeat-card" @tap="goUnlock">
				<view class="heartbeat-head">
					<text class="heartbeat-title">解锁联系方式</text>
					<text class="heartbeat-score-value">{{ interaction.heartbeat_score || 0 }}/{{ interaction.heartbeat_unlock_score || 100 }}</text>
				</view>
				<view class="progress"><view class="progress-inner" :style="progressStyle"></view></view>
				<text class="heartbeat-desc">继续了解、喜欢、收藏或完成默契题，可提升心动值。达到目标后可查看手机号。</text>
			</view>

			<view v-if="detail.is_unlocked && person.mobile" class="contact-card" @tap="goContact">
				<view>
					<text class="contact-title">已解锁联系方式</text>
					<text class="contact-desc">可重复查看手机号，不重复收费</text>
				</view>
				<text class="contact-action">查看</text>
			</view>

			<view class="section">
				<view class="section-title">个人情况</view>
				<view class="tag-grid">
					<text class="tag">{{ person.education || '学历待补充' }}</text>
					<text class="tag">{{ person.annual_income || '收入待补充' }}</text>
					<text class="tag">{{ person.marital_status || '婚况待补充' }}</text>
					<text class="tag">{{ person.house_status || '房产待补充' }}</text>
					<text class="tag">{{ person.car_status || '车辆待补充' }}</text>
					<text class="tag">{{ person.ethnicity || '民族待补充' }}</text>
				</view>
				<view class="info-list">
					<view class="info-row"><text>籍贯</text><text>{{ person.hometown || '-' }}</text></view>
					<view class="info-row"><text>常驻地</text><text>{{ person.residence || '-' }}</text></view>
				</view>
			</view>

			<view class="section">
				<view class="section-title">觅AI印象</view>
				<text class="ai-content">{{ aiContent }}</text>
			</view>
		</view>

		<view v-if="!loading && detail.visible" class="bottom-bar">
			<button class="bar-btn" open-type="share">转发</button>
			<button v-if="!detail.is_self" class="bar-btn" :class="{ active: interaction.favorited }" @tap="toggleFavorite">{{ interaction.favorited ? '已收藏' : '收藏' }}</button>
			<button v-if="detail.is_self" class="primary-btn">预览中</button>
			<button v-else-if="detail.is_unlocked" class="primary-btn" @tap="goContact">查看手机号</button>
			<button v-else class="primary-btn" @tap="goUnlock">解锁联系方式</button>
		</view>
	</view>
</template>

<script>
import { completeUnlockTask, favoriteProfile, likeProfile, plazaDetail, unfavoriteProfile, unlikeProfile } from '../../../api/mpPlaza.js'
import { ensureRegisteredSession } from '../../../utils/mpSession.js'
import { ossImage, ossPreview } from '../../../utils/ossImage.js'

export default {
	data() {
		return {
			displayNo: '',
			loading: false,
			currentPhotoIndex: 0,
			detail: { visible: true, person: {}, interaction: {} },
		}
	},
	computed: {
		person() {
			return this.detail.person || {}
		},
		interaction() {
			return this.detail.interaction || {}
		},
		photos() {
			const list = this.person.photos || []
			const source = list.length ? list : [{ url: this.person.avatar_url || '/static/logo.png', blurred: false }]
			return source.map((item, index) => ({
				url: item.url,
				displayUrl: ossImage(item.url, { width: 750, height: 860, quality: 78 }),
				blurred: item.blurred,
				key: `${item.url || 'photo'}-${index}`,
			}))
		},
		aiContent() {
			return this.detail.ai_profile && this.detail.ai_profile.content ? this.detail.ai_profile.content : '暂无觅AI印象'
		},
		progressPercent() {
			const score = Number(this.interaction.heartbeat_score || 0)
			const target = Number(this.interaction.heartbeat_unlock_score || 100)
			return Math.max(0, Math.min(100, Math.round((score / target) * 100)))
		},
		progressStyle() {
			return `width: ${this.progressPercent}%`
		},
		displayName() {
			const nickname = this.person.nickname
			if (nickname && nickname !== this.person.name) return nickname
			return this.person.display_name || '觅AI用户'
		},
	},
	onLoad(options) {
		this.displayNo = options.display_no || options.displayNo || ''
	},
	onShow() {
		this.fetchDetail()
	},
	onPullDownRefresh() {
		this.fetchDetail().finally(() => uni.stopPullDownRefresh())
	},
	onShareAppMessage() {
		if (this.displayNo) this.completeShareTask()
		return {
			title: this.profileShareTitle(),
			path: `/pages/plaza/detail/index?display_no=${this.displayNo}`,
			imageUrl: this.person.avatar_url ? ossPreview(this.person.avatar_url, { width: 800 }) : undefined,
		}
	},
	onShareTimeline() {
		if (this.displayNo) this.completeShareTask()
		return {
			title: this.profileShareTitle(),
			query: `display_no=${this.displayNo}`,
			imageUrl: this.person.avatar_url ? ossPreview(this.person.avatar_url, { width: 800 }) : undefined,
		}
	},
	methods: {
		profileShareTitle() {
			const parts = [
				this.displayName,
				this.ageText(this.person.age),
				this.person.annual_income || '收入待补充',
				this.person.occupation || '职业待补充',
			].filter((item) => item && item !== '-')
			return `${parts.join('｜')}，在觅AI认真相识`
		},
		async fetchDetail() {
			if (!this.displayNo) return
			this.loading = true
			try {
				this.detail = await plazaDetail(this.displayNo)
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			} finally {
				this.loading = false
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
			uni.navigateTo({ url: `/pages/register/index?redirect=${encodeURIComponent(`/pages/plaza/detail/index?display_no=${this.displayNo}`)}` })
			return false
		},
		async toggleLike() {
			if (!(await this.ensureRegistered())) return
			this.detail = this.interaction.liked ? await unlikeProfile(this.displayNo) : await likeProfile(this.displayNo)
		},
		async toggleFavorite() {
			if (!(await this.ensureRegistered())) return
			this.detail = this.interaction.favorited ? await unfavoriteProfile(this.displayNo) : await favoriteProfile(this.displayNo)
		},
		async goUnlock() {
			if (!(await this.ensureRegistered())) return
			uni.navigateTo({ url: `/pages/plaza/unlock/index?display_no=${this.displayNo}` })
		},
		async goContact() {
			if (!(await this.ensureRegistered())) return
			uni.navigateTo({ url: `/pages/plaza/unlock/contact?display_no=${this.displayNo}` })
		},
		completeShareTask() {
			completeUnlockTask(this.displayNo, 'share_card').catch(() => {})
		},
		onPhotoChange(event) {
			this.currentPhotoIndex = event.detail.current || 0
		},
		ageText(age) {
			return age ? `${age}岁` : '-'
		},
		heightText(height) {
			return height ? `${height}cm` : '-'
		},
	},
}
</script>

<style>
page { background: #f7f1e8; }
.detail-page { min-height: 100vh; padding-bottom: 150rpx; color: #3f2f2a; }
.content { padding-bottom: 24rpx; }
.hero { position: relative; height: 860rpx; overflow: hidden; border-bottom-left-radius: 44rpx; border-bottom-right-radius: 44rpx; background: #d9c8b8; }
.photo-swiper, .photo-wrap, .hero-photo { width: 100%; height: 860rpx; }
.hero-photo { display: block; }
.blurred { filter: blur(16rpx); transform: scale(1.05); }
.blur-mask { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 28rpx; background: rgba(63, 47, 42, 0.24); }
.photo-count { position: absolute; right: 28rpx; top: 32rpx; padding: 8rpx 18rpx; border-radius: 999rpx; color: #fff; background: rgba(63, 47, 42, .42); font-size: 24rpx; }
.photo-dots { position: absolute; left: 50%; bottom: 214rpx; transform: translateX(-50%); display: flex; align-items: center; gap: 10rpx; padding: 8rpx 14rpx; border-radius: 999rpx; background: rgba(63, 47, 42, .24); }
.photo-dot { width: 10rpx; height: 10rpx; border-radius: 999rpx; background: rgba(255, 255, 255, .56); transition: all .2s; }
.photo-dot.active { width: 28rpx; background: #fff; }
.hero-panel { position: absolute; left: 28rpx; right: 28rpx; bottom: 28rpx; display: flex; align-items: flex-end; justify-content: space-between; gap: 20rpx; padding: 28rpx; border-radius: 28rpx; background: rgba(255, 251, 244, .76); border: 1rpx solid rgba(255, 255, 255, .72); backdrop-filter: blur(18px) saturate(1.12); box-shadow: 0 16rpx 42rpx rgba(67, 45, 34, .16), inset 0 1rpx 0 rgba(255, 255, 255, .68); }
.name-row { display: flex; align-items: baseline; flex-wrap: wrap; gap: 22rpx; }
.name { display: block; font-size: 46rpx; font-weight: 800; color: #3b2a24; }
.display-id { color: #705b50; font-size: 24rpx; font-weight: 700; }
.meta { display: block; margin-top: 8rpx; font-size: 24rpx; color: #6e5a50; font-weight: 500; }
.hero-actions { flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 14rpx; }
.like-circle { width: 72rpx; height: 72rpx; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 50%; color: #c95d65; background: #fff3f2; border: 1rpx solid rgba(201, 93, 101, .22); font-size: 42rpx; line-height: 1; box-shadow: 0 10rpx 24rpx rgba(95, 70, 50, .1); }
.like-circle.active { color: #fff; background: #c95d65; border-color: #c95d65; }
.cert { flex-shrink: 0; padding: 10rpx 18rpx; border-radius: 999rpx; color: #6d7e60; background: #edf3e6; font-size: 22rpx; }
.self-tip, .heartbeat-card, .contact-card, .section, .empty-state, .hidden-state { margin: 24rpx; padding: 28rpx; border-radius: 28rpx; background: #fffaf3; box-shadow: 0 12rpx 32rpx rgba(95, 70, 50, .08); }
.self-tip { color: #7b6659; font-size: 26rpx; }
.heartbeat-card { background: linear-gradient(135deg, #fffaf3, #f5eadb); border: 1rpx solid #ead8c4; }
.heartbeat-head, .contact-card { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.heartbeat-title { font-size: 34rpx; font-weight: 700; color: #5a3b34; }
.heartbeat-score-value { color: #c85f64; font-weight: 700; }
.progress { height: 16rpx; margin: 18rpx 0 16rpx; border-radius: 999rpx; overflow: hidden; background: #eaded1; }
.progress-inner { height: 100%; border-radius: 999rpx; background: linear-gradient(90deg, #c95d65, #8ea078); }
.heartbeat-desc, .contact-desc { display: block; color: #8a776a; font-size: 25rpx; line-height: 1.7; }
.contact-title { display: block; font-size: 32rpx; font-weight: 700; color: #4a352f; }
.contact-action { color: #c95d65; font-weight: 700; }
.section-title { margin-bottom: 22rpx; font-size: 32rpx; font-weight: 700; color: #4a352f; }
.tag-grid { display: flex; flex-wrap: wrap; gap: 16rpx; }
.tag { padding: 12rpx 18rpx; border-radius: 999rpx; color: #5d4b42; background: #f2eadf; font-size: 24rpx; }
.info-list { margin-top: 18rpx; }
.info-row { display: flex; justify-content: space-between; padding: 16rpx 0; color: #7d6a5e; font-size: 26rpx; border-top: 1rpx solid #efe4d8; }
.ai-content { color: #5d4b42; font-size: 28rpx; line-height: 1.8; }
.bottom-bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 20; display: flex; gap: 18rpx; padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom)); background: rgba(255, 250, 243, .96); box-shadow: 0 -12rpx 28rpx rgba(74, 53, 47, .08); }
.bar-btn, .primary-btn { height: 92rpx; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 999rpx; font-size: 28rpx; line-height: 1; }
.bar-btn::after, .primary-btn::after, .like-circle::after { border: 0; }
.bar-btn { width: 160rpx; color: #5f4a3f; background: #eadfd2; border: 1rpx solid #d7c5b4; font-weight: 600; }
.bar-btn.active { color: #fff; background: #8ea078; border-color: #8ea078; }
.primary-btn { flex: 1; color: #fff; background: linear-gradient(135deg, #c95d65, #b9505b); font-weight: 700; box-shadow: 0 12rpx 28rpx rgba(201, 93, 101, .28); }
.empty-state, .hidden-state { margin-top: 160rpx; text-align: center; }
.empty-title, .hidden-title { display: block; font-size: 32rpx; font-weight: 700; }
.hidden-desc { display: block; margin-top: 16rpx; color: #8a776a; font-size: 26rpx; }
</style>
