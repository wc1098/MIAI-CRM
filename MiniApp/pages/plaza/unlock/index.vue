<template>
	<view class="page unlock-page">
		<view class="target-card">
			<image class="avatar" :src="avatarUrl(target.avatar_url)" mode="aspectFill"></image>
			<view class="target-info">
				<text class="name">{{ target.display_name || '觅AI用户' }}</text>
				<text class="meta">ID {{ target.display_no }} · {{ target.residence || '常驻地待补充' }}</text>
			</view>
		</view>

		<view class="step-card">
			<view class="step-item" :class="{ active: currentStep === 'question', done: !question }">
				<text class="step-index">1</text>
				<text>默契挑战</text>
			</view>
			<view class="step-line"></view>
			<view class="step-item" :class="{ active: currentStep === 'task', done: allTasksDone }">
				<text class="step-index">2</text>
				<text>心动任务</text>
			</view>
		</view>

		<view v-if="currentStep === 'question'" class="section">
			<view class="section-head">
				<text class="section-title">先完成默契挑战（{{ questionProgressText }}）</text>
				<text class="section-subtitle">回答后可获得心动值，再进入心动任务。</text>
			</view>
			<view v-if="question" class="question-card">
				<text class="question">{{ question.question }}</text>
				<button
					v-for="option in question.options"
					:key="option.value"
					class="option-btn"
					:class="{ selected: selectedAnswer === option.value }"
					:disabled="answering"
					@tap="answerQuestion(option.value)"
				>{{ option.label }}</button>
			</view>
			<text v-else class="muted">默契题已完成，正在进入任务加分。</text>
		</view>

		<view v-else class="section">
			<view class="section-head">
				<text class="section-title">继续完成任务</text>
				<text class="section-subtitle">完成下方任务，让心动值更接近解锁。</text>
			</view>
			<view v-for="task in guideTasks" :key="task.task_code" class="task-row">
				<view>
					<text class="task-name">{{ task.task_name }}</text>
					<text class="task-desc">+{{ task.score }} 心动值</text>
				</view>
				<button v-if="task.complete_mode === 'share' && task.available" class="task-btn" open-type="share">{{ taskButtonText(task) }}</button>
				<button v-else class="task-btn" :disabled="!task.available" @tap="handleTask(task)">{{ taskButtonText(task) }}</button>
			</view>
		</view>

		<view class="bottom-progress">
			<view class="progress-top">
				<text class="progress-title">心动值</text>
				<view class="score-wrap">
					<text v-if="scoreAnim.show" class="score-bump">+{{ scoreAnim.value }}</text>
					<text class="progress-score" :class="{ pulse: scoreAnim.pulse }">{{ progress.score || 0 }}/{{ progress.target_score || 100 }}</text>
				</view>
			</view>
			<view class="progress"><view class="progress-inner" :style="`width:${progress.percent || 0}%`"></view></view>
			<view class="bottom-copy">
				<text>{{ bottomHint }}</text>
				<text class="limit">今日剩余 {{ daily.remaining || 0 }} 次</text>
			</view>
			<button class="bottom-btn" :class="{ pay: showPaidUnlock }" :disabled="mainDisabled" @tap="handleMainAction">{{ mainButtonText }}</button>
		</view>
	</view>
</template>

<script>
import { answerUnlockQuestion, completeUnlockTask, unlockProgress, unlockQuestions } from '../../../api/mpPlaza.js'
import { ossImage, ossPreview } from '../../../utils/ossImage.js'

