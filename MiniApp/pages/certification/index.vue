<template>
	<view class="page cert-page">
		<view class="top-card">
			<view class="brand-row">
				<view class="brand">
					<text class="brand-mark">认</text>
					<text>觅AI 认证中心</text>
				</view>
				<text class="level-pill">{{ currentLevelName }}</text>
			</view>
			<text class="headline">{{ currentApplication ? currentApplication.level_name : '真实认证，让靠谱的人更快看见你' }}</text>
			<text class="subhead">{{ topDescription }}</text>
			<view v-if="currentApplication" class="progress-wrap">
				<view class="progress"><view class="progress-bar" :style="progressStyle"></view></view>
				<text class="progress-text">{{ progress.approved }}/{{ progress.total }} 项已通过</text>
			</view>
		</view>

		<view v-if="!currentApplication" class="panel">
			<view class="section-head loose">
				<view>
					<text class="section-title">认证是你的真实资料背书</text>
					<text class="section-desc">平台会核验实名、照片和关键资料，通过后展示认证等级，让对方更放心，也让你的资料更容易被认真了解。</text>
				</view>
			</view>

			<view
				v-for="pkg in packages"
				:key="pkg.id"
				class="package-card"
				:class="{ selected: selectedPackageId === pkg.id }"
				@tap="selectedPackageId = pkg.id"
			>
				<view class="package-head">
					<view>
						<text class="package-title">{{ pkg.level_name }}</text>
						<text class="package-desc">完成后点亮对应认证等级，购买后逐项补齐资料。</text>
					</view>
					<view class="price-box">
						<text class="price">¥{{ normalizePrice(pkg.price) }}</text>
						<text class="price-tip">{{ normalizePrice(pkg.price) === '0' ? '免费开启' : '全价购买' }}</text>
					</view>
				</view>

				<view class="block-title-row">
					<text class="block-title">认证项目</text>
					<text class="block-count">{{ (pkg.item_codes || []).length }} 项</text>
				</view>
				<view class="item-chips">
					<text v-for="code in pkg.item_codes || []" :key="code" class="item-chip">{{ itemName(code) }}</text>
				</view>

				<view class="benefit-box">
					<text class="block-title">认证权益</text>
					<text class="benefit-text">{{ packageBenefit(pkg) }}</text>
				</view>

				<view class="rights">
					<view class="right-item">
						<text class="right-value">{{ pkg.reward_coupon_count || 0 }}张</text>
						<text class="right-label">联系方式解锁券</text>
					</view>
					<view class="right-item">
						<text class="right-value">{{ pkg.reward_coupon_valid_days || 0 }}天</text>
						<text class="right-label">券有效期</text>
					</view>
					<view class="right-item">
						<text class="right-value">等级标识</text>
						<text class="right-label">广场/详情展示</text>
					</view>
				</view>
			</view>

			<view v-if="selectedPackage" class="buy-bar">
				<view>
					<text class="buy-title">{{ selectedPackage.level_name }}</text>
					<text class="buy-desc">¥{{ normalizePrice(selectedPackage.price) }} · {{ selectedPackage.item_codes.length }} 项认证</text>
				</view>
				<button class="primary-btn buy-btn" :loading="payingId === selectedPackage.id" @tap="buyPackage(selectedPackage)">
					{{ normalizePrice(selectedPackage.price) === '0' ? '立即开启' : '购买认证' }}
				</button>
			</view>
		</view>

		<view v-else class="panel">
			<view class="application-card">
				<view class="section-head">
					<view>
						<text class="section-title">{{ currentApplication.level_name }}</text>
						<text class="section-desc">订单号：{{ currentApplication.order_id || '-' }}</text>
					</view>
					<text class="status">{{ appStatusLabel(currentApplication.application_status) }}</text>
				</view>
				<button
					v-if="currentApplication.application_status === 'pending_payment' && currentApplication.order_id"
					class="primary-btn single"
					:loading="submitting"
					@tap="continuePay(currentApplication.order_id)"
				>
					继续支付
				</button>
			</view>

			<view class="task-card">
				<view class="section-head loose">
					<view>
						<text class="section-title">待补齐资料</text>
						<text class="section-desc">{{ pendingRecords.length ? '按项完成后，总部会统一审核人工项。' : '该档认证资料已补齐，请等待结果同步。' }}</text>
					</view>
					<text class="section-note">{{ pendingRecords.length }} 项待处理</text>
				</view>

				<view v-if="!pendingRecords.length" class="done-box">
					<text class="done-title">资料已补齐</text>
					<text class="done-desc">自动项已完成，人工项通过后会自动升级认证等级并发放解锁券。</text>
				</view>

				<view v-for="record in pendingRecords" :key="record.id" class="record-card">
					<view class="record-top">
						<view>
							<text class="record-title">{{ record.item_name }}</text>
							<text class="record-desc">{{ recordHint(record) }}</text>
							<text v-if="record.reject_reason" class="record-reason">{{ record.reject_reason }}</text>
						</view>
						<text class="record-status" :class="record.record_status">{{ recordStatusLabel(record.record_status) }}</text>
					</view>

					<view v-if="record.item_code === 'real_name' && canSubmit(record)" class="form-block">
						<input v-model.trim="realName.name" class="input" placeholder="姓名" />
						<input
							v-model.trim="realName.id_card_no"
							class="input"
							placeholder="身份证号"
							maxlength="18"
							@input="onIdCardInput"
						/>
						<text v-if="realNameLimit.message" class="limit-tip">{{ realNameLimit.message }}</text>
						<button class="primary-btn single" :loading="submitting" :disabled="realNameLimit.cooling" @tap="submitRealNameForm">提交实名认证</button>
					</view>

					<view v-else-if="record.item_code === 'real_photo' && canSubmit(record)" class="reuse-photo">
						<text class="reuse-title">真人照片使用注册时上传的真实照片</text>
						<text class="reuse-desc">如果这里仍未通过，说明当前账号没有可复用的合格注册照片，请返回注册资料重新上传清晰本人正脸照或联系工作人员处理。</text>
					</view>

					<view v-else-if="isManual(record) && canSubmit(record)" class="manual-panel">
						<view class="upload-row">
							<button class="secondary-btn" :loading="uploadingCode === record.item_code" @tap="chooseAndUpload(record)">上传证明材料</button>
							<button class="primary-btn" :loading="submittingCode === record.item_code" @tap="submitManual(record)">提交审核</button>
						</view>
						<textarea
							:value="manualRemarks[record.item_code] || ''"
							class="textarea"
							placeholder="可填写补充说明，选填"
							maxlength="200"
							@input="setManualRemark(record.item_code, $event)"
						/>
					</view>

					<scroll-view v-if="record.materials && record.materials.length" class="materials" scroll-x>
						<image
							v-for="material in record.materials"
							:key="material.id"
							class="material-img"
							:src="thumb(material.file_url, 180, 180)"
							mode="aspectFill"
							@tap="preview(record.materials, material.file_url)"
						/>
					</scroll-view>
				</view>
			</view>

			<view v-if="approvedRecords.length" class="approved-card">
				<view class="section-head">
					<text class="section-title">已完成项目</text>
					<text class="section-note">{{ approvedRecords.length }} 项</text>
				</view>
				<view class="done-chips">
					<text v-for="record in approvedRecords" :key="record.id" class="done-chip">{{ record.item_name }}</text>
				</view>
			</view>
		</view>

		<view v-if="!loading && !packages.length" class="empty-card">
			<text class="empty-title">暂无可用认证套餐</text>
			<text class="empty-desc">请稍后再试或联系门店工作人员。</text>
		</view>
	</view>
