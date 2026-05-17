<template>
	<view class="page plaza-page">
		<view class="header">
			<view class="brand-row">
				<view class="brand">
					<text class="brand-mark">觅</text>
					<text>觅AI 真实用户广场</text>
				</view>
				<!-- <text class="sort-note">最新注册优先</text> -->
			</view>
			<text class="title">广场</text>
			<text class="desc">发现真实、认真相识的人</text>
		</view>

		<view class="search-card">
			<view class="search-box">
				<text class="search-prefix">ID</text>
				<input v-model.trim="searchNo" class="search-input" type="number" maxlength="7" placeholder="输入用户编号" confirm-type="search" @confirm="searchByNo" />
				<text v-if="searchNo" class="clear" @tap="clearSearch">清除</text>
			</view>
			<button class="search-btn" @tap="searchByNo">搜索</button>
		</view>

		<scroll-view class="quick-filters" scroll-x :show-scrollbar="false">
			<view class="quick-row">
				<view class="quick-chip" :class="{ active: filters.gender === '' }" @tap="setGender('')">{{ recommendLabel }}</view>
				<template v-if="!isRegistered">
					<view class="quick-chip" :class="{ active: filters.gender === '0' }" @tap="setGender('0')">男生</view>
					<view class="quick-chip" :class="{ active: filters.gender === '1' }" @tap="setGender('1')">女生</view>
				</template>
				<view class="quick-chip" :class="{ active: hasAdvancedFilters }" @tap="openFilter">筛选</view>
			</view>
		</scroll-view>

		<view class="state-panel">
			<text class="state-title">{{ stateTitle }}</text>
			<text class="state-desc">{{ stateDesc }}</text>
		</view>

		<view v-if="loading && !items.length" class="empty-state">
			<text class="empty-title">正在加载广场用户...</text>
			<text class="empty-desc">最新完成注册的用户会优先展示</text>
		</view>

		<view v-else-if="!items.length" class="empty-state">
			<text class="empty-title">{{ emptyTitle }}</text>
			<text class="empty-desc">{{ emptyDesc }}</text>
			<button v-if="hasAnyFilter" class="reset-btn" @tap="clearAllFilters">清空筛选</button>
		</view>

		<view v-else class="masonry">
			<view class="column">
				<view v-for="item in leftItems" :key="item.user_id" class="user-card" @tap="openProfile(item)">
					<image class="avatar" :src="item.avatar_url || '/static/logo.png'" mode="aspectFill" />
					<view class="card-content">
						<view class="card-top">
							<text class="nickname">{{ item.nickname || '觅AI用户' }}</text>
							<text class="cert">{{ item.certification_status || '未认证' }}</text>
						</view>
						<text class="display-no">ID {{ item.display_no }}</text>
						<view class="profile-line">
							<text>{{ ageText(item.age) }}</text>
							<text>{{ item.residence || '常驻地待补充' }}</text>
						</view>
						<view class="profile-line">
							<text>{{ heightText(item.height_cm) }}</text>
							<text>{{ item.occupation || '职业待补充' }}</text>
						</view>
						<view class="tag-row">
							<text class="info-tag">{{ optionLabel(item.annual_income, annualIncomeOptions) || '收入待补充' }}</text>
							<text class="info-tag">{{ optionLabel(item.education, educationOptions) || '学历待补充' }}</text>
						</view>
					</view>
				</view>
			</view>
			<view class="column">
				<view v-for="item in rightItems" :key="item.user_id" class="user-card" @tap="openProfile(item)">
					<image class="avatar" :src="item.avatar_url || '/static/logo.png'" mode="aspectFill" />
					<view class="card-content">
						<view class="card-top">
							<text class="nickname">{{ item.nickname || '觅AI用户' }}</text>
							<text class="cert">{{ item.certification_status || '未认证' }}</text>
						</view>
						<text class="display-no">ID {{ item.display_no }}</text>
						<view class="profile-line">
							<text>{{ ageText(item.age) }}</text>
							<text>{{ item.residence || '常驻地待补充' }}</text>
						</view>
						<view class="profile-line">
							<text>{{ heightText(item.height_cm) }}</text>
							<text>{{ item.occupation || '职业待补充' }}</text>
						</view>
						<view class="tag-row">
							<text class="info-tag">{{ optionLabel(item.annual_income, annualIncomeOptions) || '收入待补充' }}</text>
							<text class="info-tag">{{ optionLabel(item.education, educationOptions) || '学历待补充' }}</text>
						</view>
					</view>
				</view>
			</view>
		</view>

		<view v-if="items.length" class="load-more">
			<text>{{ loadingMore ? '加载更多...' : hasNext ? '上拉查看更多' : '已经到底了' }}</text>
		</view>

		<view v-if="filterOpen" class="filter-mask" @tap="closeFilter">
			<view class="filter-panel" @tap.stop>
				<view class="filter-head">
					<text class="filter-title">筛选</text>
					<text class="filter-close" @tap="closeFilter">关闭</text>
				</view>

				<view v-if="!isRegistered" class="filter-section">
					<text class="filter-label">性别</text>
					<view class="chips">
						<view v-for="item in genderOptions" :key="item.value" class="chip" :class="{ active: draft.gender === item.value }" @tap="draft.gender = item.value">{{ item.label }}</view>
					</view>
				</view>
				<view class="filter-section">
					<text class="filter-label">年龄</text>
					<view class="chips">
						<view v-for="item in ageOptions" :key="item.label" class="chip" :class="{ active: draft.ageKey === item.key }" @tap="selectRange('age', item)">{{ item.label }}</view>
					</view>
				</view>
				<view class="filter-section">
					<text class="filter-label">身高</text>
					<view class="chips">
						<view v-for="item in heightOptions" :key="item.label" class="chip" :class="{ active: draft.heightKey === item.key }" @tap="selectRange('height', item)">{{ item.label }}</view>
					</view>
				</view>
				<picker mode="region" @change="pickResidence">
					<view class="filter-row">
						<text class="filter-label">常驻地</text>
						<text class="filter-value">{{ draft.residence || '不限' }} ›</text>
					</view>
				</picker>
				<view class="filter-section">
					<text class="filter-label">学历</text>
					<view class="chips">
						<view v-for="item in educationOptions" :key="item.value" class="chip" :class="{ active: isDraftSelected('education', item.value) }" @tap="toggleDraft('education', item.value)">{{ item.label }}</view>
					</view>
				</view>
				<view class="filter-section">
					<text class="filter-label">婚况</text>
					<view class="chips">
						<view v-for="item in maritalStatusOptions" :key="item.value" class="chip" :class="{ active: isDraftSelected('marital_status', item.value) }" @tap="toggleDraft('marital_status', item.value)">{{ item.label }}</view>
					</view>
				</view>
				<view class="filter-section">
					<text class="filter-label">年收入</text>
					<view class="chips">
						<view v-for="item in annualIncomeOptions" :key="item.value" class="chip" :class="{ active: isDraftSelected('annual_income', item.value) }" @tap="toggleDraft('annual_income', item.value)">{{ item.label }}</view>
					</view>
				</view>
				<view class="filter-section">
					<text class="filter-label">房产信息</text>
					<view class="chips">
						<view v-for="item in houseStatusOptions" :key="item.value" class="chip" :class="{ active: isDraftSelected('house_status', item.value) }" @tap="toggleDraft('house_status', item.value)">{{ item.label }}</view>
					</view>
				</view>
				<view class="filter-section">
					<text class="filter-label">购车信息</text>
					<view class="chips">
						<view v-for="item in carStatusOptions" :key="item.value" class="chip" :class="{ active: isDraftSelected('car_status', item.value) }" @tap="toggleDraft('car_status', item.value)">{{ item.label }}</view>
					</view>
				</view>

				<view class="filter-actions">
					<button class="filter-btn" @tap="resetDraft">重置</button>
					<button class="filter-btn primary" @tap="applyFilter">查看结果</button>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { plazaList } from '../../api/mpPlaza.js'