export default {
	data() {
		return {
			displayNo: '',
			data: {},
			question: null,
			questionMeta: { total: 3, answered: 0, remaining: 3 },
			selectedAnswer: '',
			answering: false,
			scoreAnim: { show: false, value: 0, pulse: false },
		}
	},
	computed: {
		target() { return this.data.target || {} },
		progress() { return this.data.progress || {} },
		daily() { return this.data.daily_unlock || {} },
		coupon() { return this.data.coupon || {} },
		payment() { return this.data.payment || {} },
		copy() { return this.data.copy || {} },
		guideTasks() {
			return (this.data.tasks || []).filter((item) => !['daily_login', 'daily_browse', 'view_profile'].includes(item.task_code))
		},
		currentStep() { return this.question ? 'question' : 'task' },
		questionProgressText() {
			const total = Number(this.questionMeta.total || 3)
			const answered = Number(this.questionMeta.answered || 0)
			return `${Math.min(answered + 1, total)}/${total}`
		},
		allTasksDone() {
			const tasks = this.guideTasks
			return tasks.length ? tasks.every((item) => !item.available) : true
		},
		canFreeUnlock() {
			return this.data.is_unlocked || this.coupon.available || this.progress.free_unlock_eligible
		},
		showPaidUnlock() {
			return this.currentStep === 'task' && !this.canFreeUnlock && this.payment.allow_paid_boost && this.allTasksDone
		},
		mainButtonText() {
			if (this.data.is_unlocked) return '查看联系方式'
			if (this.currentStep === 'question') return '先回答默契题'
			if (this.canFreeUnlock) return '进入最后一步'
			if (this.showPaidUnlock) return `付费直接解锁 ¥${this.payment.price || '0.00'}`
			return '继续完成任务'
		},
		mainDisabled() {
			return this.currentStep === 'question' || (!this.canFreeUnlock && !this.showPaidUnlock)
		},
		bottomHint() {
			if (this.data.is_unlocked) return '已解锁，可直接查看联系方式。'
			if (this.currentStep === 'question') return '先回答默契题，拿到第一段心动值。'
			if (this.coupon.available) return '有可用免费券，建议优先使用。'
			if (this.progress.free_unlock_eligible) return '心动值已达标，可以进入最后一步。'
			if (this.showPaidUnlock) return '当前任务已完成，心动值仍不足，可付费直接解锁。'
			return '继续完成任务，心动值满后即可解锁。'
		},
	},
	onLoad(options) {
		this.displayNo = options.display_no || ''
	},
	onShow() {
		this.load()
	},
	onPullDownRefresh() {
		this.load().finally(() => uni.stopPullDownRefresh())
	},
	onShareAppMessage() {
		const shareTask = this.guideTasks.find((item) => item.task_code === 'share_card' && item.available)
		if (shareTask) this.completeTask(shareTask, false)
		return {
			title: `${this.target.display_name || '觅AI用户'}的资料`,
			path: `/pages/plaza/detail/index?display_no=${this.displayNo}`,
			imageUrl: this.target.avatar_url ? ossPreview(this.target.avatar_url, { width: 800 }) : undefined,
		}
	},
	onShareTimeline() {
		const shareTask = this.guideTasks.find((item) => item.task_code === 'share_card' && item.available)
		if (shareTask) this.completeTask(shareTask, false)
		return {
			title: `${this.target.display_name || '觅AI用户'}的资料`,
			query: `display_no=${this.displayNo}`,
			imageUrl: this.target.avatar_url ? ossPreview(this.target.avatar_url, { width: 800 }) : undefined,
		}
	},
	methods: {
		avatarUrl(url) {
			return ossImage(url, { width: 180, height: 180 }) || '/static/logo.png'
		},
		async load() {
			if (!this.displayNo) return
			try {
				this.data = await unlockProgress(this.displayNo)
				await this.ensureViewTaskDone()
				this.data = await unlockProgress(this.displayNo)
				const res = await unlockQuestions(this.displayNo)
				this.questionMeta = {
					total: Number(res.total || res.limit || 3),
					answered: Number(res.answered || 0),
					remaining: Number(res.remaining || 0),
				}
				this.question = res.items && res.items.length ? res.items[0] : null
				this.selectedAnswer = ''
				this.answering = false
			} catch (error) {
				uni.showToast({ title: error.message || '加载失败', icon: 'none' })
			}
		},
		async ensureViewTaskDone() {
			const task = (this.data.tasks || []).find((item) => item.task_code === 'view_profile' && item.available)
			if (!task) return
			this.data = await completeUnlockTask(this.displayNo, task.task_code)
		},
		async completeTask(task, showToast = true) {
			if (!task.available) return
			try {
				this.data = await completeUnlockTask(this.displayNo, task.task_code)
				if (showToast) uni.showToast({ title: `+${task.score} 心动值`, icon: 'none' })
				await this.load()
			} catch (error) {
				uni.showToast({ title: error.message || '任务失败', icon: 'none' })
			}
		},
		handleTask(task) {
			if (!task.available) return
			if (task.complete_mode === 'detail_action') {
				uni.navigateTo({ url: `/pages/plaza/detail/index?display_no=${this.displayNo}` })
				return
			}
			this.completeTask(task)
		},
		taskButtonText(task) {
			if (!task.available) return '已完成'
			if (task.complete_mode === 'detail_action') return '去详情页'
			if (task.complete_mode === 'share') return '去转发'
			return '去完成'
		},
		async answerQuestion(value) {
			if (!this.question || this.answering) return
			this.selectedAnswer = value
			this.answering = true
			const before = Number(this.progress.score || 0)
			try {
				this.data = await answerUnlockQuestion(this.displayNo, this.question.id, value)
				const after = Number((this.data.progress || {}).score || 0)
				this.showScoreChange(Math.max(0, after - before))
				uni.showToast({ title: '已增加心动值', icon: 'none' })
				await this.sleep(520)
				await this.load()
			} catch (error) {
				this.answering = false
				uni.showToast({ title: error.message || '提交失败', icon: 'none' })
			}
		},
		showScoreChange(value) {
			if (!value) return
			this.scoreAnim = { show: true, value, pulse: true }
			setTimeout(() => { this.scoreAnim.show = false }, 760)
			setTimeout(() => { this.scoreAnim.pulse = false }, 420)
		},
		sleep(ms) {
			return new Promise((resolve) => setTimeout(resolve, ms))
		},
		handleMainAction() {
			if (this.mainDisabled) return
			this.goFinal()
		},
		goFinal() {
			uni.navigateTo({ url: `/pages/plaza/unlock/final?display_no=${this.displayNo}` })
		},
	},
}
</script>