</template>

<script>
import {
	certificationCenter,
	continueCertificationPay,
	createCertificationOrder,
	submitManualCertification,
	submitRealName,
	uploadCertificationMaterial,
} from '../../api/mpCertification.js'
import { ensureRegisteredSession } from '../../utils/mpSession.js'
import { getPerson } from '../../utils/storage.js'
import { ossImage, ossImageList } from '../../utils/ossImage.js'

export default {
	data() {
		return {
			loading: false,
			submitting: false,
			payingId: 0,
			uploadingCode: '',
			submittingCode: '',
			selectedPackageId: 0,
			center: {},
			manualRemarks: {},
			realName: {
				name: '',
				id_card_no: '',
			},
		}
	},
	computed: {
		packages() {
			return this.center.packages || []
		},
		currentApplication() {
			return this.center.current_application || null
		},
		records() {
			return this.currentApplication && this.currentApplication.records ? this.currentApplication.records : []
		},
		itemMap() {
			const map = {}
			;(this.center.items || []).forEach((item) => {
				map[item.item_code] = item
			})
			return map
		},
		currentLevelName() {
			return this.center.current_level_name || '未认证'
		},
		topDescription() {
			if (!this.currentApplication) return '你可以按自己的资料完整度选择认证等级。购买后再逐项补齐材料，审核通过后点亮标识并发放对应权益。'
			if (this.pendingRecords.length) return '你已购买该档认证，继续补齐下方资料即可推进审核。'
			return '当前档位资料已补齐，系统会在通过后点亮等级并发放权益。'
		},
		pendingRecords() {
			return this.records.filter((item) => ['not_submitted', 'rejected'].includes(item.record_status))
		},
		approvedRecords() {
			return this.records.filter((item) => item.record_status === 'approved')
		},
		selectedPackage() {
			return this.packages.find((item) => item.id === this.selectedPackageId) || this.packages[0] || null
		},
		progress() {
			const raw = this.currentApplication && this.currentApplication.progress
			if (raw) return raw
			const total = this.records.length
			const approved = this.approvedRecords.length
			return { total, approved, percent: total ? Math.round((approved / total) * 100) : 0 }
		},
		progressStyle() {
			return `width: ${this.progress.percent || 0}%`
		},
		realNameLimit() {
			return (this.center.limits && this.center.limits.real_name) || {}
		},
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		thumb(url, width = 300, height = 300) {
			return ossImage(url, { width, height })
		},
		async load() {
			this.loading = true
			try {
				await ensureRegisteredSession()
				const data = await certificationCenter()
				this.center = data || {}
				const person = getPerson() || {}
				this.realName.name = this.realName.name || person.name || ''
				if (!this.selectedPackageId && this.packages.length) this.selectedPackageId = this.packages[0].id
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		itemName(code) {
			return this.itemMap[code] ? this.itemMap[code].item_name : code
		},
		normalizePrice(price) {
			const value = Number(price || 0)
			return value ? value.toFixed(2) : '0'
		},
		packageBenefit(pkg) {
			return pkg.benefit_desc || '展示认证等级标识，增强资料可信度；认证通过后发放联系方式解锁券。'
		},
		canSubmit(record) {
			return ['not_submitted', 'rejected'].includes(record.record_status)
		},
		isManual(record) {
			return record.verify_mode === 'manual'
		},
		recordHint(record) {
			if (record.item_code === 'real_name') return '姓名默认使用注册姓名，可在这里修改后做三要素核验。'
			if (record.item_code === 'real_photo') return '复用注册时已通过人脸检测的真人照片。'
			return this.itemMap[record.item_code] && this.itemMap[record.item_code].material_desc ? this.itemMap[record.item_code].material_desc : '上传材料后提交总部审核。'
		},
		setManualRemark(code, event) {
			this.manualRemarks = {
				...this.manualRemarks,
				[code]: (event.detail && event.detail.value) || '',
			}
		},
		async buyPackage(pkg) {
			this.selectedPackageId = pkg.id
			this.payingId = pkg.id
			try {
				const result = await createCertificationOrder(pkg.id)
				const pay = result.payment || {}
				if (pay.wechat_pay) await this.requestPayment(pay.wechat_pay)
				uni.showToast({ title: pay.paid ? '已开启认证' : '支付已发起', icon: 'success' })
				setTimeout(() => this.load(), 700)
			} catch (error) {
				uni.showToast({ title: error.message || '创建订单失败', icon: 'none' })
			} finally {
				this.payingId = 0
			}
		},
		async continuePay(orderId) {
			this.submitting = true
			try {
				const result = await continueCertificationPay(orderId)
				const pay = result.payment || {}
				if (pay.wechat_pay) await this.requestPayment(pay.wechat_pay)
				uni.showToast({ title: pay.paid ? '已开启认证' : '支付已发起', icon: 'success' })
				setTimeout(() => this.load(), 700)
			} catch (error) {
				uni.showToast({ title: error.message || '继续支付失败', icon: 'none' })
			} finally {
				this.submitting = false
			}
		},
		requestPayment(payload) {
			return new Promise((resolve, reject) => {
				uni.requestPayment({ ...payload, success: resolve, fail: reject })
			})
		},
		onIdCardInput(event) {
			this.realName.id_card_no = String(event.detail.value || '').toUpperCase()
		},
		async submitRealNameForm() {
			const idCardNo = String(this.realName.id_card_no || '').toUpperCase()
			if (!this.realName.name || !idCardNo) {
				uni.showToast({ title: '请填写姓名和身份证号', icon: 'none' })
				return
			}
			if (!/^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])([0-2]\d|3[01])\d{3}[\dX]$/.test(idCardNo)) {
				uni.showToast({ title: '身份证号格式不正确', icon: 'none' })
				return
			}
			this.submitting = true
			try {
				await submitRealName({ name: this.realName.name, id_card_no: idCardNo })
				uni.showToast({ title: '实名认证通过', icon: 'success' })
				await this.load()
			} catch (error) {
				uni.showToast({ title: error.message || '实名认证失败', icon: 'none' })
				await this.load()
			} finally {
				this.submitting = false
			}
		},
		chooseAndUpload(record) {
			uni.chooseImage({
				count: 1,
				sizeType: ['compressed'],
				sourceType: ['album', 'camera'],
				success: async (res) => {
					this.uploadingCode = record.item_code
					try {
						await uploadCertificationMaterial(record.item_code, res.tempFilePaths[0])
						uni.showToast({ title: '上传成功', icon: 'success' })
						await this.load()
					} catch (error) {
						uni.showToast({ title: error.message || '上传失败', icon: 'none' })
					} finally {
						this.uploadingCode = ''
					}
				},
			})
		},
		async submitManual(record) {
			this.submittingCode = record.item_code
			try {
				await submitManualCertification(record.item_code, { remark: this.manualRemarks[record.item_code] || '' })
				uni.showToast({ title: '已提交审核', icon: 'success' })
				await this.load()
			} catch (error) {
				uni.showToast({ title: error.message || '提交失败', icon: 'none' })
			} finally {
				this.submittingCode = ''
			}
		},
		preview(materials, current) {
			const urls = materials.map((item) => item.file_url).filter(Boolean)
			uni.previewImage({
				urls: ossImageList(urls, { width: 1200, quality: 85 }),
				current: ossImage(current, { width: 1200, mode: 'lfit', quality: 85 }),
			})
		},
		appStatusLabel(value) {
			return { pending_payment: '待支付', paid_pending_submit: '待提交', in_progress: '进行中', approved: '已通过', rejected: '已驳回', expired: '已过期' }[value] || value
		},
		recordStatusLabel(value) {
			return { not_submitted: '待补齐', submitted: '已提交', verifying: '核验中', pending_review: '待审核', approved: '已通过', rejected: '需重提', expired: '已过期' }[value] || value
		},
	},
}
</script>

