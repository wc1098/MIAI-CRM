<template>
	<view class="page preference-page">
		<view class="hero">
			<text class="eyebrow">个人信息维护</text>
			<text class="hero-title">择偶要求</text>
			<text class="hero-desc">选择越清晰，订阅推荐越有方向。不确定的项目保持不限即可。</text>
		</view>

		<view class="card section">
			<view class="section-head">
				<text class="section-title">基础范围</text>
				<text class="section-desc">用于先过滤明显不合适的人选。</text>
			</view>
			<view class="sub-title">期望年龄</view>
			<view class="range-row">
				<picker mode="selector" :range="ageLimitOptions" range-key="label" :value="limitIndex(ageLimitOptions, form.age_min)" @change="onLimitChange('age_min', ageLimitOptions, $event)">
					<view class="range-cell"><text class="range-label">下限</text><text class="range-value">{{ limitLabel(ageLimitOptions, form.age_min) }}</text></view>
				</picker>
				<text class="range-separator">至</text>
				<picker mode="selector" :range="ageLimitOptions" range-key="label" :value="limitIndex(ageLimitOptions, form.age_max)" @change="onLimitChange('age_max', ageLimitOptions, $event)">
					<view class="range-cell"><text class="range-label">上限</text><text class="range-value">{{ limitLabel(ageLimitOptions, form.age_max) }}</text></view>
				</picker>
			</view>
			<view class="sub-title">期望身高</view>
			<view class="range-row">
				<picker mode="selector" :range="heightLimitOptions" range-key="label" :value="limitIndex(heightLimitOptions, form.height_min_cm)" @change="onLimitChange('height_min_cm', heightLimitOptions, $event)">
					<view class="range-cell"><text class="range-label">下限</text><text class="range-value">{{ limitLabel(heightLimitOptions, form.height_min_cm) }}</text></view>
				</picker>
				<text class="range-separator">至</text>
				<picker mode="selector" :range="heightLimitOptions" range-key="label" :value="limitIndex(heightLimitOptions, form.height_max_cm)" @change="onLimitChange('height_max_cm', heightLimitOptions, $event)">
					<view class="range-cell"><text class="range-label">上限</text><text class="range-value">{{ limitLabel(heightLimitOptions, form.height_max_cm) }}</text></view>
				</picker>
			</view>
		</view>

		<view class="card section">
			<view class="section-head">
				<text class="section-title">地区范围</text>
				<text class="section-desc">支持选择省份或城市；省份代表接受全省，未选择表示不限。</text>
			</view>
			<view class="sub-title">常驻地</view>
			<view class="region-actions">
				<view class="chip" :class="{ active: !form.preferred_residence_region_codes.length }" @tap="clearField('preferred_residence_region_codes')">不限</view>
				<picker mode="region" @change="addRegion('preferred_residence_region_codes', $event, 1)"><view class="region-add">添加省份</view></picker>
				<picker mode="region" @change="addRegion('preferred_residence_region_codes', $event, 2)"><view class="region-add">添加城市</view></picker>
			</view>
			<view v-if="form.preferred_residence_region_codes.length" class="selected-list">
				<view v-for="item in form.preferred_residence_region_codes" :key="'r'+item" class="selected-chip" @tap="removeFromField('preferred_residence_region_codes', item)">{{ item }} ×</view>
			</view>
			<view class="sub-title">籍贯</view>
			<view class="region-actions">
				<view class="chip" :class="{ active: !form.preferred_hometown_region_codes.length }" @tap="clearField('preferred_hometown_region_codes')">不限</view>
				<picker mode="region" @change="addRegion('preferred_hometown_region_codes', $event, 1)"><view class="region-add">添加省份</view></picker>
				<picker mode="region" @change="addRegion('preferred_hometown_region_codes', $event, 2)"><view class="region-add">添加城市</view></picker>
			</view>
			<view v-if="form.preferred_hometown_region_codes.length" class="selected-list">
				<view v-for="item in form.preferred_hometown_region_codes" :key="'h'+item" class="selected-chip" @tap="removeFromField('preferred_hometown_region_codes', item)">{{ item }} ×</view>
			</view>
			<view class="sub-title">是否接受异地</view>
			<view class="chips">
				<view class="chip" :class="{ active: form.accept_long_distance === null }" @tap="form.accept_long_distance = null">不限</view>
				<view class="chip" :class="{ active: form.accept_long_distance === true }" @tap="form.accept_long_distance = true">接受</view>
				<view class="chip" :class="{ active: form.accept_long_distance === false }" @tap="form.accept_long_distance = false">不接受</view>
			</view>
		</view>

		<view class="card section">
			<view class="section-head">
				<text class="section-title">现实条件</text>
				<text class="section-desc">这些条件支持多选，不选就是不限。</text>
			</view>
			<view class="option-group">
				<view class="sub-title">学历</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_education_codes.length }" @tap="clearField('preferred_education_codes')">不限</view><view v-for="item in educationOptions" :key="'edu'+item.value" class="chip" :class="{ active: includes('preferred_education_codes', item.value) }" @tap="toggle('preferred_education_codes', item.value)">{{ item.label }}</view></view>
			</view>
			<view class="option-group">
				<view class="sub-title">婚况</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_marital_status_codes.length }" @tap="clearField('preferred_marital_status_codes')">不限</view><view v-for="item in maritalStatusOptions" :key="'marital'+item.value" class="chip" :class="{ active: includes('preferred_marital_status_codes', item.value) }" @tap="toggle('preferred_marital_status_codes', item.value)">{{ item.label }}</view></view>
			</view>
			<view class="option-group">
				<view class="sub-title">年收入</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_annual_income_codes.length }" @tap="clearField('preferred_annual_income_codes')">不限</view><view v-for="item in annualIncomeOptions" :key="'income'+item.value" class="chip" :class="{ active: includes('preferred_annual_income_codes', item.value) }" @tap="toggle('preferred_annual_income_codes', item.value)">{{ item.label }}</view></view>
			</view>
			<view class="option-group">
				<view class="sub-title">房产</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_house_status_codes.length }" @tap="clearField('preferred_house_status_codes')">不限</view><view v-for="item in houseStatusOptions" :key="'house'+item.value" class="chip" :class="{ active: includes('preferred_house_status_codes', item.value) }" @tap="toggle('preferred_house_status_codes', item.value)">{{ item.label }}</view></view>
			</view>
			<view class="option-group">
				<view class="sub-title">车辆</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_car_status_codes.length }" @tap="clearField('preferred_car_status_codes')">不限</view><view v-for="item in carStatusOptions" :key="'car'+item.value" class="chip" :class="{ active: includes('preferred_car_status_codes', item.value) }" @tap="toggle('preferred_car_status_codes', item.value)">{{ item.label }}</view></view>
			</view>
		</view>

		<view class="card section">
			<view class="section-head">
				<text class="section-title">婚育态度</text>
				<text class="section-desc">用于推荐时理解底线和接受范围。</text>
			</view>
			<view class="sub-title">接受离异</view>
			<view class="chips">
				<view class="chip" :class="{ active: form.accept_divorced === null }" @tap="form.accept_divorced = null">不限</view>
				<view class="chip" :class="{ active: form.accept_divorced === true }" @tap="form.accept_divorced = true">接受</view>
				<view class="chip" :class="{ active: form.accept_divorced === false }" @tap="form.accept_divorced = false">不接受</view>
			</view>
			<view class="sub-title">接受有子女</view>
			<view class="chips">
				<view class="chip" :class="{ active: form.accept_children === null }" @tap="form.accept_children = null">不限</view>
				<view class="chip" :class="{ active: form.accept_children === true }" @tap="form.accept_children = true">接受</view>
				<view class="chip" :class="{ active: form.accept_children === false }" @tap="form.accept_children = false">不接受</view>
			</view>
		</view>

		<view class="card section">
			<view class="section-head">
				<text class="section-title">性格生活</text>
				<text class="section-desc">这些偏好会参与画像匹配，不作为硬性筛掉。</text>
			</view>
			<view class="option-group">
				<view class="sub-title">性格偏好</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_personality_tags.length }" @tap="clearField('preferred_personality_tags')">不限</view><view v-for="item in personalityOptions" :key="'personality'+item.value" class="chip" :class="{ active: includes('preferred_personality_tags', item.value) }" @tap="toggle('preferred_personality_tags', item.value)">{{ item.label }}</view></view>
			</view>
			<view class="option-group">
				<view class="sub-title">生活方式</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_lifestyle_tags.length }" @tap="clearField('preferred_lifestyle_tags')">不限</view><view v-for="item in lifestyleOptions" :key="'lifestyle'+item.value" class="chip" :class="{ active: includes('preferred_lifestyle_tags', item.value) }" @tap="toggle('preferred_lifestyle_tags', item.value)">{{ item.label }}</view></view>
			</view>
			<view class="option-group">
				<view class="sub-title">关系期待</view>
				<view class="chips"><view class="chip" :class="{ active: !form.preferred_relationship_tags.length }" @tap="clearField('preferred_relationship_tags')">不限</view><view v-for="item in relationshipOptions" :key="'relationship'+item.value" class="chip" :class="{ active: includes('preferred_relationship_tags', item.value) }" @tap="toggle('preferred_relationship_tags', item.value)">{{ item.label }}</view></view>
			</view>
		</view>

		<view class="card section">
			<view class="section-head">
				<text class="section-title">自由描述</text>
				<text class="section-desc">只有这里需要手动填写。可以补充你特别看重的相处感受、价值观或不能接受的情况。</text>
			</view>
			<textarea v-model.trim="form.preference_text" class="free-textarea" maxlength="800" placeholder="例如：希望对方情绪稳定、沟通真诚，愿意一起经营长期关系。不太接受长期异地和生活作息差异过大。" />
			<text class="textarea-count">{{ (form.preference_text || '').length }}/800</text>
		</view>

		<view class="bottom-bar">
			<button class="save-btn" :loading="saving" @tap="submit">保存择偶要求</button>
		</view>
	</view>
