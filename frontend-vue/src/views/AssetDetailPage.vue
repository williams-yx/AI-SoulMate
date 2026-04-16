<template>
  <div class="asset-detail-container">
    <!-- 图片预览弹窗 -->
    <div
      v-if="imagePreviewUrl"
      class="image-preview-overlay"
      @click.self="closeImagePreview"
    >
      <div class="image-preview-dialog">
        <button
          class="image-preview-close-btn"
          type="button"
          @click="closeImagePreview"
        >
          ×
        </button>
        <img :src="imagePreviewUrl" :alt="t('assetDetail.previewImageAlt')" class="image-preview-img" />
      </div>
    </div>
    <!-- 确认删除评论对话框 -->
    <ConfirmDialog
      v-model:open="deleteCommentDialogOpen"
      :title="t('assetDetail.deleteCommentTitle')"
      :message="t('assetDetail.deleteCommentMessage')"
      :confirm-text="t('assetDetail.delete')"
      :cancel-text="t('assetDetail.cancel')"
      @confirm="confirmDeleteComment"
    />

    <!-- 确认删除作品对话框 -->
    <ConfirmDialog
      v-model:open="deleteAssetDialogOpen"
      :title="t('assetDetail.deleteAssetTitle')"
      :message="t('assetDetail.deleteAssetMessage')"
      :confirm-text="t('assetDetail.delete')"
      :cancel-text="t('assetDetail.cancel')"
      @confirm="confirmDeleteAsset"
    />

    <!-- 请先登录提示弹窗（点赞 / 一键打印等） -->
    <LoginPromptModal
      v-model:open="loginPromptOpen"
      :message="t(loginPromptMessage)"
      @goLogin="loginPromptOpen = false"
    />

    <!-- 一键打印：确认下单 -->
    <div
      v-if="printConfirmOpen"
      class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center"
      @click.self="printConfirmOpen = false"
    >
      <div class="glass-panel max-w-md w-full mx-auto rounded-2xl p-6 border border-slate-700 shadow-2xl">
        <div class="flex items-center justify-between gap-4">
          <h3 class="text-lg font-bold text-white">{{ t('assetDetail.printConfirmTitle') }}</h3>
          <button
            class="text-slate-400 transition hover:text-white"
            type="button"
            @click="printConfirmOpen = false"
          >
            ×
          </button>
        </div>
        <p class="mt-3 text-slate-300">{{ t('assetDetail.printConfirmMessage') }}</p>

        <div class="mt-5 space-y-2">
          <label class="text-sm font-bold text-slate-200">{{ t('assetDetail.printHeightLabel') }}</label>
          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              class="rounded-lg border px-4 py-3 text-sm font-semibold transition"
              :class="printHeight === '5cm' ? 'border-indigo-500 bg-indigo-500/20 text-indigo-200' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
              @click="printHeight = '5cm'"
            >
              5cm
            </button>
            <button
              type="button"
              class="rounded-lg border px-4 py-3 text-sm font-semibold transition"
              :class="printHeight === '10cm' ? 'border-indigo-500 bg-indigo-500/20 text-indigo-200' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
              @click="printHeight = '10cm'"
            >
              10cm
            </button>
          </div>
          <p class="text-xs text-slate-500">{{ t('assetDetail.printHeightHint') }}</p>
        </div>

        <div class="mt-6 flex items-center justify-end gap-3">
          <button
            class="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-700"
            type="button"
            @click="printConfirmOpen = false"
          >
            {{ t('assetDetail.cancel') }}
          </button>
          <button
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            :disabled="printing"
            @click="submitPrintJob"
          >
            {{ printing ? t('assetDetail.printSubmitting') : t('assetDetail.confirm') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 一键打印：提交成功/失败提示 -->
    <ConfirmDialog
      v-model:open="printSuccessOpen"
      :title="t(printSuccessTitle)"
      :message="printSuccessMessageDisplay"
      :confirm-text="t('assetDetail.ok')"
      single-button
      @confirm="printSuccessOpen = false"
    />

    <!-- 图片数量超限提示 -->
    <ConfirmDialog
      v-model:open="imageLimitDialogOpen"
      :title="t('assetDetail.tipTitle')"
      :message="t(imageLimitDialogMessage)"
      :confirm-text="t('assetDetail.okGotIt')"
      single-button
      @confirm="imageLimitDialogOpen = false"
    />

    <div v-if="loading" class="asset-detail-loading">{{ t('assetDetail.loading') }}</div>
    <div v-else-if="error" class="asset-detail-error">{{ error }}</div>

    <div v-else-if="asset" class="asset-detail-content">
      <!-- 作品预览图区 -->
      <section class="asset-preview-section">
        <button class="asset-back-btn" type="button" @click="router.push('/community')">
          {{ t('assetDetail.backCommunity') }}
        </button>
        <div class="asset-preview-wrapper">
          <!-- 3D 容器始终存在，只是根据条件显示/隐藏 -->
          <div
            v-if="show3DHint && canShow3D && !viewerLoadFailed && !viewerLoading"
            class="asset-3d-hint-pill"
          >
            {{ t('assetDetail.rotate3dHint') }}
          </div>
          <div
            ref="viewerContainer"
            class="asset-3d-viewer"
            v-show="canShow3D && !viewerLoadFailed"
          ></div>
          <!-- 自定义 3D 加载遮罩 -->
          <div
            v-if="viewerLoading && !viewerLoadFailed && canShow3D"
            class="asset-3d-loading-mask"
          >
            <div class="asset-3d-loading-spinner"></div>
            <p class="asset-3d-loading-text">{{ t('assetDetail.modelLoading') }}</p>
          </div>
          <!-- 回退图片也用 v-show，避免和上面互相抢 DOM -->
          <img
            v-show="!canShow3D || viewerLoadFailed"
            :src="resolveImageUrl(asset.image_url)"
            class="asset-preview-image"
            :alt="asset.prompt"
            @error="handlePreviewError"
          />
        </div>
      </section>

      <!-- 作品信息区 -->
      <section class="asset-info-section">
        <div class="asset-info-header">
          <h1 class="asset-detail-title">{{ t('assetDetail.pageTitle') }}</h1>
          <div class="asset-info-actions">
            <button
              class="asset-stat-badge asset-stat-btn asset-stat-download"
              type="button"
              @click="download"
              :title="t('assetDetail.downloadTitle')"
            >
              <svg class="asset-stat-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span class="asset-stat-value">{{ asset.stats?.downloads || 0 }}</span>
            </button>
            <button
              class="asset-stat-badge asset-stat-btn asset-stat-like"
              type="button"
              :class="{ 'asset-stat-like-active': liked }"
              @click="like"
              :title="t('assetDetail.likeTitle')"
            >
              <svg class="asset-stat-icon" fill="currentColor" viewBox="0 0 20 20">
                <path
                  d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"
                />
              </svg>
              <span class="asset-stat-value">{{ asset.stats?.likes || 0 }}</span>
            </button>
            <button
              v-if="auth.isAuthed && auth.user?.id && asset.author_id && String(auth.user.id) === String(asset.author_id)"
              class="asset-delete-btn"
              type="button"
              @click="handleDelete"
              :title="t('assetDetail.deleteWorkTitle')"
            >
              {{ t('assetDetail.delete') }}
            </button>
          </div>
        </div>

        <div class="asset-author-row">
          <!--
          <img
            :src="asset.author_avatar || '/default-avatar.png'"
            class="asset-author-avatar"
            :alt="asset.author_name"
          />
          -->
          <span class="asset-author">{{ t('assetDetail.authorPrefix') }}{{ asset.author_name || t('assetDetail.authorUnknown') }}</span>
        </div>

        <div class="asset-prompt-section">
          <div class="asset-prompt-header">
            <span class="asset-prompt-label">{{ t('assetDetail.promptLabel') }}</span>
              <button
                v-if="!isImagePrompt"
                class="asset-prompt-copy"
                type="button"
                :class="{ 'asset-prompt-copy-success': copyPromptSuccess }"
                @click="copyPrompt"
              >
                {{ copyPromptSuccess ? t('assetDetail.copied') : t('assetDetail.copy') }}
              </button>
          </div>
          <div
            v-if="asset.studio_mode === 'image23d' && asset.reference_image_url"
            class="asset-prompt-reference"
          >
            <span class="asset-prompt-reference-label">图生3D · 参考图</span>
            <div class="asset-prompt-reference-frame">
              <img
                :src="resolveImageUrl(asset.reference_image_url)"
                class="asset-prompt-reference-img"
                alt="图生3D 参考图"
                @error="handleReferenceImageError"
              />
            </div>
          </div>
          <div class="asset-prompt-content">{{ asset.prompt }}</div>
        </div>

        <div v-if="asset.tags && asset.tags.length > 0" class="asset-tags">
          <span v-for="t in asset.tags" :key="t" class="asset-tag">{{ t }}</span>
        </div>

        <div class="asset-actions">
          <button
            type="button"
            class="asset-action-btn asset-action-btn-primary"
            @click="goToStudioRemix"
          >
            {{ t('assetDetail.remix') }}
          </button>
          <button
            class="asset-action-btn asset-action-btn-print"
            type="button"
            :disabled="printing"
            @click="oneClickPrint"
          >
            {{ printing ? t('assetDetail.printSubmitting') : t('assetDetail.oneClickPrint') }}
          </button>
        </div>

        <p v-if="asset.created_at" class="asset-published">
          {{ t('assetDetail.publishedAt', { time: formatTime(asset.created_at) }) }}
        </p>
      </section>
    </div>

    <!-- 评论区 -->
    <section v-if="asset" class="comment-section">
      <h2 class="comment-section-title">{{ t('assetDetail.commentsSectionTitle', { count: commentTotal }) }}</h2>

      <!-- 评论输入区 -->
      <div v-if="auth.isAuthed" class="comment-input-area">
        <textarea
          v-model="commentContent"
          class="comment-textarea"
          :placeholder="t('assetDetail.commentPlaceholder')"
          maxlength="1000"
          @input="handleCommentInput"
        />
        <div class="comment-input-actions">
          <div class="flex items-center gap-3">
            <input
              ref="imageInput"
              type="file"
              accept="image/*"
              multiple
              class="hidden"
              @change="handleImageSelect"
            />
            <!-- 回复用：单一 file input 放在稳定位置，避免 v-if 下 ref 绑定失败 -->
            <input
              ref="replyImageInput"
              type="file"
              accept="image/*"
              multiple
              class="hidden"
              @change="handleReplyImageSelect"
            />
            <input
              ref="videoInput"
              type="file"
              accept="video/mp4,video/webm,video/quicktime"
              multiple
              class="hidden"
              @change="handleVideoSelect"
            />
            <input
              ref="replyVideoInput"
              type="file"
              accept="video/mp4,video/webm,video/quicktime"
              multiple
              class="hidden"
              @change="handleReplyVideoSelect"
            />
            <button
              class="btn-image-select"
              type="button"
              @click="triggerImageInput"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              {{ t('assetDetail.selectPhotos') }}
            </button>
            <button
              class="btn-image-select"
              type="button"
              @click="triggerVideoInput"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
              </svg>
              {{ t('assetDetail.selectVideos') }}
            </button>
            <span class="comment-image-hint">{{ t('assetDetail.mediaHint') }}</span>
          </div>
          <div class="flex items-center gap-3">
            <span class="comment-char-count" :class="{ 'comment-char-count-warning': commentCharCount >= 1000 }">
              ({{ commentCharCount }}/1000)
            </span>
            <button
              class="btn-publish"
              type="button"
              :disabled="submitting || (!commentContent.trim() && selectedImages.length === 0 && selectedVideos.length === 0) || commentCharCount > 1000"
              @click="submitComment"
            >
              {{ submitting ? t('assetDetail.publishSubmitting') : t('assetDetail.publish') }}
            </button>
          </div>
        </div>
        <!-- 已选择的图片预览 -->
        <div v-if="selectedImages.length > 0" class="comment-image-preview">
          <div
            v-for="(img, idx) in selectedImages"
            :key="idx"
            class="comment-image-item"
          >
            <img :src="img.preview" class="comment-image-preview-img" />
            <button
              class="comment-image-remove"
              type="button"
              @click="removeImage(idx)"
            >
              ×
            </button>
          </div>
        </div>
        <div v-if="selectedVideos.length > 0" class="comment-video-preview">
          <div
            v-for="(video, idx) in selectedVideos"
            :key="`comment-video-${idx}`"
            class="comment-video-item"
          >
            <video :src="video.preview" class="comment-video-preview-player" controls preload="metadata"></video>
            <div class="comment-video-name">{{ video.file.name }}</div>
            <button
              class="comment-image-remove"
              type="button"
              @click="removeVideo(idx)"
            >
              ×
            </button>
          </div>
        </div>
      </div>
      <p v-else class="comment-login-prompt">
        <button type="button" class="comment-login-link" @click="router.push('/profile')">{{ t('assetDetail.loginLink') }}</button> {{ t('assetDetail.afterLoginComment') }}
      </p>

      <!-- 排序选项 -->
      <div class="comment-sort-bar">
        <div class="text-sm text-slate-400">{{ t('assetDetail.sortAll') }}</div>
        <div class="flex items-center gap-4">
          <button
            v-for="(opt, idx) in sortOptions"
            :key="opt.value"
            class="comment-sort-btn"
            :class="{ 'comment-sort-btn-active': sortBy === opt.value }"
            type="button"
            @click="changeSort(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 评论列表 -->
      <div v-if="commentsLoading" class="comment-loading">{{ t('assetDetail.loadComments') }}</div>
      <div v-else class="comment-list">
        <div
          v-for="comment in comments"
          :key="comment.id"
          class="comment-card"
        >
          <!-- 主评论 -->
          <div class="comment-card-content">
            <!--
            <img
              :src="comment.author_avatar || '/default-avatar.png'"
              class="comment-avatar"
              :alt="comment.author_name"
            />
            -->
            <div class="comment-body">
              <div class="comment-header">
                <div class="flex items-center gap-2">
                  <span class="comment-author">{{ comment.author_name || t('assetDetail.anonymous') }}</span>
                </div>
                <button
                  v-if="auth.isAuthed && comment.author_id && String(auth.user?.id) === String(comment.author_id)"
                  class="comment-delete-btn"
                  type="button"
                  @click="deleteComment(comment.id)"
                >
                  {{ t('assetDetail.delete') }}
                </button>
              </div>
              <p class="comment-text">{{ comment.content }}</p>
              <!-- 评论图片 -->
              <div v-if="comment.images && comment.images.length > 0" class="comment-images">
                <img
                  v-for="(img, idx) in comment.images"
                  :key="idx"
                  :src="resolveImageUrl(img)"
                  class="comment-image"
                  @click="previewImage(img)"
                />
              </div>
              <div v-if="comment.videos && comment.videos.length > 0" class="comment-videos">
                <video
                  v-for="(video, idx) in comment.videos"
                  :key="`comment-video-${comment.id}-${idx}`"
                  :src="resolveImageUrl(video)"
                  class="comment-video"
                  controls
                  preload="metadata"
                ></video>
              </div>
              <div class="comment-meta-actions">
                <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
                <div class="comment-actions">
                <button
                  v-if="auth.isAuthed"
                  type="button"
                  class="comment-action-btn"
                  :class="{ 'comment-action-btn-active': comment.liked_by_me }"
                  @click="toggleCommentLike(comment)"
                >
                  <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                  </svg>
                  {{ comment.like_count || 0 }}
                </button>
                <button
                  v-if="auth.isAuthed"
                  type="button"
                  class="comment-action-btn"
                  @click="startReply(comment, comment)"
                >
                  {{ t('assetDetail.replyVerb') }}
                </button>
                </div>
              </div>

              <!-- 楼中楼回复（扁平化：所有子评论在同一层显示） -->
              <template v-if="comment.replies && comment.replies.length > 0">
                <div
                  v-for="reply in comment.replies"
                  :key="reply.id"
                  class="reply-wrapper"
                  :data-comment-id="reply.id"
                >
                  <div class="comment-card-content">
                    <!--
                    <img
                      :src="reply.author_avatar || '/default-avatar.png'"
                      class="comment-avatar"
                      :alt="reply.author_name"
                    />
                    -->
                    <div class="comment-body">
                      <div class="comment-header">
                        <div class="flex items-center gap-2">
                          <span class="comment-author">{{ reply.author_name || t('assetDetail.anonymous') }}</span>
                          <span v-if="reply.reply_to_name" class="comment-reply-to">
                            {{ t('assetDetail.replyToUser', { name: reply.reply_to_name }) }}
                          </span>
                        </div>
                        <button
                          v-if="auth.isAuthed && reply.author_id && String(auth.user?.id) === String(reply.author_id)"
                          class="comment-delete-btn"
                          type="button"
                          @click="deleteComment(reply.id)"
                        >
                          {{ t('assetDetail.delete') }}
                        </button>
                      </div>

                      <p class="comment-text">{{ reply.content }}</p>

                      <!-- 回复图片 -->
                      <div v-if="reply.images && reply.images.length > 0" class="comment-images">
                        <img
                          v-for="(img, idx) in reply.images"
                          :key="idx"
                          :src="resolveImageUrl(img)"
                          class="comment-image"
                          @click="previewImage(img)"
                        />
                      </div>
                      <div v-if="reply.videos && reply.videos.length > 0" class="comment-videos">
                        <video
                          v-for="(video, idx) in reply.videos"
                          :key="`reply-video-${reply.id}-${idx}`"
                          :src="resolveImageUrl(video)"
                          class="comment-video"
                          controls
                          preload="metadata"
                        ></video>
                      </div>

                      <div class="comment-meta-actions">
                        <span class="comment-time">{{ formatTime(reply.created_at) }}</span>
                        <div class="comment-actions">
                        <button
                          v-if="auth.isAuthed"
                          type="button"
                          class="comment-action-btn"
                          :class="{ 'comment-action-btn-active': reply.liked_by_me }"
                          @click="toggleReplyLike(comment, reply)"
                        >
                          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"
                            />
                          </svg>
                          {{ reply.like_count || 0 }}
                        </button>
                        <button
                          v-if="auth.isAuthed"
                          type="button"
                          class="comment-action-btn"
                          @click="startReply(reply, comment)"
                        >
                          {{ t('assetDetail.replyVerb') }}
                        </button>
                        </div>
                      </div>

                      <!-- 回复输入框（针对当前 reply，不再嵌套） -->
                      <div v-if="replyingTo === reply.id" class="comment-reply-input">
                        <textarea
                          v-model="replyContent"
                          class="comment-textarea comment-textarea-sm"
                          :placeholder="t('assetDetail.replyPlaceholder', { name: getReplyToUserName(reply) })"
                          maxlength="1000"
                          @input="handleReplyInput"
                        />
                        <div class="comment-reply-input-actions">
                          <div class="flex items-center gap-2">
                            <button
                              class="btn-image-select btn-image-select-sm"
                              type="button"
                              @click="triggerReplyImageInput"
                            >
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                />
                              </svg>
                              {{ t('assetDetail.selectPhotos') }}
                            </button>
                            <button
                              class="btn-image-select btn-image-select-sm"
                              type="button"
                              @click="triggerReplyVideoInput"
                            >
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
                              </svg>
                              {{ t('assetDetail.selectVideos') }}
                            </button>
                          </div>
                          <div class="flex items-center gap-2">
                            <span
                              class="comment-char-count comment-char-count-sm"
                              :class="{ 'comment-char-count-warning': replyCharCount >= 1000 }"
                            >
                              ({{ replyCharCount }}/1000)
                            </span>
                            <button
                              class="btn-cancel-sm"
                              type="button"
                              @click="cancelReply"
                            >
                              {{ t('assetDetail.cancelReply') }}
                            </button>
                            <button
                              class="btn-publish btn-publish-sm"
                              type="button"
                              :disabled="
                                submitting ||
                                (!replyContent.trim() && replyImages.length === 0 && replyVideos.length === 0) ||
                                replyCharCount > 1000
                              "
                              @click="submitReply(reply, comment)"
                            >
                              {{ submitting ? t('assetDetail.replySubmitting') : t('assetDetail.replyVerb') }}
                            </button>
                          </div>
                        </div>
                        <!-- 回复图片预览 -->
                        <div v-if="replyImages.length > 0" class="comment-image-preview">
                          <div
                            v-for="(img, idx) in replyImages"
                            :key="idx"
                            class="comment-image-item comment-image-item-sm"
                          >
                            <img
                              :src="img.preview"
                              class="comment-image-preview-img comment-image-preview-img-sm"
                            />
                            <button
                              class="comment-image-remove comment-image-remove-sm"
                              type="button"
                              @click="removeReplyImage(idx)"
                            >
                              ×
                            </button>
                          </div>
                        </div>
                        <div v-if="replyVideos.length > 0" class="comment-video-preview">
                          <div
                            v-for="(video, idx) in replyVideos"
                            :key="`reply-inline-video-${idx}`"
                            class="comment-video-item comment-video-item-sm"
                          >
                            <video :src="video.preview" class="comment-video-preview-player comment-video-preview-player-sm" controls preload="metadata"></video>
                            <div class="comment-video-name">{{ video.file.name }}</div>
                            <button
                              class="comment-image-remove comment-image-remove-sm"
                              type="button"
                              @click="removeReplyVideo(idx)"
                            >
                              ×
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 回复输入框（展开时显示） -->
              <div v-if="replyingTo === comment.id" class="comment-reply-input">
                <textarea
                  v-model="replyContent"
                  class="comment-textarea comment-textarea-sm"
                  :placeholder="t('assetDetail.replyPlaceholder', { name: getReplyToUserName(comment) })"
                  maxlength="1000"
                  @input="handleReplyInput"
                />
                <div class="comment-reply-input-actions">
                  <div class="flex items-center gap-2">
                    <button
                      class="btn-image-select btn-image-select-sm"
                      type="button"
                      @click="triggerReplyImageInput"
                    >
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {{ t('assetDetail.selectPhotos') }}
                    </button>
                    <button
                      class="btn-image-select btn-image-select-sm"
                      type="button"
                      @click="triggerReplyVideoInput"
                    >
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
                      </svg>
                      {{ t('assetDetail.selectVideos') }}
                    </button>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="comment-char-count comment-char-count-sm" :class="{ 'comment-char-count-warning': replyCharCount >= 1000 }">
                      ({{ replyCharCount }}/1000)
                    </span>
                    <button
                      class="btn-cancel-sm"
                      type="button"
                      @click="cancelReply"
                    >
                      {{ t('assetDetail.cancelReply') }}
                    </button>
                    <button
                      class="btn-publish btn-publish-sm"
                      type="button"
                      :disabled="submitting || (!replyContent.trim() && replyImages.length === 0 && replyVideos.length === 0) || replyCharCount > 1000"
                      @click="submitReply(comment, comment)"
                    >
                      {{ submitting ? t('assetDetail.replySubmitting') : t('assetDetail.replyVerb') }}
                    </button>
                  </div>
                </div>
                <!-- 回复图片预览 -->
                <div v-if="replyImages.length > 0" class="comment-image-preview">
                  <div
                    v-for="(img, idx) in replyImages"
                    :key="idx"
                    class="comment-image-item comment-image-item-sm"
                  >
                    <img :src="img.preview" class="comment-image-preview-img comment-image-preview-img-sm" />
                    <button
                      class="comment-image-remove comment-image-remove-sm"
                      type="button"
                      @click="removeReplyImage(idx)"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div v-if="replyVideos.length > 0" class="comment-video-preview">
                  <div
                    v-for="(video, idx) in replyVideos"
                    :key="`reply-root-video-${idx}`"
                    class="comment-video-item comment-video-item-sm"
                  >
                    <video :src="video.preview" class="comment-video-preview-player comment-video-preview-player-sm" controls preload="metadata"></video>
                    <div class="comment-video-name">{{ video.file.name }}</div>
                    <button
                      class="comment-image-remove comment-image-remove-sm"
                      type="button"
                      @click="removeReplyVideo(idx)"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="comments.length === 0" class="comment-empty">{{ t('assetDetail.noComments') }}</div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import * as OV from 'online-3d-viewer'
import { api, resolveMediaUrl } from '../lib/api'
import { applyEmbeddedViewerPostLoad } from '../lib/embeddedViewerSetup'
import { STUDIO_T2I_REMIX_STORAGE_KEY, type StudioT2iRemixPayload } from '../lib/studioT2iRemix'
import { useAuthStore } from '../stores/auth'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import LoginPromptModal from '../components/LoginPromptModal.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const props = defineProps<{ id: string }>()

const loading = ref(false)
const error = ref('')
const asset = ref<any>(null)
const liked = ref(false)
const comments = ref<any[]>([])
const commentsLoading = ref(false)
const commentTotal = ref(0)
const commentContent = ref('')
const replyContent = ref('')
const commentCharCount = ref(0)
const replyCharCount = ref(0)
const submitting = ref(false)
const replyingTo = ref<string | null>(null)
const sortBy = ref<'new' | 'liked' | 'replied'>('new')
const selectedImages = ref<Array<{ file: File; preview: string; url?: string }>>([])
const selectedVideos = ref<Array<{ file: File; preview: string; url?: string }>>([])
const replyImages = ref<Array<{ file: File; preview: string; url?: string }>>([])
const replyVideos = ref<Array<{ file: File; preview: string; url?: string }>>([])
const imageInput = ref<HTMLInputElement | null>(null)
const replyImageInput = ref<HTMLInputElement | null>(null)
const videoInput = ref<HTMLInputElement | null>(null)
const replyVideoInput = ref<HTMLInputElement | null>(null)
const deleteCommentDialogOpen = ref(false)
const deleteAssetDialogOpen = ref(false)
const pendingDeleteCommentId = ref<string | null>(null)
const loginPromptOpen = ref(false)
const loginPromptMessage = ref('')
const printConfirmOpen = ref(false)
const printHeight = ref<'5cm' | '10cm'>('5cm')
const printSuccessOpen = ref(false)
const printSuccessTitle = ref('')
const printSuccessMessage = ref('')
const printSuccessMessageDisplay = computed(() => {
  const v = printSuccessMessage.value
  return typeof v === 'string' && v.startsWith('assetDetail.') ? t(v) : v
})
// 图片预览
const imagePreviewUrl = ref<string | null>(null)
// 复制提示词成功反馈
const copyPromptSuccess = ref(false)
// 评论/回复图片张数限制提示
const imageLimitDialogOpen = ref(false)
const imageLimitDialogMessage = ref('')

// 3D 预览相关
const viewerContainer = ref<HTMLElement | null>(null)
const viewerLoadFailed = ref(false)
const viewerLoading = ref(false)
const show3DHint = ref(true)
let embeddedViewer: any = null
let viewerLoadTimer: number | null = null
const previewRefreshedOnce = ref(false)
const referencePreviewRefreshedOnce = ref(false)
const modelRefreshedOnce = ref(false)

function getFileExtFromUrl(url?: string | null): string {
  if (!url) return ''
  try {
    const path = (url.startsWith('/') ? url.split('?')[0] : new URL(url).pathname) || ''
    const fileName = path.split('/').filter(Boolean).pop() || ''
    const parts = fileName.split('.')
    if (parts.length > 1) {
      return parts[parts.length - 1].toLowerCase()
    }
    return ''
  } catch {
    return ''
  }
}

function isViewerRenderableFormat(modelUrl?: string | null, modelFormat?: string | null) {
  const supported = new Set(['glb', 'gltf', 'obj', 'stl', 'fbx'])
  const normalizedFormat = (modelFormat || '').toLowerCase()
  if (supported.has(normalizedFormat)) return true
  const ext = getFileExtFromUrl(modelUrl)
  return supported.has(ext)
}

const canShow3D = computed(() => {
  const a = asset.value
  if (!a || !a.model_url) return false
  return isViewerRenderableFormat(a.model_url, (a as any).model_format ?? null)
})

const isImagePrompt = computed(() => {
  const a = asset.value
  if (!a) return false
  // 优先使用后端显式字段（若存在）
  if (a.is_image_prompt !== undefined) return !!a.is_image_prompt
  if (a.studio_mode === 'image23d') return true
  if (a.reference_image_url) return true
  const p = (a.prompt ?? '').toString().trim()
  if (!p) return false
  if (p.startsWith('data:image/')) return true
  const ext = getFileExtFromUrl(p)
  if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'svg'].includes(ext)) return true
  try {
    const u = new URL(p)
    const ext2 = getFileExtFromUrl(u.href)
    if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'svg'].includes(ext2)) return true
  } catch {
    // not a URL
  }
  return false
})

