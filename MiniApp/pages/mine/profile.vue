<template>
	<view class="page profile-page">
		<view class="hero">
			<text class="eyebrow">个人情况</text>
			<text class="hero-title">让真实资料替你开场</text>
			<text class="hero-desc">这些资料会同步到 CRM 人员主体，手机号、身份证和认证等级不能在这里修改。</text>
		</view>

		<view class="card">
			<view class="section-head">
				<view>
					<text class="section-title">照片相册</text>
					<text class="section-desc">上传清晰本人照片，系统会做人脸检测。</text>
				</view>
				<button class="mini-btn" :loading="uploading" @tap="choosePhoto">添加</button>
			</view>
			<view class="photo-grid">
				<view
					v-for="(slot, index) in photoSlots"
					:key="slot.label"
					class="photo"
					:class="{ filled: slot.url, empty: !slot.url }"
					@tap="slot.url ? preview(index) : choosePhoto()"
				>
					<image v-if="slot.url" class="photo-img" :src="thumb(slot.url, 220, 220)" mode="aspectFill" />
					<text v-if="slot.badge" class="badge">{{ slot.badge }}</text>
					<text v-if="slot.url" class="remove" @tap.stop="removePhoto(index)">×</text>
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
			<view class="photo-hint"><text>第一张照片会作为主展示照；每张照片都需要通过真人脸检测。</text></view>
		</view>

		<view class="card">
			<text class="section-title">基础资料</text>
			<view class="field"><text class="label">姓名</text><input v-model.trim="form.name" class="input" placeholder="请输入姓名" /></view>
			<picker :range="genderOptions" range-key="label" :value="optionIndex(genderOptions, form.gender)" @change="pickOption('gender', genderOptions, $event)">
				<view class="field"><text class="label">性别</text><text class="value">{{ optionLabel(genderOptions, form.gender) || '请选择' }}</text></view>
			</picker>
			<view class="field"><text class="label">微信号</text><input v-model.trim="form.wechat" class="input" placeholder="请输入微信号" /></view>
			<picker mode="date" :value="form.birth_date || ''" @change="form.birth_date = $event.detail.value">
				<view class="field"><text class="label">生日</text><text class="value">{{ form.birth_date || '请选择' }}</text></view>
			</picker>
			<view class="field"><text class="label">身高</text><input v-model.number="form.height_cm" class="input" type="number" placeholder="cm" /></view>
			<picker :range="ethnicityOptions" range-key="label" :value="optionIndex(ethnicityOptions, form.ethnicity)" @change="pickOption('ethnicity', ethnicityOptions, $event)">
				<view class="field"><text class="label">民族</text><text class="value">{{ optionLabel(ethnicityOptions, form.ethnicity) || '请选择' }}</text></view>
			</picker>
		</view>

		<view class="card">
			<text class="section-title">现实情况</text>
			<view class="field"><text class="label">职业</text><input v-model.trim="form.occupation" class="input" placeholder="请输入职业" /></view>
			<picker :range="annualIncomeOptions" range-key="label" :value="optionIndex(annualIncomeOptions, form.annual_income)" @change="pickOption('annual_income', annualIncomeOptions, $event)">
				<view class="field"><text class="label">年收入</text><text class="value">{{ optionLabel(annualIncomeOptions, form.annual_income) || '请选择' }}</text></view>
			</picker>
			<picker :range="maritalStatusOptions" range-key="label" :value="optionIndex(maritalStatusOptions, form.marital_status)" @change="pickOption('marital_status', maritalStatusOptions, $event)">
				<view class="field"><text class="label">婚况</text><text class="value">{{ optionLabel(maritalStatusOptions, form.marital_status) || '请选择' }}</text></view>
			</picker>
			<picker :range="educationOptions" range-key="label" :value="optionIndex(educationOptions, form.education)" @change="pickOption('education', educationOptions, $event)">
				<view class="field"><text class="label">学历</text><text class="value">{{ optionLabel(educationOptions, form.education) || '请选择' }}</text></view>
			</picker>
			<picker :range="houseStatusOptions" range-key="label" :value="optionIndex(houseStatusOptions, form.house_status)" @change="pickOption('house_status', houseStatusOptions, $event)">
				<view class="field"><text class="label">房产</text><text class="value">{{ optionLabel(houseStatusOptions, form.house_status) || '请选择' }}</text></view>
			</picker>
			<picker :range="carStatusOptions" range-key="label" :value="optionIndex(carStatusOptions, form.car_status)" @change="pickOption('car_status', carStatusOptions, $event)">
				<view class="field"><text class="label">车辆</text><text class="value">{{ optionLabel(carStatusOptions, form.car_status) || '请选择' }}</text></view>
			</picker>
		</view>

		<view class="card">
			<text class="section-title">地区与介绍</text>
			<picker mode="region" @change="pickRegion('hometown', $event)">
				<view class="field"><text class="label">籍贯</text><text class="value">{{ form.hometown || '请选择' }}</text></view>
			</picker>
			<picker mode="region" @change="pickRegion('residence', $event)">
				<view class="field"><text class="label">常驻地</text><text class="value">{{ form.residence || '请选择' }}</text></view>
			</picker>
			<textarea v-model.trim="form.profile_intro" class="textarea" maxlength="800" placeholder="可以写写你的生活状态、关系期待或希望对方了解你的地方。" />
			<text class="count">{{ (form.profile_intro || '').length }}/800</text>
		</view>

		<view class="bottom-bar"><button class="save-btn" :loading="saving" @tap="submit">保存资料</button></view>
	</view>