<style>
page { background: #f7f1e8; }
.unlock-page { min-height: 100vh; padding: 24rpx 24rpx 260rpx; color: #3f2f2a; }
.target-card, .step-card, .section { margin-bottom: 24rpx; padding: 28rpx; border-radius: 28rpx; background: #fffaf3; box-shadow: 0 12rpx 32rpx rgba(95,70,50,.08); }
.target-card { display: flex; gap: 22rpx; align-items: center; }
.avatar { width: 132rpx; height: 132rpx; border-radius: 28rpx; }
.name { display: block; font-size: 36rpx; font-weight: 700; }
.meta, .section-subtitle, .task-desc, .muted { display: block; margin-top: 8rpx; color: #8a776a; font-size: 25rpx; line-height: 1.6; }
.step-card { display: flex; align-items: center; gap: 18rpx; }
.step-item { display: flex; align-items: center; gap: 10rpx; color: #9a897d; font-size: 25rpx; font-weight: 600; }
.step-item.active { color: #c95d65; }
.step-item.done { color: #6d7e60; }
.step-index { width: 42rpx; height: 42rpx; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: #fff; background: #cdbdaf; font-size: 22rpx; }
.step-item.active .step-index { background: #c95d65; }
.step-item.done .step-index { background: #8ea078; }
.step-line { flex: 1; height: 2rpx; background: #eaded1; }
.section-head { margin-bottom: 20rpx; }
.section-title { display: block; font-size: 34rpx; font-weight: 700; }
.question { display: block; margin-bottom: 18rpx; font-size: 30rpx; font-weight: 700; line-height: 1.5; }
.option-btn { margin-top: 16rpx; height: 82rpx; display: flex; align-items: center; justify-content: center; padding: 0 20rpx; border-radius: 20rpx; color: #5a463d; background: #f1e7dc; font-size: 27rpx; line-height: 1.2; transition: all .18s; }
.option-btn.selected { color: #fff; background: #c95d65; transform: scale(.98); box-shadow: 0 12rpx 28rpx rgba(201, 93, 101, .22); }
.option-btn[disabled]:not(.selected) { color: #5a463d; background: #f1e7dc; }
.option-btn::after { border: 0; }
.task-row { display: grid; grid-template-columns: minmax(0, 1fr) 160rpx; column-gap: 24rpx; align-items: center; padding: 20rpx 0; border-top: 1rpx solid #efe4d8; }
.task-row:first-of-type { border-top: 0; }
.task-name { display: block; font-size: 28rpx; font-weight: 600; }
.task-btn { width: 160rpx; height: 64rpx; display: flex; align-items: center; justify-content: center; justify-self: end; padding: 0; border-radius: 999rpx; color: #fff; background: #c95d65; font-size: 24rpx; line-height: 1; }
.task-btn::after, .bottom-btn::after { border: 0; }
.task-btn[disabled] { color: #9b8d83; background: #eee3d7; }
.bottom-progress { position: fixed; left: 0; right: 0; bottom: 0; z-index: 20; padding: 22rpx 24rpx calc(22rpx + env(safe-area-inset-bottom)); border-top-left-radius: 30rpx; border-top-right-radius: 30rpx; background: rgba(255, 250, 243, .98); box-shadow: 0 -14rpx 36rpx rgba(74, 53, 47, .12); }
.progress-top, .bottom-copy { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.progress-title { font-size: 30rpx; font-weight: 700; }
.score-wrap { position: relative; display: flex; align-items: center; justify-content: flex-end; min-width: 160rpx; }
.progress-score { color: #c95d65; font-size: 30rpx; font-weight: 700; transition: transform .2s; }
.progress-score.pulse { transform: scale(1.12); }
.score-bump { position: absolute; right: 0; top: -40rpx; color: #8ea078; font-size: 30rpx; font-weight: 800; animation: scoreFloat .76s ease-out forwards; }
@keyframes scoreFloat {
	0% { opacity: 0; transform: translateY(16rpx) scale(.9); }
	20% { opacity: 1; transform: translateY(0) scale(1); }
	100% { opacity: 0; transform: translateY(-34rpx) scale(1.08); }
}
.progress { height: 18rpx; margin: 18rpx 0 14rpx; border-radius: 999rpx; overflow: hidden; background: #eaded1; }
.progress-inner { height: 100%; background: linear-gradient(90deg, #c95d65, #8ea078); }
.bottom-copy { color: #8a776a; font-size: 24rpx; line-height: 1.5; }
.limit { flex-shrink: 0; color: #6d7e60; }
.bottom-btn { width: 100%; height: 92rpx; margin-top: 18rpx; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 999rpx; color: #fff; background: #c95d65; font-size: 30rpx; font-weight: 700; line-height: 1; box-shadow: 0 12rpx 28rpx rgba(201, 93, 101, .26); }
.bottom-btn.pay { color: #fff; background: #8ea078; box-shadow: 0 12rpx 28rpx rgba(142, 160, 120, .28); }
.bottom-btn[disabled] { color: #9b8d83; background: #eee3d7; box-shadow: none; }
</style>