function goToStudioRemix() {
  const a = asset.value
  if (!a) return
  let targetMode: 'text2image' | 'text23d' | 'image23d' = 'text2image'
  try {
    if (a.studio_mode === 'text23d' || a.studio_mode === 'image23d') {
      targetMode = a.studio_mode
    } else if (canShow3D.value) {
      // 若后端未标明 studio_mode，但有可渲染模型，默认跳转到文生3D 编辑器
      targetMode = 'text23d'
    } else {
      targetMode = 'text2image'
    }

    const payload: StudioT2iRemixPayload = {
      prompt: typeof a.prompt === 'string' ? a.prompt : '',
      mode: targetMode,
    }

    if (a.model_url) {
      payload.modelUrl = a.model_url
      payload.modelFormat = (a as any).model_format ?? null
    }

    if (targetMode === 'image23d' && a.reference_image_url) {
      payload.referenceImageUrl = a.reference_image_url
    }

    sessionStorage.setItem(STUDIO_T2I_REMIX_STORAGE_KEY, JSON.stringify(payload))
  } catch (e) {
    console.warn('studio t2i remix sessionStorage failed:', e)
  }
  router.push({ path: '/studio', query: { mode: targetMode } })
}

const sortOptions = computed(() => [
  { label: t('assetDetail.sortLiked'), value: 'liked' as const },
  { label: t('assetDetail.sortNew'), value: 'new' as const },
  { label: t('assetDetail.sortReplied'), value: 'replied' as const },
])