</template>

<script>
import { mpMe, uploadRegisterPhoto, mpRegisterOptions } from '../../api/mpAuth.js'
import { mineProfile, saveMineProfile } from '../../api/mpProfile.js'
import { ensureRegisteredSession } from '../../utils/mpSession.js'
import { ossImage, ossPreview } from '../../utils/ossImage.js'

const emptyForm = () => ({
	name: '',
	gender: '2',
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
	profile_intro: '',
})

export default {
	data() {
		return {
			form: emptyForm(),
			saving: false,
			uploading: false,
			photoGuideLabels: ['本人正脸', '生活照', '补充照片', '旅行/日常', '兴趣瞬间', '自然半身'],
			genderOptions: [{ label: '男生', value: '0' }, { label: '女生', value: '1' }, { label: '暂不展示', value: '2' }],
			ethnicityOptions: [],
			annualIncomeOptions: [],
			educationOptions: [],
			maritalStatusOptions: [],
			houseStatusOptions: [],
			carStatusOptions: [],
		}
	},
	computed: {
		photoSlots() {
			return this.photoGuideLabels.map((label, index) => ({
				label,
				url: this.form.photo_urls[index] || '',
				badge: index === 0 ? '主展示照' : '',
			}))
		},
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		thumb(url, width, height) {
			return ossImage(url, { width, height })
		},
		async load() {
			try {
				await ensureRegisteredSession()
				let profile = {}
				try {
					profile = await mineProfile()
				} catch (error) {
					const me = await mpMe()
					profile = { user: me.user, person: me.person }
				}
				const options = await mpRegisterOptions()
				const person = profile.person || {}
				this.form = { ...emptyForm(), ...person, birth_date: person.birth_date || '', photo_urls: person.photo_urls || [] }
				this.annualIncomeOptions = options.annual_income || []
				this.ethnicityOptions = options.ethnicity || []
				this.educationOptions = options.education || []
				this.maritalStatusOptions = options.marital_status || []
				this.houseStatusOptions = options.house_status || []
				this.carStatusOptions = options.car_status || []
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			}
		},
		optionIndex(options, value) {
			return Math.max(0, options.findIndex((item) => item.value === value))
		},
		optionLabel(options, value) {
			const item = options.find((option) => option.value === value)
			return item ? item.label : ''
		},
		pickOption(field, options, event) {
			const item = options[Number(event.detail.value)]
			this.form[field] = item ? item.value : ''
		},
		pickRegion(field, event) {
			this.form[field] = (event.detail.value || []).join(' ')
		},
		choosePhoto() {
			const remainingCount = this.photoGuideLabels.length - this.form.photo_urls.length
			if (remainingCount <= 0) {
				uni.showToast({ title: '最多上传6张照片', icon: 'none' })
				return
			}
			uni.chooseImage({
				count: remainingCount,
				sizeType: ['compressed'],
				sourceType: ['album', 'camera'],
				success: async (res) => {
					const paths = res.tempFilePaths || []
					if (!paths.length) return
					this.uploading = true
					uni.showLoading({ title: '上传照片中' })
					try {
						for (const filePath of paths) {
							const result = await uploadRegisterPhoto(filePath)
							const url = result.file_url || result.url
							if (url && !this.form.photo_urls.includes(url)) this.form.photo_urls.push(url)
						}
						uni.showToast({ title: '照片已通过检测', icon: 'none' })
					} catch (error) {
						uni.showModal({
							title: '照片不符合要求',
							content: error.message || '照片上传失败',
							showCancel: false,
							confirmText: '重新上传',
						})
					} finally {
						uni.hideLoading()
						this.uploading = false
					}
				},
			})
		},
		removePhoto(index) {
			this.form.photo_urls.splice(index, 1)
		},
		preview(index) {
			const urls = this.form.photo_urls.map((url) => ossPreview(url))
			uni.previewImage({ urls, current: urls[index] })
		},
		async submit() {
			if (!this.form.name) {
				uni.showToast({ title: '请填写姓名', icon: 'none' })
				return
			}
			if (!this.form.photo_urls.length) {
				uni.showToast({ title: '请至少上传一张本人照片', icon: 'none' })
				return
			}
			this.saving = true
			try {
				await saveMineProfile({ ...this.form, height_cm: this.form.height_cm ? Number(this.form.height_cm) : null })
				uni.showToast({ title: '已保存', icon: 'success' })
				setTimeout(() => uni.navigateBack(), 500)
			} catch (error) {
				uni.showToast({ title: error.message || '保存失败', icon: 'none' })
			} finally {
				this.saving = false
			}
		},
	},
}
</script>

