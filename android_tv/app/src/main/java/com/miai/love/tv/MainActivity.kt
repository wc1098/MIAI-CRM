package com.miai.love.tv

import android.annotation.SuppressLint
import android.app.Activity
import android.app.Dialog
import android.content.Context
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.net.http.SslError
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.TextUtils
import android.util.Log
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.Window
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.animation.AlphaAnimation
import android.view.animation.DecelerateInterpolator
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebStorage
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.GridLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.Locale
import java.util.concurrent.Executors
import kotlin.math.max
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var prefs: SharedPreferences
    private lateinit var root: FrameLayout
    private lateinit var scenePanel: LinearLayout
    private lateinit var webView: WebView
    private lateinit var promoPanel: FrameLayout
    private lateinit var statusPanel: LinearLayout
    private lateinit var statusTitle: TextView
    private lateinit var statusMessage: TextView
    private var playerView: PlayerView? = null
    private var exoPlayer: ExoPlayer? = null
    private var staffCardWebView: WebView? = null
    private var settingsDialog: Dialog? = null
    private var pendingPromoTokenSync = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private val ioExecutor = Executors.newSingleThreadExecutor()
    private val settingsKeyBuffer = ArrayDeque<Int>()
    private val promoItems = mutableListOf<PromoItem>()
    private var currentScene = Scene.SELECT
    private var currentPromoIndex = 0
    private var promoConfig = PromoConfig()
    private var lastBackPressedAt = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        buildContentView()
        keepFullscreen()
        showSceneSelect()
    }

    override fun onResume() {
        super.onResume()
        keepFullscreen()
        webView.onResume()
        staffCardWebView?.onResume()
        exoPlayer?.play()
    }

    override fun onPause() {
        exoPlayer?.pause()
        staffCardWebView?.onPause()
        webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        settingsDialog?.dismiss()
        exoPlayer?.release()
        staffCardWebView?.destroy()
        webView.destroy()
        ioExecutor.shutdownNow()
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) keepFullscreen()
    }

    @Deprecated("Deprecated Android API override")
    override fun onBackPressed() {
        if (settingsDialog?.isShowing == true) {
            settingsDialog?.dismiss()
            return
        }
        if (currentScene != Scene.SELECT) {
            if (currentScene == Scene.USER_WALL) pullTokenFromWebView()
            showSceneSelect()
            return
        }
        val now = System.currentTimeMillis()
        if (now - lastBackPressedAt <= BACK_EXIT_INTERVAL_MS) {
            finish()
            return
        }
        lastBackPressedAt = now
        Toast.makeText(this, "再按一次返回退出大屏", Toast.LENGTH_SHORT).show()
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        logKeyEvent("dispatchKeyEvent", event.keyCode, event)
        if (event.action == KeyEvent.ACTION_DOWN) {
            val keyCode = normalizeOk(event.keyCode)
            if (keyCode == KeyEvent.KEYCODE_MENU) {
                showSettingsDialog()
                return true
            }
            if (handleSettingsShortcut(keyCode)) return true
            if (keyCode == KeyEvent.KEYCODE_BACK) {
                onBackPressed()
                return true
            }
            if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER && statusPanel.visibility == View.VISIBLE) {
                retryCurrentScene()
                return true
            }
            if (currentScene == Scene.USER_WALL && keyCode == KeyEvent.KEYCODE_DPAD_CENTER) {
                webView.evaluateJavascript("window.dispatchEvent(new Event('miai-tv-confirm'));", null)
                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

    override fun onKeyLongPress(keyCode: Int, event: KeyEvent): Boolean {
        logKeyEvent("onKeyLongPress", keyCode, event)
        return when (normalizeOk(keyCode)) {
            KeyEvent.KEYCODE_DPAD_CENTER -> {
                showSettingsDialog()
                true
            }
            else -> super.onKeyLongPress(keyCode, event)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun buildContentView() {
        root = FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        scenePanel = buildScenePanel()
        webView = WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            isFocusable = true
            isFocusableInTouchMode = true
            setBackgroundColor(Color.BLACK)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = WebSettings.LOAD_DEFAULT
            settings.mediaPlaybackRequiresUserGesture = false
            settings.loadWithOverviewMode = true
            settings.useWideViewPort = true
            settings.userAgentString = "${settings.userAgentString} MiaiTvShell/${BuildConfig.VERSION_NAME}"
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            settings.allowFileAccess = false
            settings.allowContentAccess = true
            addJavascriptInterface(TokenBridge(), "MiaiTvShell")
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                    hideStatus()
                    if (!url.isNullOrBlank()) prefs.edit().putString(KEY_LAST_LOADED_URL, url).apply()
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    if (pendingPromoTokenSync) {
                        pullTokenFromWebView {
                            pendingPromoTokenSync = false
                            loadPromo()
                        }
                    } else {
                        syncTokenToWebView()
                    }
                }

                override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                    if (request?.isForMainFrame == true) showStatus("大屏暂不可用", error?.description?.toString() ?: "页面加载失败")
                }

                override fun onReceivedSslError(view: WebView?, handler: SslErrorHandler?, error: SslError?) {
                    handler?.cancel()
                    showStatus("大屏暂不可用", "证书校验失败，请检查服务器地址")
                }
            }
        }
        promoPanel = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            visibility = View.GONE
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        }
        statusPanel = buildStatusPanel()
        root.addView(webView)
        root.addView(promoPanel)
        root.addView(scenePanel)
        root.addView(statusPanel)
        setContentView(root)
    }

    private fun buildScenePanel(): LinearLayout {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(80, 70, 80, 70)
            setBackgroundColor(Color.rgb(17, 19, 24))
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        }
        panel.addView(TextView(this).apply {
            text = "觅爱智慧大屏"
            textSize = 42f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 14)
        })
        panel.addView(TextView(this).apply {
            text = "请选择播放场景"
            textSize = 20f
            setTextColor(Color.rgb(174, 181, 192))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 42)
        })
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        row.addView(sceneButton("用户墙") { openUserWall() })
        row.addView(sceneButton("宣传大屏") { openPromo() })
        panel.addView(row)
        return panel
    }

    private fun sceneButton(label: String, action: () -> Unit): Button {
        return Button(this).apply {
            text = label
            textSize = 28f
            isAllCaps = false
            minWidth = 260
            minHeight = 112
            setOnClickListener { action() }
            layoutParams = LinearLayout.LayoutParams(300, 132).apply { setMargins(20, 0, 20, 0) }
        }
    }

    private fun buildStatusPanel(): LinearLayout {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.rgb(18, 20, 24))
            visibility = View.GONE
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            setPadding(64, 64, 64, 64)
        }
        statusTitle = TextView(this).apply {
            text = "大屏暂不可用"
            setTextColor(Color.WHITE)
            textSize = 36f
            gravity = Gravity.CENTER
        }
        statusMessage = TextView(this).apply {
            setTextColor(Color.rgb(184, 190, 198))
            textSize = 22f
            gravity = Gravity.CENTER
            setPadding(0, 24, 0, 36)
        }
        val retry = Button(this).apply {
            text = "重试"
            textSize = 22f
            setOnClickListener { retryCurrentScene() }
        }
        panel.addView(statusTitle)
        panel.addView(statusMessage)
        panel.addView(retry)
        return panel
    }

    private fun showSceneSelect() {
        currentScene = Scene.SELECT
        mainHandler.removeCallbacksAndMessages(null)
        exoPlayer?.stop()
        promoPanel.removeAllViews()
        promoPanel.visibility = View.GONE
        webView.visibility = View.GONE
        scenePanel.visibility = View.VISIBLE
        hideStatus()
        scenePanel.requestFocus()
    }

    private fun openUserWall() {
        currentScene = Scene.USER_WALL
        mainHandler.removeCallbacksAndMessages(null)
        exoPlayer?.stop()
        scenePanel.visibility = View.GONE
        promoPanel.visibility = View.GONE
        webView.visibility = View.VISIBLE
        if (!isNetworkAvailable()) {
            showStatus("大屏暂不可用", "网络不可用，请连接网络后按 OK 重试")
            return
        }
        hideStatus()
        webView.loadUrl(userWallUrl())
        webView.requestFocus()
    }

    private fun openPromo() {
        currentScene = Scene.PROMO
        scenePanel.visibility = View.GONE
        webView.visibility = View.GONE
        promoPanel.visibility = View.VISIBLE
        if (deviceToken().isBlank()) {
            pendingPromoTokenSync = true
            showLoading("正在读取设备授权")
            webView.loadUrl(userWallUrl())
        } else {
            loadPromo()
        }
    }

    private fun loadPromo() {
        if (!isNetworkAvailable()) {
            showStatus("宣传大屏暂不可用", "网络不可用，请连接网络后按 OK 重试")
            return
        }
        val token = deviceToken()
        if (token.isBlank()) {
            showStatus("设备未绑定", "请先进入用户墙完成设备绑定；绑定成功后再进入宣传大屏")
            return
        }
        showLoading("正在同步宣传素材")
        ioExecutor.execute {
            try {
                val json = httpJson("GET", "${apiBaseUrl()}/screen/player/promo", token)
                val data = json.getJSONObject("data")
                promoConfig = PromoConfig.fromJson(data.getJSONObject("config"))
                val loaded = parsePromoItems(data.getJSONArray("items"))
                cacheCurrentPlaylist(loaded, token)
                mainHandler.post {
                    promoItems.clear()
                    promoItems.addAll(loaded.filter { it.isPlayable() })
                    currentPromoIndex = 0
                    if (!promoConfig.enabled) showStatus("宣传大屏未启用", "请在后台启用宣传大屏")
                    else if (promoItems.isEmpty()) showStatus("暂无可播放素材", "请在后台配置图片、视频或员工展示资料")
                    else playCurrentPromo()
                }
            } catch (error: Exception) {
                Log.e(TAG, "load promo failed", error)
                mainHandler.post { showStatus("宣传大屏暂不可用", error.message ?: "同步失败") }
            }
        }
    }

    private fun playCurrentPromo() {
        hideStatus()
        exoPlayer?.stop()
        promoPanel.removeAllViews()
        if (promoItems.isEmpty()) return
        val item = promoItems[currentPromoIndex % promoItems.size]
        if (!item.isPlayable()) {
            recordPromo(item, "failed", 0, "素材未缓存或文件不存在")
            nextPromo()
            return
        }
        when (item.type) {
            "video" -> playVideo(item)
            "staff" -> showStaff(item)
            else -> showImage(item)
        }
    }

    private fun nextPromo() {
        if (currentScene != Scene.PROMO || promoItems.isEmpty()) return
        currentPromoIndex = (currentPromoIndex + 1) % promoItems.size
        playCurrentPromo()
    }

    private fun showImage(item: PromoItem) {
        val file = item.readyFile
        if (file == null || !file.exists()) {
            recordPromo(item, "failed", 0, "图片素材未缓存")
            return nextPromo()
        }
        val image = ImageView(this).apply {
            setBackgroundColor(Color.BLACK)
            scaleType = ImageView.ScaleType.FIT_CENTER
            setImageURI(Uri.fromFile(file))
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        }
        promoPanel.addView(image)
        fadeIn(image)
        recordPromo(item, "success", item.durationSeconds)
        mainHandler.postDelayed({ nextPromo() }, item.durationSeconds * 1000L)
    }

    private fun showStaff(item: PromoItem) {
        val staff = item.staff ?: return nextPromo()
        val staffView = staffCardView()
        staffView.loadDataWithBaseURL("file:///", staffCardHtml(staff), "text/html", "UTF-8", null)
        promoPanel.addView(staffView)
        fadeIn(staffView)
        recordPromo(item, "success", item.durationSeconds)
        mainHandler.postDelayed({ nextPromo() }, item.durationSeconds * 1000L)
    }

    private fun staffCardView(): WebView {
        return staffCardWebView ?: WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            setBackgroundColor(Color.TRANSPARENT)
            settings.javaScriptEnabled = false
            settings.domStorageEnabled = false
            settings.allowFileAccess = true
            settings.allowContentAccess = true
            settings.loadWithOverviewMode = true
            settings.useWideViewPort = true
            staffCardWebView = this
        }
    }

    private fun staffCardHtml(staff: PromoStaff): String {
        val avatar = staff.readyAvatar?.takeIf { it.exists() }?.toURI()?.toString()
        val avatarHtml = if (avatar != null) {
            """<img src="${htmlEscape(avatar)}" alt="">"""
        } else {
            """<div class="avatar-fallback">${htmlEscape(staff.displayName.take(1))}</div>"""
        }
        val role = staff.roleTitle?.takeIf { it.isNotBlank() }?.let { """<span class="role">${htmlEscape(it)}</span>""" }.orEmpty()
        val specialties = tagsHtml(staff.specialties, "specialty")
        val tags = tagsHtml(staff.publicTags.ifEmpty { listOf("暂无标签") }, "tag")
        val slogan = htmlEscape(staff.serviceSlogan ?: "用真诚连接彼此，用专业守护每一次相遇。")
        return """
            <!doctype html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
              <style>
                * { box-sizing: border-box; }
                html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
                body {
                  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
                  background: linear-gradient(90deg, rgba(255,255,255,.98) 0%, rgba(255,255,255,.94) 42%, rgba(255,246,248,.86) 100%), #f8fafc;
                  color: #20252d;
                }
                .card {
                  width: 100vw;
                  height: 100vh;
                  display: grid;
                  grid-template-columns: 43vw minmax(0, 1fr);
                  gap: 4vw;
                  padding-right: 4vw;
                }
                .photo { width: 100%; height: 100vh; overflow: hidden; background: #e5e7eb; }
                .photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
                .avatar-fallback {
                  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
                  color: #94a3b8; font-size: 12vw; font-weight: 900;
                }
                .info {
                  min-width: 0;
                  height: 100vh;
                  display: grid;
                  grid-template-rows: 27vh 18vh 15vh 1fr;
                  padding: 6vh 0;
                }
                .kicker {
                  color: #8c97a8;
                  font-size: clamp(9px, 1.05vw, 22px);
                  font-weight: 900;
                  letter-spacing: .22em;
                }
                .header { display: flex; align-items: flex-end; gap: 1.1vw; margin-top: 1.4vh; }
                h1 {
                  margin: 0;
                  max-width: 70%;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                  font-size: clamp(30px, 5.6vw, 112px);
                  line-height: .98;
                  font-weight: 950;
                }
                .role {
                  flex: 0 0 auto;
                  margin-bottom: .7vh;
                  border-radius: 6px;
                  background: #2f3744;
                  color: white;
                  padding: .75vh 1vw;
                  font-size: clamp(11px, 1.2vw, 26px);
                  font-weight: 800;
                }
                .subtitle { margin-top: 2vh; color: #697386; font-size: clamp(13px, 1.65vw, 34px); }
                .subtitle strong { color: #ff5876; font-size: 1.18em; }
                .line { height: 1px; margin-top: 3vh; background: linear-gradient(90deg, rgba(255,88,118,.5), rgba(148,163,184,.15)); }
                .section { min-width: 0; overflow: hidden; }
                .title { color: #2f3744; font-size: clamp(14px, 1.55vw, 32px); font-weight: 900; margin-bottom: 1.3vh; }
                .tags { display: flex; flex-wrap: wrap; gap: 1vh .85vw; overflow: hidden; max-height: 10vh; }
                .tags span {
                  min-width: 0;
                  max-width: 31%;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                  border-radius: 5px;
                  padding: .8vh .95vw;
                  font-size: clamp(11px, 1.22vw, 26px);
                  line-height: 1.15;
                  font-weight: 850;
                }
                .specialty { background: #fff0f3; color: #ff5876; }
                .tag-0 { background: #ffe7ed; color: #df6270; }
                .tag-1 { background: #fff0dc; color: #d89142; }
                .tag-2 { background: #e9f8ec; color: #4fa765; }
                .tag-3 { background: #fff1f4; color: #d65b6a; }
                .tag-4 { background: #fff3df; color: #de8a3f; }
                .slogan {
                  min-height: 0;
                  border-radius: 8px;
                  background: #f4f6f9;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  padding: 2.5vh 3vw;
                }
                .slogan p {
                  margin: 0;
                  color: #2f3744;
                  font-size: clamp(14px, 1.8vw, 38px);
                  line-height: 1.48;
                  text-align: center;
                  white-space: pre-line;
                }
              </style>
            </head>
            <body>
              <article class="card">
                <div class="photo">$avatarHtml</div>
                <div class="info">
                  <section>
                    <div class="kicker">MATCHMAKER PROFILE</div>
                    <div class="header"><h1>${htmlEscape(staff.displayName)}</h1>$role</div>
                    <div class="subtitle">专注婚恋服务 <strong>${staff.yearsExperience ?: "-"}</strong> 年</div>
                    <div class="line"></div>
                  </section>
                  <section class="section">
                    <div class="title">擅长方向</div>
                    <div class="tags">$specialties</div>
                  </section>
                  <section class="section">
                    <div class="title">服务标签</div>
                    <div class="tags">$tags</div>
                  </section>
                  <section class="slogan"><p>$slogan</p></section>
                </div>
              </article>
            </body>
            </html>
        """.trimIndent()
    }

    private fun tagsHtml(values: List<String>, kind: String): String {
        return values.take(6).mapIndexed { index, value ->
            val klass = if (kind == "specialty") "specialty" else "tag-${index % 5}"
            """<span class="$klass">${htmlEscape(value)}</span>"""
        }.joinToString("")
    }

    private fun htmlEscape(value: String): String {
        return value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("'", "&#39;")
    }

    private fun sectionTitle(label: String, uiScale: Float): TextView {
        return TextView(this).apply {
            text = label
            setTextSize(TypedValue.COMPLEX_UNIT_PX, (40f * uiScale).coerceAtLeast(14f))
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(47, 55, 68))
            setPadding(0, 0, 0, (10 * uiScale).toInt())
        }
    }

    private fun tagRow(values: List<String>, primary: Boolean, uiScale: Float, columns: Int, cellWidth: Int): GridLayout {
        return GridLayout(this).apply {
            columnCount = columns
            rowCount = 2
            val maxTags = columns * 2
            values.take(maxTags).forEachIndexed { index, value ->
                val (bg, fg) = if (primary) {
                    Color.rgb(255, 240, 243) to Color.rgb(255, 88, 118)
                } else {
                    tagPalette(index)
                }
                addView(tagText(value, bg, fg, uiScale).apply {
                    layoutParams = GridLayout.LayoutParams().apply {
                        width = cellWidth
                        height = (48 * uiScale).toInt().coerceAtLeast(24)
                        setMargins(0, 0, (12 * uiScale).toInt(), (8 * uiScale).toInt())
                    }
                })
            }
        }
    }

    private fun tagText(value: String, bgColor: Int, textColor: Int, uiScale: Float = 1f): TextView {
        return TextView(this).apply {
            text = value
            setTextSize(TypedValue.COMPLEX_UNIT_PX, (32f * uiScale).coerceAtLeast(12f))
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
            setTextColor(textColor)
            setPadding((14 * uiScale).toInt(), (6 * uiScale).toInt(), (14 * uiScale).toInt(), (6 * uiScale).toInt())
            background = roundRect(bgColor, 7f)
        }
    }

    private fun tvUiScale(): Float {
        val metrics = resources.displayMetrics
        return minOf(metrics.widthPixels / 1920f, metrics.heightPixels / 1080f).coerceIn(0.48f, 1.15f)
    }

    private fun tagPalette(index: Int): Pair<Int, Int> {
        return when (index % 5) {
            0 -> Color.rgb(255, 231, 237) to Color.rgb(223, 98, 112)
            1 -> Color.rgb(255, 240, 220) to Color.rgb(216, 145, 66)
            2 -> Color.rgb(233, 248, 236) to Color.rgb(79, 167, 101)
            3 -> Color.rgb(255, 241, 244) to Color.rgb(214, 91, 106)
            else -> Color.rgb(255, 243, 223) to Color.rgb(222, 138, 63)
        }
    }

    private fun roundRect(color: Int, radius: Float): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color)
            cornerRadius = radius
        }
    }

    private fun fadeIn(view: View) {
        view.startAnimation(AlphaAnimation(0f, 1f).apply {
            duration = 520
            interpolator = DecelerateInterpolator()
        })
    }

    private fun playVideo(item: PromoItem) {
        val file = item.readyFile
        if (file == null || !file.exists()) {
            recordPromo(item, "failed", 0, "视频素材未缓存")
            return nextPromo()
        }
        Log.i(TAG, "play local promo video item=${item.id} path=${file.absolutePath} size=${file.length()}")
        val player = exoPlayer ?: ExoPlayer.Builder(this).build().also { exoPlayer = it }
        playerView = PlayerView(this).apply {
            useController = false
            this.player = player
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        }
        promoPanel.addView(playerView)
        player.setMediaItem(MediaItem.fromUri(Uri.fromFile(file)))
        player.prepare()
        player.play()
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) {
                    player.removeListener(this)
                    recordPromo(item, "success", max(0, (player.duration / 1000).toInt()))
                    nextPromo()
                }
            }
        })
    }

    private fun showLoading(message: String) {
        promoPanel.removeAllViews()
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.rgb(18, 20, 24))
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        }
        box.addView(ProgressBar(this))
        box.addView(TextView(this).apply {
            text = message
            textSize = 24f
            setTextColor(Color.WHITE)
            setPadding(0, 24, 0, 0)
        })
        promoPanel.addView(box)
    }

    private fun parsePromoItems(array: JSONArray): List<PromoItem> {
        val result = mutableListOf<PromoItem>()
        for (index in 0 until array.length()) {
            val obj = array.getJSONObject(index)
            val type = obj.optString("type", obj.optString("item_type"))
            val staffObj = obj.optJSONObject("staff")
            val staff = staffObj?.let { PromoStaff.fromJson(it) }
            result.add(
                PromoItem(
                    id = obj.optInt("id"),
                    type = type,
                    title = obj.optString("title"),
                    fileUrl = obj.optString("file_url").takeIf { it.isNotBlank() && it != "null" },
                    coverUrl = obj.optString("cover_url").takeIf { it.isNotBlank() && it != "null" },
                    fileHash = obj.optString("file_hash").takeIf { it.isNotBlank() && it != "null" },
                    fileSize = obj.optLong("file_size").takeIf { it > 0L },
                    version = max(1, obj.optInt("version", 1)),
                    durationSeconds = max(1, obj.optInt("duration_seconds", if (type == "staff") promoConfig.staffDurationSeconds else promoConfig.imageDurationSeconds)),
                    staff = staff
                )
            )
        }
        return result
    }

    private fun cacheCurrentPlaylist(items: List<PromoItem>, token: String) {
        val cacheDir = File(filesDir, "screen_cache").apply { mkdirs() }
        val activeNames = mutableSetOf<String>()
        for (item in items) {
            if (item.type == "staff") {
                item.staff?.avatarUrl?.let { url ->
                    item.staff.readyAvatar = cacheFile(cacheDir, "staff_${item.id}_${item.version}", url, item.fileHash, null, token, item.id, item.version)
                    activeNames.add(item.staff.readyAvatar?.name.orEmpty())
                }
                continue
            }
            val url = item.fileUrl ?: continue
            val expectedSize = if (item.type == "video") item.fileSize else null
            item.readyFile = cacheFile(cacheDir, "material_${item.id}_${item.version}", url, item.fileHash, expectedSize, token, item.id, item.version)
            activeNames.add(item.readyFile?.name.orEmpty())
        }
        cacheDir.listFiles()?.forEach { file ->
            if (!file.name.endsWith(".download") && file.name !in activeNames) file.delete()
        }
    }

    private fun cacheFile(cacheDir: File, baseName: String, sourceUrl: String, fileHash: String?, fileSize: Long?, token: String, itemId: Int, version: Int): File? {
        val ext = extensionOf(sourceUrl)
        val target = File(cacheDir, "$baseName$ext")
        if (target.exists() && verifyFile(target, fileHash, fileSize)) {
            Log.i(TAG, "cache hit item=$itemId path=${target.absolutePath} size=${target.length()}")
            reportCache(token, itemId, version, "cached", target.absolutePath, target.length(), null)
            return target
        }
        if (!hasCacheSpace(cacheDir)) {
            reportCache(token, itemId, version, "space_not_enough", target.absolutePath, 0, "缓存空间不足")
            return null
        }
        val tmp = File(cacheDir, "$baseName$ext.download")
        repeat(DOWNLOAD_RETRY) { attempt ->
            try {
                reportCache(token, itemId, version, "downloading", target.absolutePath, tmp.length(), null)
                downloadToFile(sourceUrl, tmp)
                if (!verifyFile(tmp, fileHash, fileSize)) throw IllegalStateException("素材校验失败")
                if (target.exists()) target.delete()
                tmp.renameTo(target)
                Log.i(TAG, "cache downloaded item=$itemId path=${target.absolutePath} size=${target.length()}")
                reportCache(token, itemId, version, "cached", target.absolutePath, target.length(), null)
                return target
            } catch (error: Exception) {
                Log.w(TAG, "download failed item=$itemId attempt=${attempt + 1}", error)
                if (attempt == DOWNLOAD_RETRY - 1) {
                    reportCache(token, itemId, version, "failed", target.absolutePath, tmp.length(), error.message)
                }
            }
        }
        return null
    }

    private fun downloadToFile(sourceUrl: String, target: File) {
        val conn = (URL(sourceUrl).openConnection() as HttpURLConnection).apply {
            connectTimeout = HTTP_TIMEOUT_MS
            readTimeout = HTTP_TIMEOUT_MS
        }
        conn.inputStream.use { input ->
            FileOutputStream(target).use { output ->
                input.copyTo(output)
            }
        }
    }

    private fun verifyFile(file: File, hash: String?, fileSize: Long?): Boolean {
        if (!file.exists() || file.length() <= 0) return false
        if (!hash.isNullOrBlank() && hash.length == 64) return sha256(file).equals(hash, ignoreCase = true)
        return fileSize == null || file.length() == fileSize
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun hasCacheSpace(cacheDir: File): Boolean {
        val limitBytes = promoConfig.cacheLimitGb * 1024L * 1024L * 1024L
        val used = cacheDir.walkTopDown().filter { it.isFile }.sumOf { it.length() }
        return used < limitBytes && cacheDir.usableSpace > 256L * 1024L * 1024L
    }

    private fun extensionOf(url: String): String {
        val path = Uri.parse(url).path.orEmpty().lowercase(Locale.ROOT)
        return when {
            path.endsWith(".mp4") -> ".mp4"
            path.endsWith(".webp") -> ".webp"
            path.endsWith(".png") -> ".png"
            else -> ".jpg"
        }
    }

    private fun retryCurrentScene() {
        keepFullscreen()
        when (currentScene) {
            Scene.USER_WALL -> openUserWall()
            Scene.PROMO -> loadPromo()
            Scene.SELECT -> showSceneSelect()
        }
    }

    private fun showSettingsDialog() {
        if (!BuildConfig.DEBUG_PANEL_ENABLED || settingsDialog?.isShowing == true) return
        val dialog = Dialog(this)
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(36, 30, 36, 30)
            setBackgroundColor(Color.rgb(245, 246, 248))
        }
        val title = TextView(this).apply {
            text = "大屏设置"
            textSize = 26f
            setTextColor(Color.rgb(34, 38, 44))
            setPadding(0, 0, 0, 18)
        }
        val urlInput = EditText(this).apply {
            setSingleLine(true)
            textSize = 18f
            setText(serverUrl())
            hint = "http://10.0.2.2:5180/web"
        }
        val buttonRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, 24, 0, 0)
        }
        val save = settingButton("保存") {
            val nextUrl = urlInput.text?.toString()?.trim().orEmpty()
            if (nextUrl.isBlank()) {
                Toast.makeText(this, "请输入服务器地址", Toast.LENGTH_SHORT).show()
                return@settingButton
            }
            prefs.edit().putString(KEY_SCREEN_URL, normalizeServerUrl(nextUrl)).apply()
            dialog.dismiss()
            showSceneSelect()
        }
        val reload = settingButton("重载") {
            dialog.dismiss()
            retryCurrentScene()
        }
        val clearToken = settingButton("清除绑定") {
            clearScreenToken()
            dialog.dismiss()
        }
        val clearCache = settingButton("清缓存") {
            clearWebData()
            clearPromoCache()
            dialog.dismiss()
            showSceneSelect()
        }
        val close = settingButton("关闭") { dialog.dismiss() }
        listOf(save, reload, clearToken, clearCache, close).forEach { buttonRow.addView(it) }
        container.addView(title)
        container.addView(urlInput)
        container.addView(buttonRow)
        dialog.setContentView(container)
        dialog.setOnDismissListener {
            settingsDialog = null
            keepFullscreen()
        }
        settingsDialog = dialog
        dialog.show()
        dialog.window?.setLayout((resources.displayMetrics.widthPixels * 0.72).toInt(), ViewGroup.LayoutParams.WRAP_CONTENT)
        urlInput.requestFocus()
    }

    private fun settingButton(label: String, action: () -> Unit): Button {
        return Button(this).apply {
            text = label
            textSize = 18f
            isAllCaps = false
            setOnClickListener { action() }
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(6, 0, 6, 0) }
        }
    }

    private fun clearScreenToken() {
        prefs.edit().remove(KEY_DEVICE_TOKEN).apply()
        webView.evaluateJavascript("try{localStorage.removeItem('screen_device_token');localStorage.removeItem('screen_bootstrap_info');}catch(e){}", null)
        Toast.makeText(this, "绑定信息已清除", Toast.LENGTH_SHORT).show()
    }

    private fun clearWebData() {
        webView.clearCache(true)
        webView.clearHistory()
        WebStorage.getInstance().deleteAllData()
        CookieManager.getInstance().removeAllCookies(null)
        CookieManager.getInstance().flush()
    }

    private fun clearPromoCache() {
        File(filesDir, "screen_cache").deleteRecursively()
        Toast.makeText(this, "缓存已清除", Toast.LENGTH_SHORT).show()
    }

    private fun syncTokenToWebView() {
        val token = deviceToken()
        if (token.isNotBlank()) {
            webView.evaluateJavascript("try{localStorage.setItem('screen_device_token', ${JSONObject.quote(token)});}catch(e){}", null)
        } else {
            pullTokenFromWebView()
        }
    }

    private fun pullTokenFromWebView(afterPull: (() -> Unit)? = null) {
        webView.evaluateJavascript("try{localStorage.getItem('screen_device_token')}catch(e){''}") { value ->
            val clean = value.trim().trim('"')
            if (clean.isNotBlank() && clean != "null") prefs.edit().putString(KEY_DEVICE_TOKEN, clean).apply()
            afterPull?.invoke()
        }
    }

    inner class TokenBridge {
        @JavascriptInterface
        fun saveDeviceToken(token: String?) {
            val clean = token?.trim().orEmpty()
            if (clean.isBlank()) return
            prefs.edit().putString(KEY_DEVICE_TOKEN, clean).apply()
            Log.i(TAG, "device token synced from web")
        }

        @JavascriptInterface
        fun clearDeviceToken() {
            prefs.edit().remove(KEY_DEVICE_TOKEN).apply()
            Log.i(TAG, "device token cleared from web")
        }
    }

    private fun showStatus(title: String, message: String) {
        statusTitle.text = title
        statusMessage.text = "$message\n\n按 OK 重试，按 上上下下左右左右OK 打开设置"
        statusPanel.visibility = View.VISIBLE
        statusPanel.requestFocus()
    }

    private fun hideStatus() {
        statusPanel.visibility = View.GONE
    }

    private fun isNetworkAvailable(): Boolean {
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = manager.activeNetwork ?: return false
            val capabilities = manager.getNetworkCapabilities(network) ?: return false
            return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
        }
        @Suppress("DEPRECATION")
        return manager.activeNetworkInfo?.isConnected == true
    }

    private fun keepFullscreen() {
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.decorView.post {
                window.insetsController?.let {
                    it.hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                    it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                }
            }
        }
    }

    private fun serverUrl(): String {
        return prefs.getString(KEY_SCREEN_URL, normalizeServerUrl(BuildConfig.DEFAULT_SCREEN_URL)) ?: normalizeServerUrl(BuildConfig.DEFAULT_SCREEN_URL)
    }

    private fun normalizeServerUrl(value: String): String {
        val base = value.substringBefore("#").trimEnd('/')
        return base
    }

    private fun userWallUrl(): String = "${serverUrl()}#/screen/player"

    private fun apiBaseUrl(): String {
        val uri = Uri.parse(serverUrl())
        val basePath = uri.path.orEmpty().trimEnd('/')
        val origin = "${uri.scheme}://${uri.authority}"
        return if (basePath.endsWith("/api/v1")) "$origin$basePath" else "$origin/api/v1"
    }

    private fun deviceToken(): String = prefs.getString(KEY_DEVICE_TOKEN, "") ?: ""

    private fun httpJson(method: String, url: String, token: String, body: JSONObject? = null): JSONObject {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = HTTP_TIMEOUT_MS
            readTimeout = HTTP_TIMEOUT_MS
            setRequestProperty("Authorization", "ScreenDevice $token")
            setRequestProperty("Content-Type", "application/json")
            if (body != null) doOutput = true
        }
        if (body != null) conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        if (conn.responseCode !in 200..299) throw IllegalStateException(text.ifBlank { "HTTP ${conn.responseCode}" })
        return JSONObject(text)
    }

    private fun reportCache(token: String, itemId: Int, version: Int, status: String, localPath: String?, downloadedBytes: Long?, error: String?) {
        runCatching {
            httpJson(
                "POST",
                "${apiBaseUrl()}/screen/player/promo/cache-report",
                token,
                JSONObject()
                    .put("item_id", itemId)
                    .put("version", version)
                    .put("cache_status", status)
                    .put("local_path", localPath)
                    .put("downloaded_bytes", downloadedBytes)
                    .put("error_message", error)
            )
        }
    }

    private fun recordPromo(item: PromoItem, result: String, durationSeconds: Int, errorMessage: String? = null) {
        val token = deviceToken()
        if (token.isBlank()) return
        ioExecutor.execute {
            runCatching {
                httpJson(
                    "POST",
                    "${apiBaseUrl()}/screen/player/promo/record",
                    token,
                    JSONObject()
                        .put("item_id", item.id)
                        .put("item_type", item.type)
                        .put("play_result", result)
                        .put("duration_seconds", durationSeconds)
                        .put("error_message", errorMessage)
                )
            }
        }
    }

    private fun normalizeOk(keyCode: Int): Int {
        return if (keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER) KeyEvent.KEYCODE_DPAD_CENTER else keyCode
    }

    private fun handleSettingsShortcut(keyCode: Int): Boolean {
        val shortcut = intArrayOf(
            KeyEvent.KEYCODE_DPAD_UP,
            KeyEvent.KEYCODE_DPAD_UP,
            KeyEvent.KEYCODE_DPAD_DOWN,
            KeyEvent.KEYCODE_DPAD_DOWN,
            KeyEvent.KEYCODE_DPAD_LEFT,
            KeyEvent.KEYCODE_DPAD_RIGHT,
            KeyEvent.KEYCODE_DPAD_LEFT,
            KeyEvent.KEYCODE_DPAD_RIGHT,
            KeyEvent.KEYCODE_DPAD_CENTER
        )
        settingsKeyBuffer.addLast(keyCode)
        while (settingsKeyBuffer.size > shortcut.size) settingsKeyBuffer.removeFirst()
        val matched = settingsKeyBuffer.size == shortcut.size && settingsKeyBuffer.toList().toIntArray().contentEquals(shortcut)
        if (matched) {
            settingsKeyBuffer.clear()
            showSettingsDialog()
        }
        return matched
    }

    private fun logKeyEvent(stage: String, keyCode: Int, event: KeyEvent) {
        Log.d(TAG, "$stage keyCode=$keyCode keyName=${KeyEvent.keyCodeToString(keyCode)} action=${event.action} repeat=${event.repeatCount} scanCode=${event.scanCode}")
    }

    private enum class Scene { SELECT, USER_WALL, PROMO }

    private data class PromoConfig(
        val enabled: Boolean = true,
        val imageDurationSeconds: Int = 8,
        val staffDurationSeconds: Int = 12,
        val syncIntervalSeconds: Int = 60,
        val cacheLimitGb: Int = 20
    ) {
        companion object {
            fun fromJson(obj: JSONObject): PromoConfig = PromoConfig(
                enabled = obj.optBoolean("enabled", true),
                imageDurationSeconds = obj.optInt("image_duration_seconds", 8),
                staffDurationSeconds = obj.optInt("staff_duration_seconds", 12),
                syncIntervalSeconds = obj.optInt("sync_interval_seconds", 60),
                cacheLimitGb = obj.optInt("cache_limit_gb", 20)
            )
        }
    }

    private data class PromoItem(
        val id: Int,
        val type: String,
        val title: String,
        val fileUrl: String?,
        val coverUrl: String?,
        val fileHash: String?,
        val fileSize: Long?,
        val version: Int,
        val durationSeconds: Int,
        val staff: PromoStaff?,
        var readyFile: File? = null
    ) {
        fun isPlayable(): Boolean {
            return when (type) {
                "staff" -> staff != null
                "image", "video" -> readyFile?.exists() == true
                else -> false
            }
        }
    }

    private data class PromoStaff(
        val avatarUrl: String?,
        val displayName: String,
        val roleTitle: String?,
        val yearsExperience: Int?,
        val specialties: List<String>,
        val serviceSlogan: String?,
        val publicTags: List<String>,
        var readyAvatar: File? = null
    ) {
        companion object {
            fun fromJson(obj: JSONObject): PromoStaff {
                val tags = mutableListOf<String>()
                val arr = obj.optJSONArray("public_tags") ?: JSONArray()
                for (index in 0 until arr.length()) tags.add(arr.optString(index))
                val specialties = mutableListOf<String>()
                val specialtiesArr = obj.optJSONArray("specialties")
                if (specialtiesArr != null) {
                    for (index in 0 until specialtiesArr.length()) specialties.add(specialtiesArr.optString(index))
                } else {
                    obj.optString("specialties").split("、", ",", "，", ";", "；").map { it.trim() }.filter { it.isNotBlank() && it != "null" }.forEach { specialties.add(it) }
                }
                return PromoStaff(
                    avatarUrl = obj.optString("avatar_url").takeIf { it.isNotBlank() && it != "null" },
                    displayName = obj.optString("display_name", "员工"),
                    roleTitle = obj.optString("role_title").takeIf { it.isNotBlank() && it != "null" },
                    yearsExperience = obj.optInt("years_experience").takeIf { it > 0 },
                    specialties = specialties,
                    serviceSlogan = obj.optString("service_slogan").takeIf { it.isNotBlank() && it != "null" },
                    publicTags = tags
                )
            }
        }
    }

    companion object {
        private const val TAG = "MiaiTvShell"
        private const val PREFS_NAME = "miai_tv_settings"
        private const val KEY_SCREEN_URL = "screen_url"
        private const val KEY_LAST_LOADED_URL = "last_loaded_url"
        private const val KEY_DEVICE_TOKEN = "screen_device_token"
        private const val BACK_EXIT_INTERVAL_MS = 2000L
        private const val HTTP_TIMEOUT_MS = 30000
        private const val DOWNLOAD_RETRY = 3
    }
}
