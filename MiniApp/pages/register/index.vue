<template>
	<view class="register-page">
		<view v-if="checkingRegistered" class="checking-card">
			<text class="checking-title">正在确认注册状态</text>
			<text class="checking-desc">已注册用户会自动返回，不需要重复填写资料。</text>
		</view>
		<block v-else>
		<view class="top">
			<view class="brand-row">
				<view class="brand">
					<text class="brand-mark">觅</text>
					<text>觅AI 真实缘分档案</text>
				</view>
				<text class="completion">已完成 {{ completionPercent }}%</text>
			</view>
			<text class="headline">{{ stepMeta.title }}</text>
			<text class="subhead">{{ stepMeta.desc }}</text>
			<view class="progress"><view class="progress-bar" :style="{ width: completionPercent + '%' }"></view></view>
		</view>

		<scroll-view class="step-nav" scroll-x>
			<view class="step-tabs">
				<view v-for="(item, index) in steps" :key="item" class="step-tab" :class="{ active: currentStep === index }">
					{{ item }}
				</view>
			</view>
		</scroll-view>

		<view v-if="currentStep === 0" class="panel">
			<view class="section hero-card">
				<text class="mini-kicker">MI AI · TRUSTED PROFILE</text>
				<text class="hero-title">点亮真实档案，提升遇见机会</text>
				<text class="hero-desc">认证完成后，你的资料将获得真实标识，后续可继续补充照片与婚恋信息，让匹配更可信。</text>
			</view>
			<view class="section">
				<text class="section-title">授权确认</text>
				<view class="field-row">
					<text class="label">昵称</text>
					<input v-model.trim="form.nickname" class="field-input right" type="nickname" placeholder="请输入昵称" />
				</view>
				<view class="field-row phone-row">
					<text class="label">手机号</text>
					<view class="phone-action">
						<text class="value" :class="{ placeholder: !phoneMasked }">{{ phoneMasked || '未授权' }}</text>
						<button class="inline-auth-btn" open-type="getPhoneNumber" @getphonenumber="getPhoneNumber">
							{{ phoneMasked ? '重新授权' : '微信授权' }}
						</button>
					</view>
				</view>
				<view class="field-row">
					<text class="label">微信身份</text>
					<text class="verified">{{ form.login_code ? '已准备' : '待登录' }}</text>
				</view>
			</view>
			<view class="agreement">
				<checkbox :checked="form.agreement_accepted" color="#C15B65" @tap="toggleAgreement" />
				<text>我已阅读并同意</text>
				<text class="agreement-link" @tap.stop="openAgreement">《觅AI用户注册协议》</text>
				<text>。平台会严格保护隐私。</text>
			</view>
		</view>

		<view v-if="currentStep === 1" class="panel">
			<view class="section">
				<text class="section-title">基础资料</text>
				<text class="section-desc">先补齐可被信任的基础信息，后续推荐会更准确。</text>
			</view>
			<view class="field-group">
				<view class="field-row input-row"><text class="label">姓名</text><input v-model.trim="form.name" class="field-input right" placeholder="请输入姓名" /></view>
				<view class="section compact">
					<text class="section-title">性别</text>
					<view class="segmented">
						<view v-for="item in genderOptions" :key="item.value" class="option" :class="{ active: form.gender === item.value }" @tap="form.gender = item.value">{{ item.label }}</view>
					</view>
				</view>
				<view class="field-row input-row"><text class="label">微信号</text><input v-model.trim="form.wechat" class="field-input right" placeholder="请输入微信号" /></view>
				<picker mode="date" :value="birthPickerValue" :end="today" @change="pickBirthDate"><view class="field-row"><text class="label">出生日期</text><text class="value">{{ form.birth_date || '请选择' }} ›</text></view></picker>
				<view class="field-row input-row"><text class="label">身高</text><input v-model.number="form.height_cm" class="field-input right" type="number" placeholder="cm" /></view>
				<picker :range="ethnicityOptions" range-key="label" @change="pickOption('ethnicity', ethnicityOptions, $event)"><view class="field-row"><text class="label">民族</text><text class="value">{{ optionLabel('ethnicity', ethnicityOptions) || '请选择' }} ›</text></view></picker>
				<view class="field-row input-row"><text class="label">职业</text><input v-model.trim="form.occupation" class="field-input right" placeholder="请输入职业" /></view>
			</view>
		</view>

		<view v-if="currentStep === 2" class="panel">
			<view class="hint"><text>✦</text><text>完善缘分档案，这些信息会帮助系统生成更合适的缘分推荐。</text></view>
			<view class="section">
				<text class="section-title">年收入</text>
				<view class="chips"><view v-for="item in annualIncomeOptions" :key="item.value" class="chip" :class="{ active: form.annual_income === item.value }" @tap="form.annual_income = item.value">{{ item.label }}</view></view>
			</view>
			<view class="section">
				<text class="section-title">婚况</text>
				<view class="chips"><view v-for="item in maritalStatusOptions" :key="item.value" class="chip" :class="{ active: form.marital_status === item.value }" @tap="form.marital_status = item.value">{{ item.label }}</view></view>
			</view>
			<view class="field-group">
				<picker :range="educationOptions" range-key="label" @change="pickOption('education', educationOptions, $event)"><view class="field-row"><text class="label">学历</text><text class="value">{{ optionLabel('education', educationOptions) || '请选择' }} ›</text></view></picker>
				<picker mode="region" :value="regionPickerValue(form.hometown)" @change="pickRegion('hometown', $event)"><view class="field-row"><text class="label">籍贯</text><text class="value">{{ form.hometown || '请选择' }} ›</text></view></picker>
				<picker mode="region" :value="regionPickerValue(form.residence)" @change="pickRegion('residence', $event)"><view class="field-row"><text class="label">常驻地</text><text class="value">{{ form.residence || '请选择' }} ›</text></view></picker>
			</view>
			<view class="section">
				<text class="section-title">房产信息</text>
				<view class="chips"><view v-for="item in houseStatusOptions" :key="item.value" class="chip" :class="{ active: form.house_status === item.value }" @tap="form.house_status = item.value">{{ item.label }}</view></view>
			</view>
			<view class="section">
				<text class="section-title">购车信息</text>
				<view class="chips"><view v-for="item in carStatusOptions" :key="item.value" class="chip" :class="{ active: form.car_status === item.value }" @tap="form.car_status = item.value">{{ item.label }}</view></view>
			</view>
		</view>

		<view v-if="currentStep === 3" class="panel">
			<view class="section">
				<text class="section-title">真实照片上传</text>
				<text class="section-desc">请上传清晰、自然、包含本人正脸的真实照片。第一张照片将作为系统头像 / 主展示照。</text>
			</view>
			<view class="photo-grid">
				<view
					v-for="(slot, index) in photoSlots"
					:key="slot.label"
					class="photo"
					:class="{ filled: slot.url, empty: !slot.url }"
					@tap="slot.url ? previewPhoto(index) : choosePhotos()"
				>
					<image v-if="slot.url" class="photo-img" :src="slot.url" mode="aspectFill"></image>
					<text v-if="slot.badge" class="badge">{{ slot.badge }}</text>
					<view v-if="slot.url" class="photo-mask">
						<text>{{ slot.label }}</text>
						<text>已上传</text>
					</view>
					<template v-else>
						<text class="plus">＋</text>
						<text>{{ slot.label }}</text>
					</template>
				</view>
			</view>
			<view class="hint"><text>隐</text><text>照片会上传到系统存储，不使用微信头像，也不会同步微信头像。</text></view>
		</view>

		<view v-if="currentStep === 4" class="panel">
			<view class="section">
				<view class="avatar-summary">
					<image v-if="mainPhoto" class="summary-avatar" :src="mainPhoto" mode="aspectFill"></image>
					<view>
						<text class="section-title">确认缘分档案</text>
						<text class="section-desc">提交后将生成专属缘分档案，可在“我的”中继续查看。</text>
					</view>
				</view>
				<view class="summary-list">
					<view v-for="item in confirmRows" :key="item.label" class="summary-row">
						<text class="label">{{ item.label }}</text>
						<text class="value">{{ item.value || '-' }}</text>
					</view>
				</view>
			</view>
		</view>

		<view v-if="toastText" class="toast">{{ toastText }}</view>
		<view class="bottom-bar" :class="{ first: currentStep === 0 }">
			<button v-if="currentStep > 0" class="bottom-btn" @click="prevStep">上一步</button>
			<button class="bottom-btn primary" :loading="submitting || uploading" @click="handlePrimaryAction">{{ primaryButtonText }}</button>
		</view>
		</block>
	</view>