</template>

<script>
import { mpRegisterOptions } from '../../api/mpAuth.js'
import { getPartnerPreference, savePartnerPreference } from '../../api/mpProfile.js'
import { ensureMpSession } from '../../utils/mpSession.js'

const emptyForm = () => ({
	age_min: null,
	age_max: null,
	height_min_cm: null,
	height_max_cm: null,
	preferred_residence_region_codes: [],
	preferred_hometown_region_codes: [],
	preferred_education_codes: [],
	preferred_marital_status_codes: [],
	preferred_annual_income_codes: [],
	preferred_house_status_codes: [],
	preferred_car_status_codes: [],
	accept_long_distance: null,
	accept_divorced: null,
	accept_children: null,
	children_requirement: '',
	preferred_personality_tags: [],
	preferred_lifestyle_tags: [],
	preferred_relationship_tags: [],
	hard_reject_items: [],
	soft_preference_items: [],
	preferred_occupation_text: '',
	preference_text: '',
	strictness_level: 'normal',
	must_match_fields: [],
	preferred_match_fields: [],
})

export default {
	data() {
		return {
			form: emptyForm(),
			saving: false,
			annualIncomeOptions: [],
			maritalStatusOptions: [],
			educationOptions: [],
			houseStatusOptions: [],
			carStatusOptions: [],
			personalityOptions: ['情绪稳定', '外向开朗', '温和顾家', '独立成熟', '有责任心', '真诚直接'].map((v) => ({ label: v, value: v })),
			lifestyleOptions: ['规律作息', '爱运动', '喜欢旅行', '重视家庭', '消费理性', '愿意下厨'].map((v) => ({ label: v, value: v })),
			relationshipOptions: ['结婚目标明确', '重视陪伴', '重视沟通', '边界感清晰', '共同成长', '尊重彼此'].map((v) => ({ label: v, value: v })),
			ageLimitOptions: [{ label: '不限', value: null }, ...Array.from({ length: 63 }, (_, index) => {
				const value = index + 18
				return { label: `${value}岁`, value }
			})],
			heightLimitOptions: [{ label: '不限', value: null }, ...Array.from({ length: 71 }, (_, index) => {
				const value = index + 140
				return { label: `${value}cm`, value }
			})],
		}
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	methods: {
		async load() {
			try {
				await ensureMpSession()
				const [options, preference] = await Promise.all([mpRegisterOptions().catch(() => ({})), getPartnerPreference()])
				this.applyOptions(options || {})
				const current = preference.current || {}
				this.form = this.normalizeForm({ ...emptyForm(), ...current })
			} catch (error) {
				uni.showToast({ title: '请先完成注册', icon: 'none' })
				setTimeout(() => uni.navigateTo({ url: '/pages/register/index' }), 500)
			}
		},
		applyOptions(options) {
			this.annualIncomeOptions = this.toOptions(options.annual_income, ['10万以下', '10-20万', '20-30万', '30-50万', '50万以上'])
			this.maritalStatusOptions = this.toOptions(options.marital_status, ['未婚', '离异', '丧偶'])
			this.educationOptions = this.toOptions(options.education, ['大专', '本科', '硕士', '博士及以上'])
			this.houseStatusOptions = this.toOptions(options.house_status, ['有房', '无房', '与家人同住'])
			this.carStatusOptions = this.toOptions(options.car_status, ['有车', '无车'])
		},
		toOptions(list, fallbackLabels) {
			if (Array.isArray(list) && list.length) return list.filter((item) => item.value !== '')
			return fallbackLabels.map((v) => ({ label: v, value: v }))
		},
		normalizeForm(form) {
			const normalized = { ...form }
			const arrayFields = [
				'preferred_residence_region_codes',
				'preferred_hometown_region_codes',
				'preferred_education_codes',
				'preferred_marital_status_codes',
				'preferred_annual_income_codes',
				'preferred_house_status_codes',
				'preferred_car_status_codes',
				'preferred_personality_tags',
				'preferred_lifestyle_tags',
				'preferred_relationship_tags',
				'hard_reject_items',
				'soft_preference_items',
				'must_match_fields',
				'preferred_match_fields',
			]
			arrayFields.forEach((field) => {
				normalized[field] = Array.isArray(normalized[field]) ? normalized[field] : []
			})
			;['age_min', 'age_max', 'height_min_cm', 'height_max_cm'].forEach((field) => {
				normalized[field] = normalized[field] === '' || normalized[field] === undefined ? null : normalized[field]
			})
			;['accept_long_distance', 'accept_divorced', 'accept_children'].forEach((field) => {
				normalized[field] = typeof normalized[field] === 'boolean' ? normalized[field] : null
			})
			return normalized
		},
		includes(field, value) {
			return (this.form[field] || []).includes(value)
		},
		toggle(field, value) {
			const list = this.form[field] || []
			this.form[field] = list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
		},
		clearField(field) {
			this.form[field] = []
		},
		removeFromField(field, value) {
			this.form[field] = (this.form[field] || []).filter((item) => item !== value)
		},
		limitIndex(options, value) {
			const index = options.findIndex((item) => item.value === value)
			return index >= 0 ? index : 0
		},
		limitLabel(options, value) {
			return options.find((item) => item.value === value)?.label || '不限'
		},
		onLimitChange(field, options, event) {
			this.form[field] = options[Number(event.detail.value)]?.value ?? null
			this.normalizeRangePair(field)
		},
		normalizeRangePair(field) {
			const isAge = field.indexOf('age') === 0
			const minField = isAge ? 'age_min' : 'height_min_cm'
			const maxField = isAge ? 'age_max' : 'height_max_cm'
			const min = this.form[minField]
			const max = this.form[maxField]
			if (min !== null && max !== null && min > max) {
				this.form[field === minField ? maxField : minField] = this.form[field]
				uni.showToast({ title: '已自动调整范围', icon: 'none' })
			}
		},
		addRegion(field, event, level) {
			const values = event.detail.value || []
			const value = values[level - 1]
			if (!value) return
			const list = this.form[field] || []
			if (!list.includes(value)) {
				this.form[field] = [...list, value]
			}
		},
		async submit() {
			this.saving = true
			try {
				const payload = {
					...this.form,
					children_requirement: '',
					hard_reject_items: [],
					soft_preference_items: [],
					preferred_occupation_text: '',
				}
				await savePartnerPreference(payload)
				uni.showToast({ title: '已保存', icon: 'success' })
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
.preference-page {
	min-height: 100vh;
	padding: 28rpx 24rpx 170rpx;
	background: radial-gradient(circle at 92% 0%, rgba(214, 140, 120, 0.16), transparent 24%), #f7f0e7;
	box-sizing: border-box;
	color: #4d362b;
}

.hero,
.card {
	background: rgba(255, 252, 246, 0.96);
	border: 1rpx solid rgba(139, 104, 78, 0.13);
	border-radius: 26rpx;
	box-shadow: 0 16rpx 38rpx rgba(88, 60, 42, 0.07);
	padding: 30rpx;
}

.eyebrow,
.hero-title,
.hero-desc,
.section-title,
.section-desc,
.sub-title,
.textarea-count {
	display: block;
}

.eyebrow {
	color: #8f9f7e;
	font-size: 24rpx;
	font-weight: 800;
}

.hero-title {
	margin-top: 10rpx;
	color: #4b342d;
	font-family: "Songti SC", serif;
	font-size: 56rpx;
	font-weight: 900;
	line-height: 1.12;
}

.hero-desc,
.section-desc {
	margin-top: 10rpx;
	color: #806e63;
	font-size: 26rpx;
	line-height: 1.58;
}

.section {
	margin-top: 22rpx;
}

.section-head {
	margin-bottom: 20rpx;
}

.section-title {
	color: #4b342d;
	font-size: 34rpx;
	font-weight: 850;
	line-height: 1.35;
}

.sub-title {
	margin: 24rpx 0 14rpx;
	color: #6b5046;
	font-size: 27rpx;
	font-weight: 800;
}

.range-row {
	display: grid;
	grid-template-columns: 1fr 48rpx 1fr;
	gap: 14rpx;
	align-items: center;
}

.range-cell {
	min-height: 86rpx;
	padding: 14rpx 18rpx;
	border: 1rpx solid rgba(91, 68, 58, 0.1);
	border-radius: 20rpx;
	background: #fffdf8;
	box-sizing: border-box;
}

.range-label,
.range-value {
	display: block;
}

.range-label {
	color: #9a8a80;
	font-size: 22rpx;
	font-weight: 750;
}

.range-value {
	margin-top: 6rpx;
	color: #4b342d;
	font-size: 28rpx;
	font-weight: 850;
}

.range-separator {
	color: #9a8a80;
	font-size: 24rpx;
	font-weight: 800;
	text-align: center;
}

.option-group:first-of-type .sub-title {
	margin-top: 0;
}

.region-actions,
.chips {
	display: flex;
	flex-wrap: wrap;
	gap: 14rpx;
}

.region-actions {
	align-items: center;
}

.chip {
	min-height: 62rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 0 24rpx;
	border: 1rpx solid rgba(91, 68, 58, 0.1);
	border-radius: 999rpx;
	background: #fffdf8;
	color: #6e615b;
	font-size: 25rpx;
	font-weight: 700;
	box-sizing: border-box;
}

.region-add {
	min-height: 62rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 0 24rpx;
	border: 1rpx solid rgba(93, 154, 120, 0.28);
	border-radius: 999rpx;
	background: rgba(93, 154, 120, 0.08);
	color: #5d9a78;
	font-size: 25rpx;
	font-weight: 800;
	box-sizing: border-box;
}

.selected-list {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
	margin-top: 14rpx;
}

.selected-chip {
	padding: 12rpx 20rpx;
	border-radius: 999rpx;
	background: #f3ece2;
	color: #6b5046;
	font-size: 24rpx;
	font-weight: 750;
}

.chip.active {
	background: #c96060;
	border-color: #c96060;
	color: #fff;
	box-shadow: 0 10rpx 22rpx rgba(201, 96, 96, 0.18);
}

.free-textarea {
	width: 100%;
	min-height: 220rpx;
	padding: 22rpx;
	border: 1rpx solid rgba(91, 68, 58, 0.1);
	border-radius: 22rpx;
	background: #fffdf8;
	color: #4b342d;
	font-size: 28rpx;
	line-height: 1.55;
	box-sizing: border-box;
}

.textarea-count {
	margin-top: 12rpx;
	text-align: right;
	color: #9a8a80;
	font-size: 23rpx;
}

.bottom-bar {
	position: fixed;
	right: 0;
	bottom: 0;
	left: 0;
	padding: 18rpx 24rpx calc(22rpx + env(safe-area-inset-bottom));
	border-top: 1rpx solid rgba(91, 68, 58, 0.08);
	background: rgba(247, 240, 231, 0.96);
}

.save-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 92rpx;
	line-height: 92rpx;
	border-radius: 999rpx;
	background: #c96060;
	color: #fff;
	font-size: 32rpx;
	font-weight: 900;
	box-shadow: 0 14rpx 28rpx rgba(201, 96, 96, 0.22);
}
</style>
