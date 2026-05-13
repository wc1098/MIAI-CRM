<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/*每个页面公共css */
	page {
		background: #f7f4ef;
		color: #3d3532;
		font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
	}

	.page {
		min-height: 100vh;
		box-sizing: border-box;
		padding: 28rpx;
	}

	.card {
		background: #fff;
		border-radius: 20rpx;
		box-shadow: 0 10rpx 30rpx rgba(90, 54, 45, 0.08);
		box-sizing: border-box;
		padding: 28rpx;
	}

	.primary-btn {
		background: #c15b65;
		border-radius: 999rpx;
		color: #fff;
		font-size: 30rpx;
		line-height: 88rpx;
	}

	.secondary-btn {
		background: #f3e6e1;
		border-radius: 999rpx;
		color: #8c3f48;
		font-size: 30rpx;
		line-height: 88rpx;
	}
</style>