<style>
.cert-page {
	background: #f7f4ef;
	box-sizing: border-box;
	color: #3d3532;
	min-height: 100vh;
	padding: 28rpx 28rpx 132rpx;
}

.top-card,
.package-card,
.application-card,
.task-card,
.approved-card,
.empty-card {
	background: #fffdfa;
	border: 1rpx solid #eaded7;
	border-radius: 28rpx;
	box-shadow: 0 12rpx 30rpx rgba(90, 54, 45, 0.06);
	box-sizing: border-box;
	padding: 28rpx;
}

.brand-row,
.package-head,
.section-head,
.record-top,
.upload-row,
.rights {
	align-items: center;
	display: flex;
	gap: 18rpx;
	justify-content: space-between;
}

.brand {
	align-items: center;
	color: #7a6f69;
	display: flex;
	font-size: 24rpx;
	font-weight: 800;
	gap: 12rpx;
}

.brand-mark {
	align-items: center;
	background: #c15b65;
	border-radius: 14rpx;
	color: #fff;
	display: flex;
	font-size: 26rpx;
	font-weight: 800;
	height: 48rpx;
	justify-content: center;
	width: 48rpx;
}

.level-pill,
.status,
.record-status,
.section-note,
.block-count {
	background: #f3eee7;
	border-radius: 999rpx;
	color: #7a6f69;
	font-size: 22rpx;
	font-weight: 850;
	padding: 10rpx 18rpx;
	white-space: nowrap;
}

