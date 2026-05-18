<template>
	<view class="page relations-page">
		<view class="tabs">
			<view v-for="item in tabs" :key="item.value" class="tab" :class="{ active: activeTab === item.value }" @tap="switchTab(item.value)">{{ item.label }}</view>
		</view>

		<view v-if="loading && !items.length" class="empty-state">
			<text class="empty-title">正在加载...</text>
			<text class="empty-desc">你的互动关系会在这里汇总</text>
		</view>

		<view v-else-if="!items.length" class="empty-state">
			<text class="empty-title">{{ emptyTitle }}</text>
			<text class="empty-desc">{{ emptyDesc }}</text>
			<button class="reset-btn" @tap="goPlaza">去广场看看</button>
		</view>

		<view v-else class="list">
			<view v-for="item in items" :key="item.user_id" class="person-card" @tap="openProfile(item)">
				<image class="avatar" :src="thumb(item.avatar_url, 180, 180) || '/static/logo.png'" mode="aspectFill" />
				<view class="body">
					<view class="top">
						<text class="name">{{ item.nickname || '觅AI用户' }}</text>
						<text class="cert">{{ item.certification_status || '未认证' }}</text>
					</view>
					<text class="meta">ID {{ item.display_no }} · {{ ageText(item.age) }} · {{ item.residence || '常驻地待补充' }}</text>
					<text class="meta">{{ heightText(item.height_cm) }} · {{ item.occupation || '职业待补充' }}</text>
				</view>
				<text class="arrow">›</text>
			</view>
		</view>

		<view v-if="items.length" class="load-more">{{ hasNext ? '上拉查看更多' : '已经到底了' }}</view>
	</view>
</template>

<script>
import { mineFavorites, mineLikes } from '../../api/mpProfile.js'
import { ensureRegisteredSession } from '../../utils/mpSession.js'
import { ossImage } from '../../utils/ossImage.js'

export default {
	data() {
		return {
			activeTab: 'received',
			tabs: [
				{ label: '喜欢我的', value: 'received' },
				{ label: '我喜欢的', value: 'sent' },
				{ label: '我的收藏', value: 'favorites' },
			],
			items: [],
			pageNo: 1,
			pageSize: 20,
			hasNext: false,
			loading: false,
		}
	},
	computed: {
		emptyTitle() {
			return ({ received: '还没有人喜欢你', sent: '你还没有喜欢的人', favorites: '你还没有收藏资料' }[this.activeTab]) || '暂无数据'
		},
		emptyDesc() {
			return this.activeTab === 'received' ? '完善资料和认证后，会更容易被认真了解。' : '遇到合适的人，可以先喜欢或收藏。'
		},
	},
	onLoad(query) {
		if (query && query.tab) this.activeTab = query.tab
	},
	onShow() {
		this.reload()
	},
	onPullDownRefresh() {
		this.reload().finally(() => uni.stopPullDownRefresh())
	},
	onReachBottom() {
		if (this.hasNext && !this.loading) this.load(false)
	},
	methods: {
		thumb(url, width, height) {
			return ossImage(url, { width, height })
		},
		switchTab(tab) {
			if (this.activeTab === tab) return
			this.activeTab = tab
			this.reload()
		},
		async reload() {
			this.pageNo = 1
			this.items = []
			await this.load(true)
		},
		async load(reset) {
			this.loading = true
			try {
				await ensureRegisteredSession()
				const params = { page_no: this.pageNo, page_size: this.pageSize }
				const data = this.activeTab === 'favorites' ? await mineFavorites(params) : await mineLikes({ ...params, type: this.activeTab })
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
		openProfile(item) {
			if (!item.display_no) return
			uni.navigateTo({ url: `/pages/plaza/detail/index?display_no=${item.display_no}` })
		},
		goPlaza() {
			uni.switchTab({ url: '/pages/plaza/index' })
		},
		ageText(age) {
			return age ? `${age}岁` : '年龄待补充'
		},
		heightText(height) {
			return height ? `${height}cm` : '身高待补充'
		},
	},
}
</script>

<style>
.relations-page { min-height: 100vh; background: #f7f4ef; padding: 24rpx; box-sizing: border-box; }
.tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12rpx; background: #fffaf3; border-radius: 999rpx; padding: 10rpx; margin-bottom: 24rpx; box-shadow: 0 8rpx 24rpx rgba(95,70,50,.06); }
.tab { height: 64rpx; line-height: 64rpx; text-align: center; border-radius: 999rpx; color: #8d7f78; font-size: 26rpx; font-weight: 800; }
.tab.active { background: #c95d65; color: #fff; }
.person-card, .empty-state { background: #fffaf3; border-radius: 28rpx; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); padding: 24rpx; margin-bottom: 18rpx; }
.person-card { display: flex; align-items: center; }
.avatar { width: 120rpx; height: 120rpx; border-radius: 24rpx; background: #eadbd0; flex-shrink: 0; }
.body { flex: 1; min-width: 0; margin-left: 20rpx; }
.top { display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap; }
.name { color: #4b342d; font-size: 30rpx; font-weight: 900; }
.cert { border-radius: 999rpx; background: #eef5ec; color: #4e865e; font-size: 21rpx; font-weight: 800; padding: 6rpx 12rpx; }
.meta { display: block; color: #8d7f78; font-size: 24rpx; margin-top: 8rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.arrow { color: #c95d65; font-size: 44rpx; }
.empty-title, .empty-desc { display: block; }
.empty-title { color: #4b342d; font-size: 34rpx; font-weight: 900; }
.empty-desc { color: #8d7f78; font-size: 26rpx; line-height: 1.6; margin-top: 12rpx; }
.reset-btn { margin-top: 26rpx; height: 76rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 28rpx; }
.load-more { text-align: center; color: #9a8a7f; font-size: 24rpx; padding: 24rpx 0; }
</style>