import { ensureMpSession } from '../../utils/mpSession.js'

const defaultFilters = () => ({
	display_no: '',
	gender: '',
	age_min: '',
	age_max: '',
	ageKey: '',
	height_min: '',
	height_max: '',
	heightKey: '',
	residence: '',
	education: [],
	marital_status: [],
	annual_income: [],
	house_status: [],
	car_status: [],
})

export default {
	data() {
		return {
			loading: false,
			loadingMore: false,
			bootstrapping: false,
			bootstrapped: false,
			reloadTimer: null,
			items: [],
			pageNo: 1,
			pageSize: 20,
			total: 0,
			hasNext: false,
			searchNo: '',
			filterOpen: false,
			isRegistered: false,
			currentPerson: null,
			filters: defaultFilters(),
			draft: defaultFilters(),
			genderOptions: [
				{ label: '不限', value: '' },
				{ label: '男生', value: '0' },
				{ label: '女生', value: '1' },
			],
			ageOptions: [
				{ label: '不限', key: '', min: '', max: '' },
				{ label: '25岁以下', key: 'below_25', min: 18, max: 24 },
				{ label: '25-30岁', key: '25_30', min: 25, max: 30 },
				{ label: '31-35岁', key: '31_35', min: 31, max: 35 },
				{ label: '36-40岁', key: '36_40', min: 36, max: 40 },
				{ label: '40-50岁', key: '40_50', min: 40, max: 50 },
				{ label: '50岁以上', key: 'above_50', min: 51, max: '' },
			],
			heightOptions: [
				{ label: '不限', key: '', min: '', max: '' },
				{ label: '160以下', key: 'below_160', min: '', max: 159 },
				{ label: '160-170', key: '160_170', min: 160, max: 170 },
				{ label: '171-180', key: '171_180', min: 171, max: 180 },
				{ label: '180以上', key: 'above_180', min: 181, max: '' },
			],
			annualIncomeOptions: [
				{ label: '10万以下', value: 'below_100k' },
				{ label: '10-20万', value: '100k_200k' },
				{ label: '20-50万', value: '200k_500k' },
				{ label: '50万以上', value: 'above_500k' },
			],
			maritalStatusOptions: [
				{ label: '未婚', value: 'single' },
				{ label: '离异', value: 'divorced' },
				{ label: '丧偶', value: 'widowed' },
			],
			educationOptions: [
				{ label: '高中及以下', value: 'high_school_or_below' },
				{ label: '大专', value: 'college' },
				{ label: '本科', value: 'bachelor' },
				{ label: '硕士', value: 'master' },
				{ label: '博士及以上', value: 'doctor_or_above' },
			],
			houseStatusOptions: [
				{ label: '无房', value: 'none' },
				{ label: '有房无贷', value: 'owned' },
				{ label: '有房有贷', value: 'mortgage' },
				{ label: '与父母同住', value: 'family' },
			],
			carStatusOptions: [
				{ label: '无车', value: 'none' },
				{ label: '有车无贷', value: 'owned' },
				{ label: '有车有贷', value: 'loan' },
			],
		}
	},
	computed: {
		recommendLabel() {
			return this.isRegistered ? '异性推荐' : '智能推荐'
		},
		leftItems() {
			return this.items.filter((_, index) => index % 2 === 0)
		},
		rightItems() {
			return this.items.filter((_, index) => index % 2 === 1)
		},
		hasAdvancedFilters() {
			return Boolean(
				this.filters.ageKey || this.filters.heightKey || this.filters.residence ||
				this.hasSelected('education') || this.hasSelected('marital_status') || this.hasSelected('annual_income') ||
				this.hasSelected('house_status') || this.hasSelected('car_status')
			)
		},
		hasAnyFilter() {
			return Boolean(this.filters.display_no || this.filters.gender || this.hasAdvancedFilters)
		},
		stateTitle() {
			if (this.loading && !this.items.length) return '正在同步最新用户'
			if (this.filters.display_no) return `编号 ${this.filters.display_no} 的搜索结果`
			return `共 ${this.total} 位用户 · 最新注册优先`
		},
		stateDesc() {
			if (this.hasAnyFilter) return '当前保留筛选条件，可清空后查看全部广场用户。'
			if (this.isRegistered) return '已根据你的注册资料默认展示异性用户。'
			return '仅展示已完成小程序注册且未隐身的用户资料摘要。'
		},
		emptyTitle() {
			return this.filters.display_no ? '未找到该编号用户' : '暂无匹配用户'
		},
		emptyDesc() {
			return this.filters.display_no ? '请检查 7 位用户编号是否正确' : '可以调整筛选条件后再看看'
		},
	},
	onShow() {
		this.bootstrap()
	},
	onUnload() {
		if (this.reloadTimer) {
			clearTimeout(this.reloadTimer)
			this.reloadTimer = null
		}
	},
	onReachBottom() {
		this.loadMore()
	},
	onPullDownRefresh() {
		this.fetchList(true).finally(() => {
			uni.stopPullDownRefresh()
		})
	},
	onShareAppMessage() {
		return {
			title: '觅AI真实用户广场｜遇见认真相识的人',
			path: '/pages/plaza/index',
			imageUrl: this.shareImage(),
		}
	},
	onShareTimeline() {
		return {
			title: '觅AI真实用户广场｜让相识回到真实与慎重',
			query: '',
			imageUrl: this.shareImage(),
		}
	},
	methods: {
		shareImage() {
			const first = this.items.find((item) => item && item.avatar_url)
			return first ? first.avatar_url : undefined
		},
		async bootstrap() {
			if (this.bootstrapping) return
			this.bootstrapping = true
			try {
				const session = await ensureMpSession()
				this.currentPerson = session && session.person ? session.person : null
				this.isRegistered = Boolean(this.currentPerson)
				if (this.isRegistered && this.filters.gender) {
					this.filters.gender = ''
					this.draft.gender = ''
				}
			} catch (error) {
				this.currentPerson = null
				this.isRegistered = false
			} finally {
				this.bootstrapping = false
				if (!this.bootstrapped) {
					this.bootstrapped = true
					this.reload()
				}
			}
		},
		queryParams() {
			const params = {
				page_no: this.pageNo,
				page_size: this.pageSize,
			}
			Object.keys(this.filters).forEach((key) => {
				if (key.endsWith('Key')) return
				if (this.isRegistered && key === 'gender') return
				const value = this.filters[key]
				if (Array.isArray(value)) {
					if (value.length) params[key] = value.join(',')
					return
				}
				if (value !== '' && value !== null && value !== undefined) {
					params[key] = value
				}
			})
			return params
		},
		async fetchList(reset = false) {
			if (reset) {
				this.pageNo = 1
				this.hasNext = false
			}
			if (this.loading || this.loadingMore) return
			if (this.pageNo === 1) this.loading = true
			else this.loadingMore = true
			try {
				const data = await plazaList(this.queryParams())
				const list = data.items || []
				this.items = this.pageNo === 1 ? list : this.items.concat(list)
				this.total = data.total || 0
				this.hasNext = Boolean(data.has_next)
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			} finally {
				this.loading = false
				this.loadingMore = false
			}
		},
		reload() {
			if (this.reloadTimer) clearTimeout(this.reloadTimer)
			this.reloadTimer = setTimeout(() => {
				this.reloadTimer = null
				this.fetchList(true)
			}, 220)
		},
		loadMore() {
			if (!this.hasNext || this.loading || this.loadingMore) return
			this.pageNo += 1
			this.fetchList()
		},
		searchByNo() {
			const text = String(this.searchNo || '').trim()
			if (text && !/^[1-9]\d{6}$/.test(text)) {
				uni.showToast({ title: '请输入7位用户编号', icon: 'none' })
				return
			}
			this.filters.display_no = text
			this.reload()
		},
		clearSearch() {
			this.searchNo = ''
			this.filters.display_no = ''
			this.reload()
		},
		setGender(value) {
			if (this.isRegistered && value) {
				uni.showToast({ title: '已按你的性别自动推荐异性', icon: 'none' })
				return
			}
			this.filters.gender = value
			this.reload()
		},
		openFilter() {
			this.draft = this.cloneFilters(this.filters)
			this.filterOpen = true
		},
		closeFilter() {
			this.filterOpen = false
		},
		selectRange(type, item) {
			if (type === 'age') {
				this.draft.ageKey = item.key
				this.draft.age_min = item.min
				this.draft.age_max = item.max
			} else {
				this.draft.heightKey = item.key
				this.draft.height_min = item.min
				this.draft.height_max = item.max
			}
		},
		pickResidence(event) {
			this.draft.residence = (event.detail.value || []).filter(Boolean).join(' ')
		},
		cloneFilters(filters) {
			const cloned = { ...filters }
			;['education', 'marital_status', 'annual_income', 'house_status', 'car_status'].forEach((key) => {
				cloned[key] = Array.isArray(filters[key]) ? [...filters[key]] : []
			})
			return cloned
		},
		hasSelected(key) {
			const value = this.filters[key]
			return Array.isArray(value) && value.length > 0
		},
		isDraftSelected(key, value) {
			return Array.isArray(this.draft[key]) && this.draft[key].includes(value)
		},
		toggleDraft(key, value) {
			const selected = Array.isArray(this.draft[key]) ? [...this.draft[key]] : []
			const index = selected.indexOf(value)
			if (index >= 0) selected.splice(index, 1)
			else selected.push(value)
			this.draft[key] = selected
		},
		resetDraft() {
			this.draft = defaultFilters()
			this.draft.display_no = this.filters.display_no
			if (this.isRegistered) this.draft.gender = ''
		},
		applyFilter() {
			this.filters = this.cloneFilters({ ...this.draft, display_no: this.filters.display_no })
			if (this.isRegistered) this.filters.gender = ''
			this.filterOpen = false
			this.reload()
		},
		clearAllFilters() {
			this.searchNo = ''
			this.filters = defaultFilters()
			this.reload()
		},
		openProfile(item) {
			if (!item || !item.display_no) return
			uni.navigateTo({ url: `/pages/plaza/detail/index?display_no=${item.display_no}` })
		},
		ageText(age) {
			return age ? `${age}岁` : '年龄待补充'
		},
		heightText(height) {
			return height ? `${height}cm` : '身高待补充'
		},
		optionLabel(value, options) {
			const item = options.find((option) => option.value === value)
			return item ? item.label : ''
		},
	},
}
</script>