</template>

<script>
import { mpRegister, mpRegisterOptions, uploadRegisterPhoto } from '../../api/mpAuth.js'
import { setSession } from '../../utils/storage.js'
import { ensureMpSession } from '../../utils/mpSession.js'

export default {
	data() {
		return {
			currentStep: 0,
			submitting: false,
			uploading: false,
			checkingRegistered: true,
			redirectUrl: '',
			phoneMasked: '',
			phoneAuthorizedAt: 0,
			phoneCodeMaxAge: 4 * 60 * 1000,
			toastText: '',
			defaultBirthDate: '1990-01-01',
			defaultRegion: ['河南省', '郑州市', '金水区'],
			photoGuideLabels: ['本人正脸', '生活照', '补充照片', '旅行/日常', '兴趣瞬间', '自然半身'],
			steps: ['账号确认', '基础资料', '婚恋资料', '真实照片', '确认提交'],
			stepMetas: [
				{ title: '认真遇见，先从真实资料开始', desc: '完成微信授权后，我们将用于创建你的平台身份，帮助他人更安心地了解你。' },
				{ title: '先补齐可被信任的基础信息', desc: '资料填写采用分阶段引导，减少表单压力，也让后续推荐更准确。' },
				{ title: '完善你的缘分档案', desc: '婚恋资料会用于 AI 推荐辅助和多维筛选，不做绝对匹配承诺。' },
				{ title: '上传真实照片，建立第一印象', desc: '第一张真实本人照片会作为系统头像 / 主展示照，平台会保护照片隐私。' },
				{ title: '确认资料并提交注册', desc: '请确认摘要信息准确无误，提交后会生成你的专属缘分档案。' },
			],
			genderOptions: [
				{ label: '男生', value: '0' },
				{ label: '女生', value: '1' },
			],
			ethnicityOptions: [
				{ label: '汉族', value: 'han' }, { label: '蒙古族', value: 'mongol' }, { label: '回族', value: 'hui' },
				{ label: '藏族', value: 'tibetan' }, { label: '维吾尔族', value: 'uyghur' }, { label: '苗族', value: 'miao' },
				{ label: '彝族', value: 'yi' }, { label: '壮族', value: 'zhuang' }, { label: '满族', value: 'manchu' },
				{ label: '其他', value: 'other' },
			],
			annualIncomeOptions: [
				{ label: '10万以下', value: 'below_100k' }, { label: '10-20万', value: '100k_200k' },
				{ label: '20-50万', value: '200k_500k' }, { label: '50万以上', value: 'above_500k' },
			],
			maritalStatusOptions: [
				{ label: '未婚', value: 'single' }, { label: '离异', value: 'divorced' }, { label: '丧偶', value: 'widowed' },
			],
			educationOptions: [
				{ label: '高中及以下', value: 'high_school_or_below' }, { label: '大专', value: 'college' },
				{ label: '本科', value: 'bachelor' }, { label: '硕士', value: 'master' }, { label: '博士及以上', value: 'doctor_or_above' },
			],
			houseStatusOptions: [
				{ label: '无房', value: 'none' }, { label: '有房无贷', value: 'owned' },
				{ label: '有房有贷', value: 'mortgage' }, { label: '与父母同住', value: 'family' },
			],
			carStatusOptions: [
				{ label: '无车', value: 'none' }, { label: '有车无贷', value: 'owned' }, { label: '有车有贷', value: 'loan' },
			],
			form: {
				login_code: '',
				phone_code: '',
				nickname: '',
				avatar_url: '',
				agreement_accepted: false,
				agreement_version: '1.0',
				agreement_title: '觅AI用户注册协议',
				name: '',
				gender: '',
				wechat: '',
				birth_date: '',
				height_cm: '',
				ethnicity: '',
				occupation: '',
				annual_income: '',
				marital_status: '',
				education: '',
				hometown: '',
				residence: '',
				house_status: '',
				car_status: '',
				photo_urls: [],
			},
		}
	},
	computed: {
		today() {
			const d = new Date()
			return `${d.getFullYear()}-${`${d.getMonth() + 1}`.padStart(2, '0')}-${`${d.getDate()}`.padStart(2, '0')}`
		},
		birthPickerValue() {
			return this.form.birth_date || this.defaultBirthDate
		},
		stepMeta() {
			return this.stepMetas[this.currentStep]
		},
		completionPercent() {
			return (this.currentStep + 1) * 20
		},
		primaryButtonText() {
			if (this.currentStep === 0) return '下一步'
			if (this.currentStep === 4) return '提交注册'
			return '下一步'
		},
		genderLabel() {
			return this.optionLabel('gender', this.genderOptions)
		},
		mainPhoto() {
			return this.form.photo_urls[0] || ''
		},
		photoSlots() {
			return this.photoGuideLabels.map((label, index) => ({
				label,
				url: this.form.photo_urls[index] || '',
				badge: index === 0 ? '主展示照' : '',
			}))
		},
		ageText() {
			if (!this.form.birth_date) return ''
			const birth = new Date(this.form.birth_date.replace(/-/g, '/'))
			const now = new Date()
			let age = now.getFullYear() - birth.getFullYear()
			if (now.getMonth() < birth.getMonth() || (now.getMonth() === birth.getMonth() && now.getDate() < birth.getDate())) {
				age -= 1
			}
			return age > 0 ? `${age}岁` : ''
		},
		confirmRows() {
			return [
				{ label: '昵称', value: this.form.nickname },
				{ label: '姓名 / 性别', value: `${this.form.name} · ${this.genderLabel}` },
				{ label: '手机号', value: this.phoneMasked },
				{ label: '微信号', value: this.form.wechat },
				{ label: '年龄 / 身高', value: `${this.ageText || this.form.birth_date} · ${this.form.height_cm} cm` },
				{ label: '民族 / 职业', value: `${this.optionLabel('ethnicity', this.ethnicityOptions)} · ${this.form.occupation}` },
				{ label: '年收入 / 婚况', value: `${this.optionLabel('annual_income', this.annualIncomeOptions)} · ${this.optionLabel('marital_status', this.maritalStatusOptions)}` },
				{ label: '学历 / 常驻地', value: `${this.optionLabel('education', this.educationOptions)} · ${this.form.residence}` },
				{ label: '籍贯', value: this.form.hometown },
				{ label: '房产 / 车辆', value: `${this.optionLabel('house_status', this.houseStatusOptions)} · ${this.optionLabel('car_status', this.carStatusOptions)}` },
				{ label: '照片预览', value: `主展示照 1 张，共 ${this.form.photo_urls.length} 张` },
			]
		},
	},
	onLoad(options) {
		this.redirectUrl = options && options.redirect ? decodeURIComponent(options.redirect) : ''
		this.guardRegisteredUser()
		this.refreshLoginCode()
		this.fetchRegisterOptions()
	},
	methods: {
		goAfterRegistered() {
			if (this.redirectUrl) {
				const url = this.redirectUrl.startsWith('/') ? this.redirectUrl : `/${this.redirectUrl}`
				if (url.startsWith('/pages/mine/') || url.startsWith('/pages/activity/index') || url.startsWith('/pages/plaza/') || url.startsWith('/pages/subscription/') || url.startsWith('/pages/certification/')) {
					uni.switchTab({ url })
				} else {
					uni.redirectTo({ url })
				}
			} else {
				uni.switchTab({ url: '/pages/mine/index' })
			}
		},
		async guardRegisteredUser() {
			this.checkingRegistered = true
			try {
				const result = await ensureMpSession()
				if (result && result.person) {
					this.goAfterRegistered()
					return
				}
			} catch (error) {
				console.warn('注册页免登检查失败', error)
			} finally {
				this.checkingRegistered = false
			}
		},
		showToast(title) {
			this.toastText = title
			clearTimeout(this.toastTimer)
			this.toastTimer = setTimeout(() => {
				this.toastText = ''
			}, 1800)
			uni.showToast({ title, icon: 'none' })
		},
		async fetchRegisterOptions() {
			try {
				const options = await mpRegisterOptions()
				this.applyOptions('ethnicityOptions', options.ethnicity)
				this.applyOptions('annualIncomeOptions', options.annual_income)
				this.applyOptions('maritalStatusOptions', options.marital_status)
				this.applyOptions('educationOptions', options.education)
				this.applyOptions('houseStatusOptions', options.house_status)
				this.applyOptions('carStatusOptions', options.car_status)
			} catch (error) {
				console.warn('获取注册选项失败，使用本地默认选项', error)
			}
		},
		applyOptions(target, options) {
			if (Array.isArray(options) && options.length) this[target] = options
		},
		refreshLoginCode() {
			return new Promise((resolve) => {
				uni.login({
					provider: 'weixin',
					success: (res) => {
						this.form.login_code = res.code || ''
						resolve(this.form.login_code)
					},
					fail: () => {
						this.form.login_code = 'mock:dev-openid'
						resolve(this.form.login_code)
					},
				})
			})
		},
		getPhoneNumber(event) {
			const detail = event.detail || {}
			if (detail.code) {
				this.form.phone_code = detail.code
				this.phoneAuthorizedAt = Date.now()
				this.phoneMasked = '已授权微信手机号'
				return
			}
			this.showToast('手机号授权失败，请重试')
		},
		toggleAgreement() {
			this.form.agreement_accepted = !this.form.agreement_accepted
		},
		openAgreement() {
			uni.navigateTo({ url: '/pages/agreement/register' })
		},
		pickOption(field, options, event) {
			const item = options[Number(event.detail.value)]
			if (item) this.form[field] = item.value
		},
		optionLabel(field, options) {
			const value = field === 'gender' ? this.form.gender : this.form[field]
			const item = options.find(option => option.value === value)
			return item ? item.label : ''
		},
		pickRegion(field, event) {
			this.form[field] = (event.detail.value || []).join(' / ')
		},
		regionPickerValue(value) {
			return value ? value.split(' / ') : this.defaultRegion
		},
		pickBirthDate(event) {
			this.form.birth_date = event.detail.value
		},
		async choosePhotos() {
			if (this.uploading) return
			const remainingCount = this.photoGuideLabels.length - this.form.photo_urls.length
			if (remainingCount <= 0) return
			uni.chooseImage({
				count: remainingCount,
				sizeType: ['compressed'],
				sourceType: ['album', 'camera'],
				success: async (res) => {
					await this.uploadChosenPhotos(res.tempFilePaths || [])
				},
			})
		},
		previewPhoto(index) {
			if (!this.form.photo_urls[index]) return
			uni.previewImage({
				current: index,
				urls: this.form.photo_urls,
			})
		},
		async uploadChosenPhotos(paths) {
			if (!paths.length) return
			this.uploading = true
			uni.showLoading({ title: '上传照片中' })
			try {
				for (const path of paths) {
					const fileInfo = await uploadRegisterPhoto(path)
					if (fileInfo && fileInfo.file_url) {
						this.form.photo_urls.push(fileInfo.file_url)
					}
				}
				this.form.avatar_url = this.form.photo_urls[0] || ''
			} catch (error) {
				this.showToast(error.message || '照片上传失败')
			} finally {
				uni.hideLoading()
				this.uploading = false
			}
		},
		required(value, message) {
			if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
				this.showToast(message)
				return false
			}
			return true
		},
		validatePhoneAuthorization() {
			if (!this.form.phone_code) {
				this.showToast('请授权微信手机号')
				return false
			}
			if (!this.phoneAuthorizedAt || Date.now() - this.phoneAuthorizedAt > this.phoneCodeMaxAge) {
				this.form.phone_code = ''
				this.phoneMasked = ''
				this.phoneAuthorizedAt = 0
				this.currentStep = 0
				this.showToast('手机号授权已过期，请重新授权')
				return false
			}
			return true
		},
		validateCurrentStep() {
			if (this.currentStep === 0) {
				if (!this.form.agreement_accepted) {
					this.showToast('请先确认注册协议')
					return false
				}
				return this.required(this.form.login_code, '请先完成微信登录')
					&& this.validatePhoneAuthorization()
					&& this.required(this.form.nickname, '请填写昵称')
			}
			if (this.currentStep === 1) {
				return this.required(this.form.name, '请填写姓名')
					&& this.required(this.form.gender, '请选择性别')
					&& this.required(this.form.wechat, '请填写微信号')
					&& this.required(this.form.birth_date, '请选择出生日期')
					&& this.required(this.form.height_cm, '请填写身高')
					&& this.required(this.form.ethnicity, '请选择民族')
					&& this.required(this.form.occupation, '请填写职业')
			}
			if (this.currentStep === 2) {
				return this.required(this.form.annual_income, '请选择年收入')
					&& this.required(this.form.marital_status, '请选择婚况')
					&& this.required(this.form.education, '请选择学历')
					&& this.required(this.form.hometown, '请选择籍贯')
					&& this.required(this.form.residence, '请选择常驻地')
					&& this.required(this.form.house_status, '请选择房产信息')
					&& this.required(this.form.car_status, '请选择购车信息')
			}
			if (this.currentStep === 3) {
				return this.required(this.form.photo_urls, '请至少上传一张真实照片')
			}
			return true
		},
		handlePrimaryAction() {
			if (this.currentStep === 4) {
				this.submitRegister()
				return
			}
			this.nextStep()
		},
		nextStep() {
			if (!this.validateCurrentStep()) return
			this.currentStep += 1
		},
		prevStep() {
			this.currentStep -= 1
		},
		async submitRegister() {
			if (!this.validateCurrentStep() || !this.validatePhoneAuthorization() || this.submitting) return
			this.submitting = true
			try {
				await this.refreshLoginCode()
				const photos = this.form.photo_urls.slice()
				const payload = {
					...this.form,
					avatar_url: photos[0],
					height_cm: Number(this.form.height_cm),
					photo_urls: photos,
				}
				const result = await mpRegister(payload)
				setSession(result)
				uni.showToast({ title: '注册成功', icon: 'success' })
				setTimeout(() => {
					this.goAfterRegistered()
				}, 600)
			} catch (error) {
				this.showToast(error.message || '注册失败')
				if ((error.message || '').includes('手机号') && (error.message || '').includes('code')) {
					this.form.phone_code = ''
					this.phoneMasked = ''
					this.phoneAuthorizedAt = 0
					this.currentStep = 0
				}
				this.refreshLoginCode()
			} finally {
				this.submitting = false
			}
		},
	},
}
</script>