// 将后端返回的图片路径转换为完整可访问 URL，拒绝危险协议（XSS 防护）
function resolveImageUrl(path: string | null | undefined): string {
  return resolveMediaUrl(path)
}

function clearViewerLoadTimer() {
  if (viewerLoadTimer !== null) {
    window.clearTimeout(viewerLoadTimer)
    viewerLoadTimer = null
  }
}

function destroyEmbeddedViewer() {
  if (embeddedViewer) {
    try {
      embeddedViewer.Clear()
    } catch {
      // ignore
    }
    embeddedViewer = null
  }
  clearViewerLoadTimer()
}

function resizeEmbeddedViewer() {
  if (embeddedViewer && typeof embeddedViewer.Resize === 'function') {
    embeddedViewer.Resize()
  }
}

async function mountEmbeddedViewer(modelUrl: string | null | undefined) {
  console.log('[AssetDetail] mountEmbeddedViewer called with:', modelUrl)
  await nextTick()
  console.log('[AssetDetail] viewerContainer:', viewerContainer.value)
  if (!modelUrl || !viewerContainer.value) return

  destroyEmbeddedViewer()
  viewerLoadFailed.value = false
   viewerLoading.value = true

  const viewerOptions: any = {
    backgroundColor: new OV.RGBAColor(20, 30, 52, 255),
    onModelLoaded: () => {
      clearViewerLoadTimer()
      viewerLoadFailed.value = false
      viewerLoading.value = false
      show3DHint.value = true
      window.setTimeout(() => {
        show3DHint.value = false
      }, 4000)
      applyEmbeddedViewerPostLoad(embeddedViewer, { logLabel: 'AssetDetail' })
      resizeEmbeddedViewer()
    },
    onModelLoadFailed: () => {
      clearViewerLoadTimer()
      destroyEmbeddedViewer()
      viewerLoadFailed.value = true
      viewerLoading.value = false
      // 尝试从后端刷新一次模型 URL（后续可接入实时签名），再重试加载
      if (!modelRefreshedOnce.value) {
        modelRefreshedOnce.value = true
        window.setTimeout(async () => {
          try {
            const res = await api.assets.modelUrl(props.id)
            if (asset.value && res?.url) {
              asset.value.model_url = res.url
              viewerLoadFailed.value = false
              await mountEmbeddedViewer(res.url)
            }
          } catch {
            // ignore
          }
        }, 0)
      }
    },
  }

  embeddedViewer = new OV.EmbeddedViewer(viewerContainer.value, viewerOptions)

  let modelFileName = 'model.glb'
  try {
    const path = (modelUrl.startsWith('/') ? modelUrl.split('?')[0] : new URL(modelUrl).pathname) || ''
    const fileName = path.split('/').filter(Boolean).pop()
    if (fileName) {
      modelFileName = fileName.includes('.') ? fileName : `${fileName}.glb`
    }
  } catch {
    // ignore，使用默认文件名
  }

  let urlToLoad = modelUrl
  if (modelUrl.startsWith('/uploads/')) {
    urlToLoad = resolveImageUrl(modelUrl)
  } else if (!modelUrl.startsWith('/api/studio/local-preview-file/')) {
    const proxyToken = `v${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
    urlToLoad = `/api/studio/model-proxy/${proxyToken}/${encodeURIComponent(modelFileName)}?url=${encodeURIComponent(
      modelUrl,
    )}`
  }

  embeddedViewer.LoadModelFromUrlList([urlToLoad])

  viewerLoadTimer = window.setTimeout(() => {
    destroyEmbeddedViewer()
    viewerLoadFailed.value = true
    viewerLoading.value = false
  }, 20000)

  resizeEmbeddedViewer()
}

function formatTime(iso: string) {
  if (!iso) return ''
  // 后端存的是 UTC，这里按 UTC 解析，然后格式化成本地时间字符串：YYYY-MM-DD HH:mm
  const normalized = iso.endsWith('Z') ? iso : `${iso}Z`
  const d = new Date(normalized)

  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hour}:${minute}`
}

function getReplyToUserName(parentComment: any) {
  return parentComment?.author_name || t('assetDetail.anonymous')
}

function handleCommentInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  const text = target.value
  // 限制在 1000 字符以内
  if (text.length > 1000) {
    commentContent.value = text.slice(0, 1000)
    commentCharCount.value = 1000
  } else {
    commentCharCount.value = text.length
  }
}

function handleReplyInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  const text = target.value
  // 限制在 1000 字符以内
  if (text.length > 1000) {
    replyContent.value = text.slice(0, 1000)
    replyCharCount.value = 1000
  } else {
    replyCharCount.value = text.length
  }
}

function triggerImageInput() {
  imageInput.value?.click()
}

function triggerReplyImageInput() {
  replyImageInput.value?.click()
}

function triggerVideoInput() {
  videoInput.value?.click()
}

function triggerReplyVideoInput() {
  replyVideoInput.value?.click()
}

async function handleImageSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (selectedImages.value.length + files.length > 10) {
    imageLimitDialogMessage.value = 'assetDetail.imageLimit10'
    imageLimitDialogOpen.value = true
    return
  }
  for (const file of files) {
    if (!file.type.startsWith('image/')) {
      alert(t('assetDetail.alertImagesOnly'))
      continue
    }
    const preview = URL.createObjectURL(file)
    selectedImages.value.push({ file, preview })
  }
  if (target) target.value = ''
}

function removeImage(idx: number) {
  URL.revokeObjectURL(selectedImages.value[idx].preview)
  selectedImages.value.splice(idx, 1)
}

async function handleVideoSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (selectedVideos.value.length + files.length > 3) {
    imageLimitDialogMessage.value = 'assetDetail.imageLimit3Video'
    imageLimitDialogOpen.value = true
    return
  }
  for (const file of files) {
    if (!file.type.startsWith('video/')) {
      alert(t('assetDetail.alertVideoType', { name: file.name, type: file.type || t('assetDetail.unknownType') }))
      continue
    }
    if (file.size > 100 * 1024 * 1024) {
      alert(t('assetDetail.alertVideoSize', { name: file.name }))
      continue
    }
    const preview = URL.createObjectURL(file)
    selectedVideos.value.push({ file, preview })
  }
  if (target) target.value = ''
}