.headline,
.subhead,
.section-title,
.section-desc,
.package-title,
.package-desc,
.block-title,
.benefit-text,
.right-value,
.right-label,
.buy-title,
.buy-desc,
.record-title,
.record-desc,
.record-reason,
.progress-text,
.done-title,
.done-desc,
.reuse-title,
.reuse-desc,
.empty-title,
.empty-desc,
.limit-tip {
	display: block;
}

.headline {
	font-size: 54rpx;
	font-weight: 850;
	line-height: 1.18;
	margin-top: 28rpx;
}

.subhead {
	color: #7a6f69;
	font-size: 28rpx;
	line-height: 1.58;
	margin-top: 16rpx;
}

.progress-wrap {
	margin-top: 26rpx;
}

.progress {
	background: #efe6de;
	border-radius: 999rpx;
	height: 16rpx;
	overflow: hidden;
}

.progress-bar {
	background: linear-gradient(90deg, #5c8f68, #c15b65);
	border-radius: 999rpx;
	height: 100%;
}

.progress-text {
	color: #7a6f69;
	font-size: 24rpx;
	margin-top: 14rpx;
}

.panel {
	display: grid;
	gap: 22rpx;
	margin-top: 24rpx;
}

.section-head.loose {
	align-items: flex-start;
}

.section-title {
	color: #3d3532;
	font-size: 34rpx;
	font-weight: 850;
}

.section-desc {
	color: #7a6f69;
	font-size: 25rpx;
	line-height: 1.5;
	margin-top: 8rpx;
}

.package-card {
	padding: 26rpx;
}

.package-card.selected {
	border-color: #d88790;
	box-shadow: 0 14rpx 34rpx rgba(193, 91, 101, 0.13);
}

.package-title {
	font-size: 34rpx;
	font-weight: 850;
}

.package-desc {
	color: #746860;
	font-size: 25rpx;
	line-height: 1.45;
	margin-top: 8rpx;
	max-width: 450rpx;
}

.price-box {
	flex-shrink: 0;
	text-align: right;
}

.price {
	color: #c15b65;
	display: block;
	font-size: 34rpx;
	font-weight: 900;
}

.price-tip {
	color: #9b8d84;
	display: block;
	font-size: 22rpx;
	margin-top: 4rpx;
}

.block-title-row {
	align-items: center;
	display: flex;
	justify-content: space-between;
	margin-top: 24rpx;
}

.block-title {
	color: #3d3532;
	font-size: 26rpx;
	font-weight: 850;
}

.item-chips,
.done-chips {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 16rpx;
}

.item-chip,
.done-chip {
	background: #fbf3e4;
	border: 1rpx solid #e5c790;
	border-radius: 999rpx;
	color: #754347;
	font-size: 23rpx;
	font-weight: 800;
	padding: 12rpx 16rpx;
}

.rights {
	background: #f8f4ec;
	border-radius: 22rpx;
	margin-top: 22rpx;
	padding: 20rpx 14rpx;
}

.benefit-box {
	background: #fff7f0;
	border: 1rpx solid #eaded7;
	border-radius: 22rpx;
	margin-top: 22rpx;
	padding: 20rpx;
}

.benefit-text {
	color: #754347;
	font-size: 25rpx;
	line-height: 1.55;
	margin-top: 10rpx;
	white-space: pre-line;
}

.right-item {
	flex: 1;
	text-align: center;
}

.right-value {
	color: #5c8f68;
	font-size: 25rpx;
	font-weight: 900;
}

.right-label {
	color: #8d7f78;
	font-size: 20rpx;
	line-height: 1.25;
	margin-top: 6rpx;
}

.primary-btn,
.secondary-btn {
	border: 0;
	border-radius: 999rpx;
	box-sizing: border-box;
	font-size: 28rpx;
	font-weight: 850;
	height: 86rpx;
	line-height: 86rpx;
	margin: 0;
	padding: 0 24rpx;
}

.primary-btn {
	background: #c15b65;
	color: #fff;
}

.secondary-btn {
	background: #edf3e6;
	color: #5c8f68;
}

.primary-btn.single {
	margin-top: 22rpx;
	width: 100%;
}

.buy-bar {
	align-items: center;
	background: rgba(255, 253, 250, 0.96);
	border: 1rpx solid #eaded7;
	border-radius: 28rpx;
	box-shadow: 0 12rpx 30rpx rgba(90, 54, 45, 0.08);
	display: flex;
	gap: 18rpx;
	justify-content: space-between;
	padding: 22rpx;
	position: sticky;
	bottom: 24rpx;
	z-index: 2;
}

.buy-title {
	color: #3d3532;
	font-size: 30rpx;
	font-weight: 850;
}

.buy-desc {
	color: #8d7f78;
	font-size: 23rpx;
	margin-top: 8rpx;
}

.buy-btn {
	flex: 0 0 220rpx;
}

.done-box,
.reuse-photo {
	background: #f5faf2;
	border: 1rpx solid #dbe9d7;
	border-radius: 22rpx;
	margin-top: 22rpx;
	padding: 24rpx;
}

.done-title,
.reuse-title {
	color: #4e865e;
	font-size: 30rpx;
	font-weight: 850;
}

.done-desc,
.reuse-desc {
	color: #7a6f69;
	font-size: 25rpx;
	line-height: 1.55;
	margin-top: 8rpx;
}

.record-card {
	border-top: 1rpx solid #f0e5dc;
	padding: 24rpx 0;
}

.record-card:first-of-type {
	border-top: 0;
}

.record-top {
	align-items: flex-start;
}

.record-title {
	font-size: 30rpx;
	font-weight: 850;
}

.record-desc,
.record-reason,
.limit-tip {
	color: #8d7f78;
	font-size: 24rpx;
	line-height: 1.45;
	margin-top: 8rpx;
}

.record-reason {
	color: #b9505b;
}

.record-status.rejected {
	background: #fff0f0;
	color: #b9505b;
}

.record-status.pending_review {
	background: #fff7df;
	color: #9a6a22;
}

.record-status.approved {
	background: #eef5ec;
	color: #4e865e;
}

.form-block,
.manual-panel {
	margin-top: 18rpx;
}

.input,
.textarea {
	background: #f7f1e8;
	border-radius: 20rpx;
	box-sizing: border-box;
	color: #3d3532;
	font-size: 28rpx;
	margin-top: 14rpx;
	padding: 0 24rpx;
	width: 100%;
}

.input {
	height: 84rpx;
}

.textarea {
	height: 140rpx;
	line-height: 1.45;
	padding-top: 20rpx;
}

.upload-row {
	margin-top: 14rpx;
}

.upload-row .primary-btn,
.upload-row .secondary-btn {
	flex: 1;
}

.materials {
	margin-top: 16rpx;
	white-space: nowrap;
	width: 100%;
}

.material-img {
	background: #eadfd6;
	border-radius: 18rpx;
	height: 128rpx;
	margin-right: 14rpx;
	width: 128rpx;
}

.empty-card {
	margin-top: 24rpx;
	text-align: center;
}

.empty-title {
	font-size: 30rpx;
	font-weight: 850;
}

.empty-desc {
	color: #8d7f78;
	font-size: 24rpx;
	margin-top: 12rpx;
}

button::after {
	border: 0;
}
</style>