<style>
.profile-page { min-height: 100vh; background: #f7f4ef; box-sizing: border-box; padding-bottom: 180rpx; }
.hero { padding: 34rpx 28rpx 12rpx; }
.eyebrow, .hero-title, .hero-desc, .section-title, .section-desc, .label, .value, .count { display: block; }
.eyebrow { color: #b85c67; font-size: 24rpx; font-weight: 800; }
.hero-title { color: #3f2d28; font-size: 42rpx; font-weight: 900; margin-top: 10rpx; }
.hero-desc, .section-desc { color: #8d7f78; font-size: 25rpx; line-height: 1.6; margin-top: 8rpx; }
.card { margin: 24rpx; padding: 28rpx; border-radius: 28rpx; background: #fffaf3; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); }
.section-head { display: flex; justify-content: space-between; align-items: center; gap: 20rpx; }
.section-title { color: #4b342d; font-size: 32rpx; font-weight: 900; margin-bottom: 10rpx; }
.mini-btn { width: 132rpx; height: 64rpx; line-height: 64rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 24rpx; margin: 0; }
.photo-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18rpx; margin-top: 24rpx; }
.photo { aspect-ratio: 1; border: 1rpx solid #eaded7; border-radius: 20rpx; box-sizing: border-box; color: #7a6f69; display: flex; flex-direction: column; font-size: 24rpx; font-weight: 800; justify-content: center; overflow: hidden; position: relative; text-align: center; }
.photo.empty { background: #fbf7f1; color: #754347; }
.photo.filled { background: #8b726a; border-color: rgba(117, 67, 71, .18); color: #fff; }
.photo-img { height: 100%; width: 100%; }
.badge { background: rgba(70, 31, 38, .82); border-radius: 999rpx; color: #fff; font-size: 20rpx; font-weight: 850; left: 12rpx; padding: 8rpx 12rpx; position: absolute; top: 12rpx; z-index: 3; }
.remove { position: absolute; right: 10rpx; top: 10rpx; width: 40rpx; height: 40rpx; border-radius: 50%; background: rgba(193, 91, 101, .92); color: #fff; text-align: center; line-height: 36rpx; font-size: 30rpx; z-index: 4; }
.photo-mask { align-items: center; background: linear-gradient(180deg, rgba(61, 53, 50, .12), rgba(61, 53, 50, .56)); bottom: 0; box-sizing: border-box; color: #fff; display: flex; flex-direction: column; font-size: 24rpx; font-weight: 850; gap: 6rpx; justify-content: center; left: 0; line-height: 1.25; padding: 28rpx 10rpx 18rpx; position: absolute; right: 0; top: 0; text-shadow: 0 2rpx 6rpx rgba(61, 53, 50, .35); }
.plus { color: #c15b65; font-size: 46rpx; line-height: 1; }
.photo-hint { align-items: flex-start; background: #fbf3e4; border: 1rpx solid #e5c790; border-radius: 18rpx; color: #7a6f69; display: flex; font-size: 24rpx; line-height: 1.5; margin-top: 20rpx; padding: 18rpx 20rpx; }
.field { display: flex; align-items: center; justify-content: space-between; min-height: 96rpx; border-bottom: 1rpx solid rgba(91,68,58,.08); }
.field:last-child { border-bottom: 0; }
.label { color: #4b342d; font-size: 28rpx; font-weight: 800; width: 160rpx; flex-shrink: 0; }
.input { flex: 1; text-align: right; color: #3f2d28; font-size: 28rpx; }
.value { flex: 1; color: #7b6659; font-size: 28rpx; text-align: right; }
.textarea { width: 100%; min-height: 180rpx; box-sizing: border-box; background: #fff; border-radius: 20rpx; padding: 20rpx; margin-top: 20rpx; color: #3f2d28; font-size: 28rpx; }
.count { text-align: right; color: #9a8a7f; font-size: 22rpx; margin-top: 8rpx; }
.bottom-bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 999; box-sizing: border-box; padding: 18rpx 24rpx 34rpx; padding-bottom: calc(34rpx + env(safe-area-inset-bottom)); background: rgba(247,244,239,.98); box-shadow: 0 -12rpx 30rpx rgba(90,54,45,.08); pointer-events: auto; }
.save-btn { display: flex; align-items: center; justify-content: center; height: 88rpx; line-height: 88rpx; border-radius: 999rpx; background: #c95d65; color: #fff; font-size: 30rpx; font-weight: 800; position: relative; z-index: 1000; }
</style>
