<template>
	<view class="redirect-page">
		<text>正在打开活动详情...</text>
	</view>
</template>

<script>
export default {
	onLoad(options) {
		const query = options && options.id ? `?id=${options.id}` : ''
		uni.redirectTo({
			url: `/pages/activity/detail/index${query}`,
			fail: () => {
				uni.showToast({ title: '活动详情页打开失败', icon: 'none' })
			},
		})
	},
}
</script>

<style>
.redirect-page {
	align-items: center;
	background: #f7f4ef;
	box-sizing: border-box;
	color: #8d7f78;
	display: flex;
	font-size: 28rpx;
	justify-content: center;
	min-height: 100vh;
	padding: 40rpx;
}
</style>