<style>
.register-page {
	background: #f7f4ef;
	box-sizing: border-box;
	min-height: 100vh;
	padding: 28rpx 28rpx 260rpx;
	padding-bottom: calc(260rpx + env(safe-area-inset-bottom));
}

.checking-card {
	align-items: center;
	background: #fff;
	border: 1rpx solid #eadfd6;
	border-radius: 22rpx;
	box-shadow: 0 12rpx 30rpx rgba(82, 54, 45, 0.08);
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	gap: 16rpx;
	justify-content: center;
	margin-top: 220rpx;
	padding: 48rpx 32rpx;
}

.checking-title,
.checking-desc {
	display: block;
	text-align: center;
}

.checking-title {
	color: #2e2522;
	font-size: 34rpx;
	font-weight: 800;
}

.checking-desc {
	color: #7a6f69;
	font-size: 26rpx;
	line-height: 1.6;
}

.top {
	padding: 8rpx 4rpx 24rpx;
}

.brand-row {
	align-items: center;
	display: flex;
	gap: 18rpx;
	justify-content: space-between;
	margin-bottom: 22rpx;
}

.brand {
	align-items: center;
	color: #7a6f69;
	display: flex;
	font-size: 24rpx;
	font-weight: 700;
	gap: 12rpx;
}