<style>
.plaza-page {
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
.search-card,
.search-box,
.quick-row,
.card-top,
.profile-line,
.filter-head,
.filter-row,
.filter-actions {
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
.sort-note {
	color: #8d6b5c;
	font-size: 24rpx;
	font-weight: 650;
}
.title,
.desc,
.state-title,
.state-desc,
.empty-title,
.empty-desc,
.nickname,
.display-no,
.filter-label {
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
.search-card {
	gap: 16rpx;
	margin-bottom: 22rpx;
}
.search-box {
	flex: 1;
	height: 84rpx;
	border: 1rpx solid #eadfd6;
	border-radius: 999rpx;
	background: rgba(255, 255, 255, 0.82);
	padding: 0 24rpx;
	box-sizing: border-box;
}
.search-prefix {
	color: #5c8f68;
	font-size: 24rpx;
	font-weight: 850;
	margin-right: 14rpx;
}
.search-input {
	flex: 1;
	color: #2f2723;
	font-size: 28rpx;
}
.clear {
	color: #9a8b83;
	font-size: 24rpx;
}
.search-btn {
	width: 136rpx;
	height: 84rpx;
	margin: 0;
	border-radius: 999rpx;
	border: 0;
	background: #5c8f68;
	color: #ffffff;
	font-size: 28rpx;
	font-weight: 800;
	line-height: 84rpx;
}
.quick-filters {
	width: 100%;
	white-space: nowrap;
	margin-bottom: 24rpx;
}
.quick-row {
	gap: 16rpx;
}
.quick-chip,
.chip {
	flex: 0 0 auto;
	border: 1rpx solid #e4d9cf;
	border-radius: 999rpx;
	color: #7c716a;
	background: rgba(255, 255, 255, 0.76);
	font-size: 26rpx;
	font-weight: 650;
}
.quick-chip {
	padding: 16rpx 26rpx;
}
.quick-chip.active,
.chip.active {
	color: #ffffff;
	border-color: #5c8f68;
	background: #5c8f68;
}
.state-panel {
	margin-bottom: 28rpx;
	padding: 24rpx;
	border: 1rpx dashed #d8b7a5;
	border-radius: 28rpx;
	background: #fbf1eb;
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
	margin-top: 96rpx;
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
	width: 240rpx;
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
.masonry {
	display: flex;
	gap: 20rpx;
	align-items: flex-start;
}
.column {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 20rpx;
	min-width: 0;
}
.user-card {
	overflow: hidden;
	border: 1rpx solid #eadfd6;
	border-radius: 28rpx;
	background: #fffdfa;
	box-shadow: 0 14rpx 34rpx rgba(69, 48, 38, 0.08);
}
.avatar {
	width: 100%;
	height: 330rpx;
	background: #e5dbd1;
}
.card-content {
	padding: 20rpx;
}
.card-top {
	justify-content: space-between;
	gap: 12rpx;
}
.nickname {
	flex: 1;
	min-width: 0;
	color: #2f2723;
	font-size: 30rpx;
	font-weight: 850;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cert {
	flex: 0 0 auto;
	border-radius: 999rpx;
	padding: 6rpx 12rpx;
	color: #4e865e;
	background: #eef5ec;
	font-size: 20rpx;
	font-weight: 800;
}
.display-no {
	margin-top: 8rpx;
	color: #9a6a58;
	font-size: 22rpx;
	font-weight: 750;
}
.profile-line {
	gap: 10rpx;
	margin-top: 10rpx;
	color: #6f625b;
	font-size: 23rpx;
	line-height: 1.35;
}
.profile-line text {
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.tag-row {
	display: flex;
	flex-wrap: wrap;
	gap: 8rpx;
	margin-top: 14rpx;
}
.info-tag {
	max-width: 100%;
	border-radius: 999rpx;
	padding: 6rpx 12rpx;
	background: #f7eee7;
	color: #8d6b5c;
	font-size: 21rpx;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.load-more {
	padding: 28rpx 0 0;
	color: #9a8b83;
	font-size: 24rpx;
	text-align: center;
}
.filter-mask {
	position: fixed;
	inset: 0;
	z-index: 30;
	background: rgba(47, 39, 35, 0.32);
	display: flex;
	align-items: flex-end;
}
.filter-panel {
	width: 100%;
	max-height: 82vh;
	overflow-y: auto;
	border-radius: 36rpx 36rpx 0 0;
	background: #fffdfa;
	padding: 30rpx 28rpx 48rpx;
	box-sizing: border-box;
}
.filter-head {
	justify-content: space-between;
	margin-bottom: 24rpx;
}
.filter-title {
	color: #2f2723;
	font-size: 34rpx;
	font-weight: 850;
}
.filter-close {
	color: #8d6b5c;
	font-size: 26rpx;
}
.filter-section {
	margin-top: 24rpx;
}
.filter-label {
	color: #2f2723;
	font-size: 26rpx;
	font-weight: 750;
}
.chips {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
	margin-top: 14rpx;
}
.chip {
	padding: 14rpx 22rpx;
}
.filter-row {
	justify-content: space-between;
	min-height: 88rpx;
	margin-top: 20rpx;
	border-bottom: 1rpx solid #f0e5dc;
}
.filter-value {
	color: #7c716a;
	font-size: 26rpx;
}
.filter-actions {
	position: sticky;
	bottom: 0;
	gap: 18rpx;
	margin-top: 32rpx;
	padding-top: 18rpx;
	background: #fffdfa;
}
.filter-btn {
	flex: 1;
	height: 84rpx;
	margin: 0;
	border: 1rpx solid #eadfd6;
	border-radius: 999rpx;
	background: #fffdfa;
	color: #2f2723;
	font-size: 28rpx;
	font-weight: 800;
	line-height: 84rpx;
}
.filter-btn.primary {
	border-color: #5c8f68;
	background: #5c8f68;
	color: #ffffff;
}
.search-btn::after,
.reset-btn::after,
.filter-btn::after {
	border: 0;
}
</style>
