<template>
	<view class="page unlocks-page">
		<view class="header-card">
			<text class="title">联系方式解锁记录</text>
			<text class="desc">这里只展示已解锁对象，手机号进入详情后继续查看。</text>
		</view>

		<view v-if="loading && !items.length" class="empty-state"><text class="empty-title">正在加载...</text></view>
		<view v-else-if="!items.length" class="empty-state">
			<text class="empty-title">还没有解锁记录</text>
			<text class="empty-desc">遇到合适的人，可以通过互动任务、解锁券或付费查看联系方式。</text>
			<button class="reset-btn" @tap="goPlaza">去广场看看</button>
		</view>

		<view v-else>
			<view v-for="item in items" :key="item.unlock_id" class="unlock-card" @tap="openProfile(item)">
				<image class="avatar" :src="thumb(item.avatar_url, 180, 180) || '/static/logo.png'" mode="aspectFill" />
				<view class="body">
					<view class="top"><text class="name">{{ item.nickname || '觅AI用户' }}</text><text class="source">{{ sourceLabel(item.unlock_source) }}</text></view>
					<text class="meta">ID {{ item.display_no }} · {{ item.residence || '常驻地待补充' }}</text>
					<text class="meta">{{ timeText(item.unlocked_at) }} 解锁</text>
				</view>
				<button class="contact-btn" @tap.stop="goContact(item)">查看</button>
			</view>
		</view>
	</view>
</template>

<script>
import { mineUnlocks } from '../../api/mpProfile.js'
import { ensureRegisteredSession } from '../../utils/mpSession.js'
import { ossImage } from '../../utils/ossImage.js'

export default {
	data() {
		return { items: [], pageNo: 1, pageSize: 20, hasNext: false, loading: false }
	},
	onShow() { this.reload() },
	onPullDownRefresh() { this.reload().finally(() => uni.stopPullDownRefresh()) },
	onReachBottom() { if (this.hasNext && !this.loading) this.load(false) },
	methods: {
		thumb(url, width, height) { return ossImage(url, { width, height }) },
		async reload() { this.pageNo = 1; this.items = []; await this.load(true) },
		async load(reset) {
			this.loading = true
			try {
				await ensureRegisteredSession()
				const data = await mineUnlocks({ page_no: this.pageNo, page_size: this.pageSize })
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
		sourceLabel(source) {
			return ({ free_coupon: '解锁券', task_free: '互动解锁', paid_boost: '付费解锁' }[source]) || '已解锁'
		},
		timeText(value) {
			if (!value) return ''
			return String(value).replace('T', ' ').slice(0, 16)
		},
		openProfile(item) {
			uni.navigateTo({ url: `/pages/plaza/detail/index?display_no=${item.display_no}` })
		},
		goContact(item) {
			uni.navigateTo({ url: `/pages/plaza/unlock/contact?display_no=${item.display_no}` })
		},
		goPlaza() {
			uni.switchTab({ url: '/pages/plaza/index' })
		},
	},
}
</script>

<style>
.unlocks-page { min-height: 100vh; background: #f7f4ef; padding: 24rpx; box-sizing: border-box; }
.header-card, .unlock-card, .empty-state { background: #fffaf3; border-radius: 28rpx; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); padding: 26rpx; margin-bottom: 18rpx; }
.title, .desc, .empty-title, .empty-desc, .meta { display: block; }
.title { color: #3f2d28; font-size: 38rpx; font-weight: 900; }
.desc, .empty-desc, .meta { color: #8d7f78; font-size: 25rpx; line-height: 1.6; margin-top: 8rpx; }
.unlock-card { display: flex; align-items: center; gap: 20rpx; }
.avatar { width: 116rpx; height: 116rpx; border-radius: 24rpx; background: #eadbd0; flex-shrink: 0; }
.body { flex: 1; min-width: 0; }
.top { display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap; }
.name { color: #4b342d; font-size: 30rpx; font-weight: 900; }
.source { border-radius: 999rpx; background: #f6e6dc; color: #b85c67; font-size: 21rpx; font-weight: 800; padding: 6rpx 12rpx; }
.contact-btn { width: 104rpx; height: 60rpx; line-height: 60rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 24rpx; margin: 0; }
.empty-title { color: #4b342d; font-size: 34rpx; font-weight: 900; }
.reset-btn { margin-top: 24rpx; height: 76rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 28rpx; }
</style>