function removeVideo(idx: number) {
  URL.revokeObjectURL(selectedVideos.value[idx].preview)
  selectedVideos.value.splice(idx, 1)
}

async function handleReplyImageSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (replyImages.value.length + files.length > 10) {
    imageLimitDialogMessage.value = 'assetDetail.imageLimit10'
    imageLimitDialogOpen.value = true
    return
  }
  for (const file of files) {
    if (!file.type.startsWith('image/')) {
      alert(t('assetDetail.alertImagesOnly'))
      continue
    }
    const preview = URL.createObjectURL(file)
    replyImages.value.push({ file, preview })
  }
  if (target) target.value = ''
}

function removeReplyImage(idx: number) {
  URL.revokeObjectURL(replyImages.value[idx].preview)
  replyImages.value.splice(idx, 1)
}

async function handleReplyVideoSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (replyVideos.value.length + files.length > 3) {
    imageLimitDialogMessage.value = 'assetDetail.imageLimit3Video'
    imageLimitDialogOpen.value = true
    return
  }
  for (const file of files) {
    if (!file.type.startsWith('video/')) {
      alert(t('assetDetail.alertVideoType', { name: file.name, type: file.type || t('assetDetail.unknownType') }))
      continue
    }
    if (file.size > 100 * 1024 * 1024) {
      alert(t('assetDetail.alertVideoSize', { name: file.name }))
      continue
    }
    const preview = URL.createObjectURL(file)
    replyVideos.value.push({ file, preview })
  }
  if (target) target.value = ''
}

function removeReplyVideo(idx: number) {
  URL.revokeObjectURL(replyVideos.value[idx].preview)
  replyVideos.value.splice(idx, 1)
}

function previewImage(url: string) {
  const fullUrl = resolveImageUrl(url)
  if (!fullUrl) return
  imagePreviewUrl.value = fullUrl
}

function closeImagePreview() {
  imagePreviewUrl.value = null
}

async function handlePreviewError(e: Event) {
  if (previewRefreshedOnce.value) return
  previewRefreshedOnce.value = true
  try {
    const res = await api.assets.previewUrl(props.id)
    if (asset.value && res?.url) {
      asset.value.image_url = res.url
      const el = e?.target as HTMLImageElement | null
      if (el) el.src = res.url
    }
  } catch {
    // ignore
  }
}

async function handleReferenceImageError(e: Event) {
  if (referencePreviewRefreshedOnce.value) return
  referencePreviewRefreshedOnce.value = true
  try {
    const res = await api.assets.referenceImageUrl(props.id)
    if (asset.value && res?.url) {
      asset.value.reference_image_url = res.url
      const el = e?.target as HTMLImageElement | null
      if (el) el.src = resolveImageUrl(res.url)
    }
  } catch {
    // ignore
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    asset.value = await api.assets.detail(props.id)
    console.log('[AssetDetail] asset:', asset.value)
    console.log('[AssetDetail] canShow3D:', canShow3D.value)

    // 统一通过后端接口刷新一次资源 URL（后续可接入实时签名）
    previewRefreshedOnce.value = false
    referencePreviewRefreshedOnce.value = false
    modelRefreshedOnce.value = false
    try {
      if (asset.value?.image_url) {
        const p = await api.assets.previewUrl(props.id)
        if (p?.url) {
          asset.value.image_url = p.url
        }
      }
    } catch {
      // ignore
    }
    try {
      if (asset.value?.studio_mode === 'image23d') {
        const r = await api.assets.referenceImageUrl(props.id)
        if (r?.url) {
          asset.value.reference_image_url = r.url
        }
      }
    } catch {
      // ignore
    }
    try {
      if (asset.value?.model_url) {
        const m = await api.assets.modelUrl(props.id)
        if (m?.url) asset.value.model_url = m.url
      }
    } catch {
      // ignore
    }

    liked.value = !!asset.value?.liked_by_me
    await loadComments()
  } catch (e: any) {
    error.value = e?.message || t('assetDetail.loadFailed')
  } finally {
    loading.value = false
    // loading 结束后视图会从“加载中”切到详情，这里再等待 DOM 更新，再挂载 3D 预览
    await nextTick()
    if (canShow3D.value && asset.value && asset.value.model_url) {
      await mountEmbeddedViewer(asset.value.model_url)
    } else {
      destroyEmbeddedViewer()
    }
  }
}

async function loadComments() {
  if (!props.id) return
  commentsLoading.value = true
  try {
    const res = await api.assets.comments(props.id, {
      page: 1,
      page_size: 100,
      sort: sortBy.value,
    })

    // 把每个主评论的整棵回复树打平成一个 replies 数组
    const flatItems = (res.items || []).map((root: any) => {
      const rootCopy = { ...root }
      const flatReplies: any[] = []

      const dfs = (nodes: any[] | undefined | null, parent: any) => {
        if (!nodes) return
        for (const r of nodes) {
          const copy = { ...r }
          // 记录“回复 @谁”
          copy.reply_to_name = parent?.author_name || null

          const children = copy.replies
          delete copy.replies

          flatReplies.push(copy)
          dfs(children || [], r)
        }
      }

      dfs(root.replies || [], root)

      // 子评论按时间正序排（最早在前）
      flatReplies.sort((a, b) => {
        const ta = new Date(a.created_at).getTime()
        const tb = new Date(b.created_at).getTime()
        return ta - tb
      })

      rootCopy.replies = flatReplies
      return rootCopy
    })

    comments.value = flatItems
    commentTotal.value = res.total
  } catch {
    comments.value = []
    commentTotal.value = 0
  } finally {
    commentsLoading.value = false
  }
}

function changeSort(sort: 'new' | 'liked' | 'replied') {
  sortBy.value = sort
  loadComments()
}