.brand-mark {
	align-items: center;
	background: #c15b65;
	border-radius: 14rpx;
	color: #fff;
	display: flex;
	font-size: 26rpx;
	font-weight: 700;
	height: 48rpx;
	justify-content: center;
	width: 48rpx;
}

.completion {
	background: #f6ead6;
	border: 1rpx solid #e5c790;
	border-radius: 999rpx;
	color: #6a3038;
	font-size: 24rpx;
	font-weight: 800;
	padding: 14rpx 20rpx;
	white-space: nowrap;
}

.headline,
.subhead,
.section-title,
.section-desc,
.hero-title,
.hero-desc,
.mini-kicker {
	display: block;
}

.headline {
	color: #3d3532;
	font-size: 58rpx;
	font-weight: 800;
	line-height: 1.15;
}

.subhead {
	color: #7a6f69;
	font-size: 28rpx;
	line-height: 1.58;
	margin-top: 18rpx;
}

.progress {
	background: #efe6de;
	border: 1rpx solid #eaded7;
	border-radius: 999rpx;
	height: 16rpx;
	margin-top: 26rpx;
	overflow: hidden;
}

.progress-bar {
	background: linear-gradient(90deg, #c15b65, #d6ae65);
	border-radius: 999rpx;
	height: 100%;
	transition: width 0.2s ease;
}

.step-nav {
	margin-bottom: 22rpx;
	white-space: nowrap;
	width: 100%;
}

.step-tabs {
	display: flex;
	gap: 14rpx;
}

.step-tab {
	background: #fff;
	border: 1rpx solid #eaded7;
	border-radius: 999rpx;
	color: #7a6f69;
	display: inline-flex;
	font-size: 24rpx;
	font-weight: 750;
	padding: 16rpx 22rpx;
}

.step-tab.active {
	background: #c15b65;
	border-color: #c15b65;
	color: #fff;
}

.panel {
	display: grid;
	gap: 22rpx;
}

.section {
	background: #fff;
	border: 1rpx solid #eaded7;
	border-radius: 20rpx;
	box-shadow: 0 12rpx 30rpx rgba(90, 54, 45, 0.06);
	box-sizing: border-box;
	padding: 28rpx;
}

.section.compact {
	padding: 24rpx;
}

.section-title {
	color: #3d3532;
	font-size: 34rpx;
	font-weight: 800;
	line-height: 1.35;
}

.section-desc {
	color: #7a6f69;
	font-size: 26rpx;
	line-height: 1.55;
	margin-top: 12rpx;
}

.hero-card {
	background: linear-gradient(135deg, #5b2430, #b35a62);
	color: #fff;
	min-height: 310rpx;
	overflow: hidden;
	position: relative;
}

.mini-kicker {
	color: rgba(255, 255, 255, 0.86);
	font-size: 22rpx;
	font-weight: 700;
	letter-spacing: 2rpx;
	margin-bottom: 58rpx;
}

.hero-title {
	font-size: 46rpx;
	font-weight: 800;
	line-height: 1.18;
	max-width: 520rpx;
}

.hero-desc {
	color: rgba(255, 255, 255, 0.9);
	font-size: 26rpx;
	line-height: 1.55;
	margin-top: 16rpx;
}

.field-group {
	display: grid;
	gap: 18rpx;
}

.field-row {
	align-items: center;
	background: #fff;
	border: 1rpx solid #eaded7;
	border-radius: 20rpx;
	box-sizing: border-box;
	display: flex;
	gap: 20rpx;
	justify-content: space-between;
	min-height: 108rpx;
	padding: 0 24rpx;
	margin: 10rpx 0;
}

.input-row {
	background: #fff;
}

.label {
	color: #7a6f69;
	flex: 0 0 auto;
	font-size: 26rpx;
}

.value,
.field-input {
	color: #3d3532;
	font-size: 28rpx;
	font-weight: 700;
	min-width: 0;
}

.right {
	text-align: right;
}

.phone-row {
	padding-right: 14rpx;
}

.phone-action {
	align-items: center;
	display: flex;
	gap: 16rpx;
	justify-content: flex-end;
	min-width: 0;
}

.phone-action .value {
	max-width: 260rpx;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.value.placeholder {
	color: #a89d98;
	font-weight: 650;
}

.inline-auth-btn {
	background: #c15b65;
	border-radius: 999rpx;
	color: #fff;
	flex: 0 0 auto;
	font-size: 24rpx;
	font-weight: 850;
	line-height: 64rpx;
	margin: 0;
	padding: 0 24rpx;
	white-space: nowrap;
}

.inline-auth-btn::after {
	border: 0;
}

.verified {
	background: #eef8f1;
	border-radius: 999rpx;
	color: #3d8a63;
	font-size: 24rpx;
	font-weight: 800;
	padding: 10rpx 18rpx;
}

.agreement {
	align-items: flex-start;
	background: #fff6f4;
	border: 1rpx solid #e6c8c3;
	border-radius: 20rpx;
	color: #3d3532;
	display: flex;
	flex-wrap: wrap;
	font-size: 26rpx;
	gap: 14rpx;
	line-height: 1.52;
	padding: 22rpx;
}

.agreement-link {
	color: #c15b65;
	font-weight: 850;
	text-decoration: underline;
}

.segmented,
.chips {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
	margin-top: 18rpx;
}

.option,
.chip {
	background: #fff;
	border: 1rpx solid #eaded7;
	border-radius: 999rpx;
	color: #7a6f69;
	font-size: 26rpx;
	font-weight: 750;
	padding: 18rpx 24rpx;
}

.option.active,
.chip.active {
	background: #fff1ef;
	border-color: #d88790;
	color: #6a3038;
}

.hint {
	align-items: flex-start;
	background: #fbf3e4;
	border: 1rpx solid #e5c790;
	border-radius: 20rpx;
	color: #7a6f69;
	display: flex;
	font-size: 24rpx;
	gap: 14rpx;
	line-height: 1.5;
	padding: 22rpx 24rpx;
}

.photo-grid {
	display: grid;
	gap: 18rpx;
	grid-template-columns: repeat(3, 1fr);
}

.photo {
	aspect-ratio: 1;
	border: 1rpx solid #eaded7;
	border-radius: 20rpx;
	box-sizing: border-box;
	color: #7a6f69;
	display: flex;
	flex-direction: column;
	font-size: 24rpx;
	font-weight: 700;
	justify-content: center;
	overflow: hidden;
	position: relative;
	text-align: center;
}

.photo.empty {
	background: #fbf7f1;
	color: #754347;
}

.photo.filled {
	background: #8b726a;
	border-color: rgba(117, 67, 71, 0.18);
	color: #fff;
}

.photo-img {
	height: 100%;
	width: 100%;
}

.badge {
	background: rgba(70, 31, 38, 0.82);
	border-radius: 999rpx;
	color: #fff;
	font-size: 20rpx;
	font-weight: 850;
	left: 12rpx;
	padding: 8rpx 12rpx;
	position: absolute;
	top: 12rpx;
	z-index: 2;
}

.photo-mask {
	align-items: center;
	background: linear-gradient(180deg, rgba(61, 53, 50, 0.16), rgba(61, 53, 50, 0.58));
	bottom: 0;
	box-sizing: border-box;
	color: #fff;
	display: flex;
	flex-direction: column;
	font-size: 24rpx;
	font-weight: 850;
	gap: 6rpx;
	justify-content: center;
	left: 0;
	line-height: 1.25;
	padding: 28rpx 10rpx 18rpx;
	position: absolute;
	right: 0;
	top: 0;
	text-shadow: 0 2rpx 6rpx rgba(61, 53, 50, 0.35);
}

.plus {
	color: #c15b65;
	font-size: 46rpx;
	line-height: 1;
}

.avatar-summary {
	align-items: center;
	border-bottom: 1rpx solid #eaded7;
	display: grid;
	gap: 22rpx;
	grid-template-columns: 144rpx 1fr;
	margin-bottom: 18rpx;
	padding-bottom: 22rpx;
}

.summary-avatar {
	border-radius: 24rpx;
	height: 144rpx;
	width: 144rpx;
}

.summary-list {
	display: grid;
	gap: 4rpx;
}

.summary-row {
	align-items: center;
	border-bottom: 1rpx solid #eaded7;
	display: flex;
	gap: 20rpx;
	justify-content: space-between;
	min-height: 82rpx;
}

.summary-row:last-child {
	border-bottom: 0;
}

.summary-row .value {
	max-width: 430rpx;
	overflow-wrap: anywhere;
	text-align: right;
}

.toast {
	background: rgba(61, 53, 50, 0.9);
	border-radius: 999rpx;
	bottom: 132rpx;
	color: #fff;
	font-size: 26rpx;
	font-weight: 750;
	left: 44rpx;
	padding: 22rpx 28rpx;
	position: fixed;
	right: 44rpx;
	text-align: center;
	z-index: 20;
}

.bottom-bar {
	background: rgba(255, 255, 255, 0.94);
	border-top: 1rpx solid #eaded7;
	bottom: 0;
	box-shadow: 0 -12rpx 28rpx rgba(90, 54, 45, 0.08);
	box-sizing: border-box;
	display: grid;
	gap: 20rpx;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1.45fr);
	left: 0;
	padding: 20rpx 20rpx 30rpx;
	padding-bottom: calc(30rpx + env(safe-area-inset-bottom));
	position: fixed;
	right: 0;
	z-index: 10;
}

.bottom-bar.first {
	grid-template-columns: 1fr;
}

.bottom-btn {
	background: #fff;
	border: 1rpx solid #eaded7;
	border-radius: 24rpx;
	box-sizing: border-box;
	color: #3d3532;
	font-size: 32rpx;
	font-weight: 850;
	line-height: 104rpx;
	margin: 0;
	min-height: 104rpx;
	padding: 0;
	width: 100%;
}

.bottom-btn.primary {
	background: #c15b65;
	border-color: #c15b65;
	box-shadow: 0 12rpx 28rpx rgba(193, 91, 101, 0.28);
	color: #fff;
}
</style>