async function submitComment() {
  const content = commentContent.value?.trim()
  if (!content && selectedImages.value.length === 0 && selectedVideos.value.length === 0) return
  if (!asset.value || !auth.isAuthed) return
  if (commentCharCount.value > 1000) return

  submitting.value = true
  try {
    // 上传图片
    const imageUrls: string[] = []
    for (const img of selectedImages.value) {
      if (img.url) {
        imageUrls.push(img.url)
      } else {
        try {
          const res = await api.assets.uploadCommentImage(img.file)
          imageUrls.push(res.url)
        } catch (e: any) {
          const msg = e?.message || '未知错误'
          if (
            msg.includes('Invalid authentication credentials') ||
            msg.includes('401') ||
            msg.includes('未登录')
          ) {
            // 交给全局 401 处理（统一跳转登录），这里不再额外弹窗
            continue
          }
          alert(t('assetDetail.imageUploadFailed', { msg }))
          continue
        }
      }
    }

    // 上传视频
    const videoUrls: string[] = []
    for (const video of selectedVideos.value) {
      if (video.url) {
        videoUrls.push(video.url)
      } else {
        try {
          const res = await api.assets.uploadCommentVideo(video.file)
          videoUrls.push(res.url)
        } catch (e: any) {
          const msg = e?.message || '未知错误'
          if (
            msg.includes('Invalid authentication credentials') ||
            msg.includes('401') ||
            msg.includes('未登录')
          ) {
            continue
          }
          alert(t('assetDetail.videoUploadFailed', { msg }))
          continue
        }
      }
    }

    await api.assets.createComment(props.id, {
      content: content || '',
      images: imageUrls,
      videos: videoUrls,
    })
    commentContent.value = ''
    commentCharCount.value = 0
    selectedImages.value.forEach(img => URL.revokeObjectURL(img.preview))
    selectedVideos.value.forEach(video => URL.revokeObjectURL(video.preview))
    selectedImages.value = []
    selectedVideos.value = []
    await loadComments()
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.sendFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录') ||
      msg.includes('Failed to fetch')
    ) {
      return
    }
    alert(msg)
  } finally {
    submitting.value = false
  }
}

function startReply(comment: any, rootComment?: any) {
  if (!auth.isAuthed) {
    alert(t('assetDetail.loginToReply'))
    router.push('/profile')
    return
  }
  replyingTo.value = comment.id
  replyContent.value = ''
  replyCharCount.value = 0
  replyImages.value.forEach(img => URL.revokeObjectURL(img.preview))
  replyVideos.value.forEach(video => URL.revokeObjectURL(video.preview))
  replyImages.value = []
  replyVideos.value = []
  // 聚焦到输入框
  nextTick(() => {
    const textarea = document.querySelector(`textarea[placeholder*="${comment.author_name}"]`) as HTMLTextAreaElement
    if (textarea) {
      textarea.focus()
      // 滚动到输入框位置
      textarea.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  })
}

function cancelReply() {
  replyingTo.value = null
  replyContent.value = ''
  replyCharCount.value = 0
  replyImages.value.forEach(img => URL.revokeObjectURL(img.preview))
  replyVideos.value.forEach(video => URL.revokeObjectURL(video.preview))
  replyImages.value = []
  replyVideos.value = []
}

async function submitReply(targetComment: any, rootComment: any) {
  const content = replyContent.value?.trim()
  if (!content && replyImages.value.length === 0 && replyVideos.value.length === 0) return
  if (!asset.value || !auth.isAuthed) return
  if (replyCharCount.value > 1000) return

  submitting.value = true
  try {
    // 上传图片
    const imageUrls: string[] = []
    for (const img of replyImages.value) {
      if (img.url) {
        imageUrls.push(img.url)
      } else {
        try {
          const res = await api.assets.uploadCommentImage(img.file)
          imageUrls.push(res.url)
        } catch (e: any) {
          const msg = e?.message || '未知错误'
          if (
            msg.includes('Invalid authentication credentials') ||
            msg.includes('401') ||
            msg.includes('未登录')
          ) {
            // 交给全局 401 处理（统一跳转登录），这里不再额外弹窗
            continue
          }
          alert(t('assetDetail.imageUploadFailed', { msg }))
          continue
        }
      }
    }

    // 上传视频
    const videoUrls: string[] = []
    for (const video of replyVideos.value) {
      if (video.url) {
        videoUrls.push(video.url)
      } else {
        try {
          const res = await api.assets.uploadCommentVideo(video.file)
          videoUrls.push(res.url)
        } catch (e: any) {
          const msg = e?.message || '未知错误'
          if (
            msg.includes('Invalid authentication credentials') ||
            msg.includes('401') ||
            msg.includes('未登录')
          ) {
            continue
          }
          alert(t('assetDetail.videoUploadFailed', { msg }))
          // 阻止继续提交，避免回复在视频上传失败时只带部分视频
          return
        }
      }
    }

    if (!targetComment || !targetComment.id) {
      alert(t('assetDetail.replyTargetError'))
      return
    }

    const parentId = targetComment.id

    const created: any = await api.assets.createComment(props.id, {
      content: content || '',
      parent_id: parentId,
      images: imageUrls,
      videos: videoUrls,
    })

    // 组装新回复对象（用本地信息 + 后端返回的 id / 时间）
    const newReply: any = {
      id: created.comment_id || created.id,
      asset_id: props.id,
      author_id: auth.user?.id,
      author_name: auth.user?.username ?? t('assetDetail.anonymous'),
      author_avatar: auth.user?.avatar ?? '/default-avatar.png',
      parent_id: parentId,
      content: content || '',
      images: imageUrls,
      videos: videoUrls,
      like_count: 0,
      liked_by_me: false,
      reply_count: 0,
      status: 'published',
      created_at: created.created_at || new Date().toISOString(),
      updated_at: created.created_at || new Date().toISOString(),
      // “回复 @谁”
      reply_to_name: targetComment.author_name || t('assetDetail.anonymous'),
    }

    // 一律插到主评论的 replies 里（rootComment 是主评论）
    const parent = rootComment
    if (!parent.replies) {
      parent.replies = []
    }
    parent.replies.push(newReply)

    // 子评论按时间正序排序（最早在前）
    parent.replies.sort((a: any, b: any) => {
      const ta = new Date(a.created_at).getTime()
      const tb = new Date(b.created_at).getTime()
      return ta - tb
    })

    commentTotal.value += 1
    parent.reply_count = (parent.reply_count ?? 0) + 1

    const newId = newReply.id
    cancelReply()

    nextTick(() => {
      const el = document.querySelector(
        `[data-comment-id="${newId}"]`
      ) as HTMLElement | null
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    })
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.replyFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录') ||
      msg.includes('Failed to fetch')
    ) {
      return
    }
    alert(msg)
  } finally {
    submitting.value = false
  }
}

async function toggleCommentLike(comment: any) {
  if (!auth.isAuthed || !asset.value) return
  try {
    if (comment.liked_by_me) {
      await api.assets.unlikeComment(props.id, comment.id)
      comment.liked_by_me = false
      comment.like_count = Math.max(0, (comment.like_count ?? 1) - 1)
    } else {
      await api.assets.likeComment(props.id, comment.id)
      comment.liked_by_me = true
      comment.like_count = (comment.like_count ?? 0) + 1
    }
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.actionFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      return
    }
    alert(msg)
  }
}

async function toggleReplyLike(parentComment: any, reply: any) {
  if (!auth.isAuthed || !asset.value) return
  try {
    if (reply.liked_by_me) {
      await api.assets.unlikeComment(props.id, reply.id)
      reply.liked_by_me = false
      reply.like_count = Math.max(0, (reply.like_count ?? 1) - 1)
    } else {
      await api.assets.likeComment(props.id, reply.id)
      reply.liked_by_me = true
      reply.like_count = (reply.like_count ?? 0) + 1
    }
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.actionFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      return
    }
    alert(msg)
  }
}

function deleteComment(commentId: string) {
  pendingDeleteCommentId.value = commentId
  deleteCommentDialogOpen.value = true
}

async function confirmDeleteComment() {
  if (!pendingDeleteCommentId.value) return
  try {
    await api.assets.deleteComment(props.id, pendingDeleteCommentId.value)
    await loadComments()
    pendingDeleteCommentId.value = null
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.deleteFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      pendingDeleteCommentId.value = null
      return
    }
    alert(msg)
    pendingDeleteCommentId.value = null
  }
}

function copyTextViaExecCommand(text: string): boolean {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.left = '-9999px'
  ta.setAttribute('readonly', '')
  document.body.appendChild(ta)
  ta.select()
  try {
    return document.execCommand('copy')
  } finally {
    document.body.removeChild(ta)
  }
}

async function copyPrompt() {
  const text = asset.value?.prompt
  if (!text) return
  let ok = false
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      ok = true
    } catch {
      ok = false
    }
  }
  if (!ok) {
    ok = copyTextViaExecCommand(text)
  }
  if (ok) {
    copyPromptSuccess.value = true
    setTimeout(() => {
      copyPromptSuccess.value = false
    }, 1500)
  } else {
    alert(t('assetDetail.copyFailed'))
  }
}

async function like() {
  if (!asset.value) return
  if (!auth.isAuthed) {
    loginPromptMessage.value = 'assetDetail.loginToLike'
    loginPromptOpen.value = true
    return
  }
  try {
    const currentlyLiked = liked.value

    if (!currentlyLiked) {
      const res = await api.assets.like(props.id)
      asset.value.stats = { ...(asset.value.stats || {}), likes: res.likes }
      liked.value = true
    } else {
      const res = await api.assets.unlike(props.id)
      asset.value.stats = { ...(asset.value.stats || {}), likes: res.likes }
      liked.value = false
    }
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.likeFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      return
    }
    alert(msg)
  }
}

async function download() {
  if (!asset.value) return
  if (!auth.isAuthed) {
    loginPromptMessage.value = 'assetDetail.loginToDownload'
    loginPromptOpen.value = true
    return
  }
  try {
    const res = await api.assets.download(props.id)
    // 如果返回了下载数，更新统计（已登录用户）
    if (res.downloads !== undefined) {
      asset.value.stats = { ...(asset.value.stats || {}), downloads: res.downloads }
    }
    // 打开模型文件
    if (res.model_url) {
      const modelUrl = resolveMediaUrl(res.model_url)
      if (!modelUrl) {
             alert(t('assetDetail.invalidModelUrl'))
        return
      }
      window.open(modelUrl, '_blank')
    } else {
      alert(t('assetDetail.noModelFile'))
    }
  } catch (e: any) {
    const errorMsg = e?.message || t('assetDetail.downloadFailed')
    // 登录态失效的情况交给全局 401 处理（自动跳转登录）
    if (
      errorMsg.includes('Invalid authentication credentials') ||
      errorMsg.includes('401') ||
      errorMsg.includes('未登录')
    ) {
      return
    }
    alert(errorMsg)
  }
}

const printing = ref(false)

async function oneClickPrint() {
  if (!asset.value) return
  if (!auth.isAuthed) {
    loginPromptMessage.value = 'assetDetail.loginToPrint'
    loginPromptOpen.value = true
    return
  }
  // 已登录但可能已过期：先轻量校验一次登录态（/profile）
  try {
    await api.user.getProfile()
  } catch (e: any) {
    const msg = e?.message || e?.detail || ''
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      // 交给全局 401 处理
      return
    }
    // 其它异常按原样提示
    alert(msg || t('assetDetail.printOrderFailed'))
    return
  }
  // 登录态有效时才展示确认弹窗
  printHeight.value = '5cm'
  printConfirmOpen.value = true
}

async function submitPrintJob() {
  if (!asset.value) return
  printing.value = true
  try {
    // 切换至新的一键打印下单流程 (自动切片 + 云端同步)
      const result = await api.printOrders.create({
      asset_id: props.id,
      height: printHeight.value,
      material: 'PLA_WHITE'
    })
    printSuccessTitle.value = '提交成功'
    printSuccessMessage.value = `任务已提交 (订单号: ${result.order_id})，系统正在自动切片并核算真实克重，金额确认后订单会进入待支付。`
    printSuccessOpen.value = true
  } catch (e: any) {
    const msg = e?.message || e?.detail || t('assetDetail.printOrderFailed')
    // 登录态失效的情况交给全局 401 处理（自动跳转登录）
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      return
    }
    printSuccessTitle.value = 'assetDetail.tipTitle'
    printSuccessMessage.value = msg
    printSuccessOpen.value = true
  } finally {
    printing.value = false
  }
}

function handleDelete() {
  if (!asset.value) return
  deleteAssetDialogOpen.value = true
}

async function confirmDeleteAsset() {
  try {
    await api.assets.delete(props.id)
    router.push('/community')
  } catch (e: any) {
    const msg = e?.message || t('assetDetail.deleteFailed')
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      // 交给全局 401 处理（统一跳转登录），这里不再额外弹窗
      return
    }
    alert(msg)
  }
}

onMounted(() => {
  auth.hydrate()
  load()
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', resizeEmbeddedViewer)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', resizeEmbeddedViewer)
  }
  destroyEmbeddedViewer()
})

watch(
  () => props.id,
  () => {
    load()
  },
)
</script>

<style scoped>
/* 整体容器 */
.asset-detail-container {
  background-color: #161625;
  border-radius: 12px;
  padding: 24px;
  margin-top: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: all 0.2s;
}

.asset-detail-loading,
.asset-detail-error {
  text-align: center;
  padding: 32px 0;
  color: #94a3b8;
}

.asset-detail-error {
  color: #f87171;
}

.asset-detail-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

@media (min-width: 1024px) {
  .asset-detail-content {
    grid-template-columns: 1fr 1fr;
  }
}

/* 作品预览图区 */
.asset-preview-section {
  position: relative;
}

.asset-back-btn {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10;
  padding: 8px 12px;
  background-color: transparent;
  border: none;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 6px;
}

.asset-back-btn:hover {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.1);
}

.asset-preview-wrapper {
  background-color: #1E1E2E;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  min-height: 400px;
}

.asset-3d-hint-pill {
  position: absolute;
  top: 20px;
  right: 24px;
  z-index: 5;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.5);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.7);
  font-size: 12px;
  color: #e5e7eb;
  display: flex;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}


.asset-3d-viewer {
  width: 100%;
  height: auto;
  aspect-ratio: 4 / 3;
  max-height: 60vh;
  min-height: 320px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #020617;
}


.asset-3d-viewer :deep(.ov_info_panel) {
  display: none;
}


.asset-3d-viewer :deep(canvas) {
  transform: scale(1.1);
  transform-origin: center center;
}

.asset-3d-loading-mask {
  position: absolute;
  inset: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 8px;
  background: radial-gradient(circle at 20% 20%, rgba(148, 163, 184, 0.24), transparent 55%),
    radial-gradient(circle at 80% 80%, rgba(96, 165, 250, 0.24), transparent 55%),
    rgba(15, 23, 42, 0.92);
  pointer-events: none;
}

.asset-3d-loading-spinner {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 3px solid rgba(148, 163, 184, 0.35);
  border-top-color: #60a5fa;
  animation: asset-3d-spin 0.8s linear infinite;
}

.asset-3d-loading-text {
  font-size: 13px;
  color: #e5e7eb;
  letter-spacing: 0.04em;
}

@keyframes asset-3d-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.asset-preview-image {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  border-radius: 8px;
}

/* 作品信息区 */
.asset-info-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.asset-info-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.asset-detail-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.asset-info-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.asset-delete-btn {
  padding: 6px 12px;
  background-color: transparent;
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 8px;
  color: #f87171;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.asset-delete-btn:hover {
  background-color: rgba(248, 113, 113, 0.1);
  border-color: #f87171;
  color: #ef4444;
}

.asset-author-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.asset-author-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(148, 163, 184, 0.25);
}

.asset-author {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

.asset-published {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
  text-align: right;
  align-self: flex-end;
}

.asset-prompt-section {
  background-color: #1E1E2E;
  border-radius: 8px;
  padding: 16px;
}

.asset-prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.asset-prompt-label {
  font-size: 14px;
  font-weight: 600;
  color: #67e8f9;
  text-transform: uppercase;
}

.asset-prompt-copy {
  padding: 4px 8px;
  background-color: transparent;
  border: none;
  color: #7B61FF;
  font-size: 12px;
  cursor: pointer;
  transition: color 0.2s;
}

.asset-prompt-copy:hover {
  color: #6B51E6;
}

.asset-prompt-copy-success {
  color: #34d399 !important;
}

.asset-prompt-reference {
  margin-bottom: 14px;
}

.asset-prompt-reference-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 8px;
}

.asset-prompt-reference-frame {
  display: inline-block;
  max-width: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: #0f172a;
}

.asset-prompt-reference-img {
  display: block;
  max-width: min(100%, 360px);
  max-height: 220px;
  width: auto;
  height: auto;
  object-fit: contain;
  vertical-align: middle;
}

.asset-prompt-content {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #ffffff;
  line-height: 1.6;
  word-break: break-all;
}

.asset-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.asset-tag {
  padding: 4px 8px;
  background-color: #1E1E2E;
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 4px;
  color: #67e8f9;
  font-size: 12px;
  font-weight: 500;
}

.asset-stat-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: transparent;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #94a3b8;
}

.asset-stat-btn {
  cursor: pointer;
  transition: all 0.2s;
}

.asset-stat-btn:hover {
  color: #cbd5e1;
  border-color: rgba(148, 163, 184, 0.35);
  background-color: rgba(148, 163, 184, 0.1);
}

.asset-stat-badge .asset-stat-icon {
  width: 16px;
  height: 16px;
  color: currentColor;
}

.asset-stat-badge .asset-stat-value {
  font-size: 14px;
  font-weight: 500;
  color: currentColor;
}

.asset-stat-like:hover,
.asset-stat-like-active {
  color: #f472b6;
  border-color: rgba(244, 114, 182, 0.45);
  background-color: rgba(244, 114, 182, 0.12);
}

.asset-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.asset-action-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  border: none;
}

.asset-action-btn-primary {
  background-color: #7B61FF;
  color: #ffffff;
}

.asset-action-btn-primary:hover {
  background-color: #6B51E6;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(123, 97, 255, 0.3);
}

.asset-action-btn-secondary {
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #cbd5e1;
}

.asset-action-btn-secondary:hover {
  background-color: #252538;
  border-color: rgba(148, 163, 184, 0.3);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.asset-action-btn-print {
  background-color: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #34d399;
}

.asset-action-btn-print:hover:not(:disabled) {
  background-color: rgba(16, 185, 129, 0.25);
  border-color: #34d399;
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.asset-action-btn-print:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 评论区 */
.comment-section {
  background-color: #161625;
  border-radius: 12px;
  padding: 24px;
  margin-top: 32px;
  transition: all 0.2s;
}

.comment-section-title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 24px;
}

/* 输入区 */
.comment-input-area {
  margin-bottom: 24px;
}

.comment-textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #f8fafc;
  font-size: 14px;
  resize: vertical;
  outline: none;
  transition: all 0.2s;
}

.comment-textarea:focus {
  border-color: #7B61FF;
  box-shadow: 0 0 0 3px rgba(123, 97, 255, 0.1);
}

.comment-textarea-sm {
  min-height: 80px;
  font-size: 13px;
}

.comment-input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.comment-char-count {
  font-size: 12px;
  color: #94a3b8;
  transition: color 0.2s;
}

.comment-char-count-warning {
  color: #f87171;
}

.comment-char-count-sm {
  font-size: 11px;
}

.btn-image-select {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-image-select:hover {
  background-color: #252538;
  border-color: rgba(148, 163, 184, 0.3);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.btn-image-select-sm {
  padding: 6px 10px;
  font-size: 12px;
}

.btn-publish {
  padding: 8px 16px;
  background-color: #7B61FF;
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-publish:hover:not(:disabled) {
  background-color: #6B51E6;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(123, 97, 255, 0.3);
}

.btn-publish:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-publish-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-cancel-sm {
  padding: 6px 12px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel-sm:hover {
  background-color: #252538;
  color: #ffffff;
}

.comment-image-preview {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.comment-video-preview {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.comment-image-item {
  position: relative;
  transition: transform 0.2s;
}

.comment-video-item {
  position: relative;
  width: 160px;
  transition: transform 0.2s;
}

.comment-video-item:hover {
  transform: translateY(-2px);
}

.comment-image-item:hover {
  transform: translateY(-2px);
}

.comment-video-item-sm {
  width: 140px;
}

.comment-image-preview-img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.comment-video-preview-player {
  width: 100%;
  height: 90px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background-color: #0f172a;
}

.comment-video-preview-player-sm {
  height: 80px;
}

.comment-video-name {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.comment-image-preview-img-sm {
  width: 64px;
  height: 64px;
}

.comment-image-remove {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #ef4444;
  color: #ffffff;
  font-size: 12px;
  border: none;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.comment-image-item:hover .comment-image-remove {
  opacity: 1;
}

.comment-image-remove-sm {
  width: 16px;
  height: 16px;
  font-size: 10px;
}

.comment-login-prompt {
  color: #94a3b8;
  font-size: 14px;
  margin-bottom: 24px;
}

.comment-login-link {
  color: #7B61FF;
  cursor: pointer;
  transition: color 0.2s;
}

.comment-login-link:hover {
  color: #6B51E6;
  text-decoration: underline;
}

.comment-image-hint {
  font-size: 11px;
  color: #64748b;
}

/* 排序标签 */
.comment-sort-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.comment-sort-btn {
  padding: 6px 12px;
  background-color: transparent;
  border: none;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.comment-sort-btn:hover {
  color: #cbd5e1;
}

.comment-sort-btn-active {
  background-color: #7B61FF;
  color: #ffffff;
  font-weight: 500;
}

.comment-sort-btn-active:hover {
  background-color: #6B51E6;
}

/* 评论列表 */
.comment-loading {
  color: #94a3b8;
  text-align: center;
  padding: 32px 0;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-empty {
  color: #94a3b8;
  font-size: 14px;
  text-align: center;
  padding: 32px 0;
}

/* 评论卡片 */
.comment-card {
  background-color: #1E1E2E;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: all 0.2s;
}

.comment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.comment-card-content {
  display: flex;
  gap: 12px;
}

.comment-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(148, 163, 184, 0.2);
  flex-shrink: 0;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.comment-author {
  font-weight: 600;
  color: #ffffff;
  font-size: 14px;
}

.comment-time {
  font-size: 12px;
  color: #94a3b8;
}

.comment-text {
  color: #e2e8f0;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-images {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.comment-videos {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.comment-image {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  cursor: pointer;
  transition: opacity 0.2s;
}

.comment-video {
  width: min(320px, 100%);
  height: 180px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background-color: #0f172a;
}

.comment-image:hover {
  opacity: 0.8;
}

@media (max-width: 640px) {
  .comment-video {
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 9;
  }
}

/* 评论内容下方：时间 + 赞、回复 */
.comment-meta-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
}

.comment-meta-actions .comment-time {
  flex-shrink: 0;
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  position: relative;
}

.comment-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background-color: transparent;
  border: none;
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 4px;
}

.comment-action-btn:hover {
  color: #f472b6;
  background-color: rgba(244, 114, 182, 0.1);
}

.comment-action-btn-active {
  color: #f472b6;
}

.comment-action-btn-sm {
  font-size: 12px;
  padding: 3px 6px;
}

.comment-delete-btn {
  padding: 4px 8px;
  background-color: transparent;
  border: none;
  color: #f87171;
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
  border-radius: 4px;
  flex-shrink: 0;
}

.comment-card:hover .comment-delete-btn,
.reply-wrapper:hover .comment-delete-btn {
  opacity: 1;
}

.comment-delete-btn:hover {
  background-color: rgba(248, 113, 113, 0.1);
  color: #ef4444;
}

/* 楼中楼回复容器（不再缩进和竖线，仅用于分组） */
.reply-wrapper {
  margin-top: 8px;
}

/* 回复输入框 */
.comment-reply-input {
  margin-top: 12px;
}

.comment-reply-input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

/* 修复楼中楼删除按钮 hover 显示 */
.reply-wrapper .comment-delete-btn {
  opacity: 0;
  transition: all 0.2s;
}

/* 楼中楼卡片 hover 时显示删除按钮 */
.reply-wrapper:hover .comment-delete-btn {
  opacity: 1;
}

/* 强制楼中楼内部元素继承主评论样式，避免错位 */
.reply-wrapper .comment-card-content {
  display: flex;
  gap: 12px;
  width: 100%;
}

.reply-wrapper .comment-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(148, 163, 184, 0.2);
  flex-shrink: 0;
}

.reply-wrapper .comment-body {
  flex: 1;
  min-width: 0;
}

.reply-wrapper .comment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.reply-wrapper .comment-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  position: relative;
}

/* 图片预览弹窗 */
.image-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}

.image-preview-dialog {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  padding: 16px;
  border-radius: 16px;
  background: #020617;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview-img {
  max-width: 80vw;
  max-height: 80vh;
  border-radius: 12px;
}

.image-preview-close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 9999px;
  border: none;
  background: rgba(15, 23, 42, 0.75);
  color: #e5e7eb;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.1s;
}

.image-preview-close-btn:hover {
  background: rgba(30, 64, 175, 0.9);
  transform: translateY(-1px);
}

/* “回复 @xxx” 文本样式 */
.comment-reply-to {
  font-size: 12px;
  color: #94a3b8;
}

/* 保留原有样式（用于其他部分） */
.panel {
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
}
.like-button {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  border: 1px solid #475569;
  background: rgba(15, 23, 42, 0.7);
  color: #e2e8f0;
  font-size: 0.75rem;
  transition: all 0.2s;
}
.like-button.is-liked {
  border-color: #ec4899;
  background: rgba(236, 72, 153, 0.1);
  color: #f9a8d4;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.btn-delete {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: rgba(220, 38, 38, 0.8);
  color: #ffffff;
  font-size: 0.875rem;
  font-weight: 700;
  transition: background-color 0.2s;
}
.tag {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(99, 102, 241, 0.3);
  background: rgba(99, 102, 241, 0.1);
  color: #c7d2fe;
}
</style>
