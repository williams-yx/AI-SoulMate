<template>
  <!-- 造梦页面：支持四种模式（文生图、文生3D、图转3D、本地预览） -->
  <div class="page-transition space-y-4">
    <template v-if="auth && !auth.isAuthed">
    <!-- 顶部功能选择 Tab -->
    <div class="glass-panel p-1 rounded-xl border border-slate-700 grid grid-cols-2 md:grid-cols-4 gap-1">
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'text2image' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'text2image'"
      >
        <span class="inline-block mr-2"><i data-lucide="image" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.text2image') }}
      </button>
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'text23d' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'text23d'"
      >
        <span class="inline-block mr-2"><i data-lucide="box" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.text23d') }}
      </button>
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'image23d' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'image23d'"
      >
        <span class="inline-block mr-2"><i data-lucide="upload" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.image23d') }}
      </button>
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'local3dpreview' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'local3dpreview'"
      >
        <span class="inline-block mr-2"><i data-lucide="folder-open" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.local3dpreview') }}
      </button>
    </div>

    <!-- 未登录提示 -->
    <div class="glass-panel p-8 rounded-2xl border border-slate-700 text-center text-slate-300">
      <p class="mb-4">{{ t('studio.authRequired') }}</p>
      <router-link to="/" class="text-indigo-400 hover:underline">{{ t('studio.backHomeLogin') }}</router-link>
    </div>
    </template>

    <!-- 主内容区：登录后显示 -->
    <template v-else>
    <div
      class="flex flex-col gap-4 md:min-h-[calc(100vh-6.5rem)] md:h-[calc(100vh-6.5rem)] md:grid md:grid-cols-[auto_minmax(0,1fr)] md:grid-rows-[auto_minmax(0,1fr)] md:gap-4"
    >
      <!-- 右侧：Tab + 参数/结果（DOM 靠前以便移动端先显示 Tab；桌面端占第 2 列跨两行） -->
      <div class="order-1 md:order-none flex flex-col gap-4 min-w-0 min-h-0 md:col-start-2 md:row-start-1 md:row-span-2 md:h-full md:min-h-0">
    <!-- 顶部功能选择 Tab（与历史平级，仅占据工作区宽度） -->
    <div class="glass-panel p-1 rounded-xl border border-slate-700 grid grid-cols-2 md:grid-cols-4 gap-1 shrink-0">
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'text2image' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'text2image'"
      >
        <span class="inline-block mr-2"><i data-lucide="image" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.text2image') }}
      </button>
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'text23d' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'text23d'"
      >
        <span class="inline-block mr-2"><i data-lucide="box" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.text23d') }}
      </button>
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'image23d' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'image23d'"
      >
        <span class="inline-block mr-2"><i data-lucide="upload" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.image23d') }}
      </button>
      <button
        class="py-2 px-3 rounded-lg text-sm font-bold transition flex items-center justify-center"
        :class="mode === 'local3dpreview' ? 'bg-indigo-600 text-white' : 'bg-transparent text-slate-400 hover:text-white'"
        type="button"
        @click="mode = 'local3dpreview'"
      >
        <span class="inline-block mr-2"><i data-lucide="folder-open" class="w-4 h-4"></i></span>
        {{ t('studio.tabs.local3dpreview') }}
      </button>
    </div>

    <div class="flex flex-col gap-4 md:flex-row md:items-stretch md:flex-1 md:min-h-0 md:h-full w-full min-h-0">
      <!-- 左侧参数面板 -->
      <section class="w-full self-start md:self-stretch md:w-72 lg:w-80 xl:w-[22rem] glass-panel flex flex-col min-h-0 md:sticky md:top-4 md:h-full md:max-h-full md:rounded-l-2xl rounded-2xl border border-slate-700 md:border-r-0 overflow-hidden">
          <div class="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center gap-2">
          <span :key="mode">
            <i
              :data-lucide="mode === 'image23d' ? 'upload' : mode === 'local3dpreview' ? 'folder-open' : 'wand-2'"
              class="w-4 h-4 text-indigo-400"
            ></i>
          </span>
          <h2 class="font-bold text-sm text-slate-100">
            {{
              mode === 'text2image'
                ? t('studio.panel.title.text2image')
                : mode === 'text23d'
                  ? t('studio.panel.title.text23d')
                  : mode === 'image23d'
                    ? t('studio.panel.title.image23d')
                    : t('studio.panel.title.local3dpreview')
            }}
          </h2>
        </div>

        <div class="studio-left-panel-scroll p-4 overflow-y-auto flex-1 space-y-6 [scrollbar-gutter:stable]">
          <!-- 文生图 / 文生3D：文本输入 -->
          <template v-if="mode === 'text2image' || mode === 'text23d'">
            <!-- 提示词输入 -->
            <div>
              <div class="flex justify-between mb-1 items-center gap-2">
                <label class="text-xs font-bold text-slate-400 uppercase flex items-center gap-1.5">
                  <span>{{ t('studio.prompt.label') }}</span>
                  <span
                    class="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 text-[10px] text-slate-400 cursor-help normal-case"
                    aria-label="compliance-tip"
                    tabindex="0"
                    @mouseenter="showComplianceTip"
                    @mouseleave="hideComplianceTip"
                    @focus="showComplianceTip"
                    @blur="hideComplianceTip"
                  >
                    i
                  </span>
                </label>
                <div class="flex items-center gap-1.5">
                  <button
                    v-if="promptAssistantEnabled"
                    class="text-xs border border-indigo-500/40 rounded px-2 py-1 text-indigo-200 hover:text-white hover:bg-indigo-500/10 transition disabled:opacity-60 disabled:cursor-not-allowed"
                    type="button"
                    :disabled="optimizingPrompt || translatingPrompt || promptInputLocked"
                    @click="optimizePromptWithAssistant"
                  >
                    {{ optimizingPrompt ? t('studio.prompt.optimizing') : t('studio.prompt.aiOptimize') }}
                  </button>
                  <button
                    class="text-xs border border-slate-600 rounded px-2 py-1 text-slate-300 hover:text-white hover:bg-white/5 transition disabled:opacity-60 disabled:cursor-not-allowed"
                    type="button"
                    :disabled="translatingPrompt || optimizingPrompt || promptInputLocked"
                    @click="toggleLang"
                  >
                    {{ translatingPrompt ? t('studio.prompt.translating') : (lang === 'cn' ? t('studio.prompt.cnToEn') : t('studio.prompt.enToCn')) }}
                  </button>
                </div>
              </div>
              <textarea
                v-model="prompt"
                class="w-full h-32 border rounded p-2 text-sm resize-none outline-none transition"
                :class="
                  promptInputLocked
                    ? 'bg-slate-950/80 border-slate-600 text-slate-400 cursor-not-allowed focus:border-slate-600'
                    : 'bg-slate-900 border-slate-600 text-slate-200 focus:border-indigo-500'
                "
                :readonly="promptInputLocked"
                :placeholder="mode === 'text2image' ? t('studio.prompt.placeholder.text2image') : t('studio.prompt.placeholder.text23d')"
              ></textarea>
              <p v-if="promptInputLocked" class="mt-2 text-[11px] text-amber-400/90">生成进行中，完成后可修改提示词</p>
              <p v-if="promptAssistantEnabled" class="mt-2 text-[11px] text-slate-500">
                {{ t('studio.prompt.assistantHint', { mode: mode === 'text2image' ? t('studio.modeLabels.text2img') : t('studio.modeLabels.text23d') }) }}
              </p>
            </div>

            <div v-if="mode === 'text2image'" class="space-y-3 border border-slate-700 rounded-lg p-3 bg-slate-900/40">
              <label class="text-xs font-bold text-slate-300 uppercase block">{{ t('studio.t2i.outputSpec') }}</label>
              <div class="space-y-1">
                <label class="text-xs text-slate-400">{{ t('studio.t2i.style') }}</label>
                <select
                  v-model="t2iStyle"
                  class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition"
                >
                  <option value="auto">{{ t('studio.t2i.styles.auto') }}</option>
                  <option value="cinematic">{{ t('studio.t2i.styles.cinematic') }}</option>
                  <option value="photoreal">{{ t('studio.t2i.styles.photoreal') }}</option>
                  <option value="anime">{{ t('studio.t2i.styles.anime') }}</option>
                  <option value="illustration">{{ t('studio.t2i.styles.illustration') }}</option>
                  <option value="watercolor">{{ t('studio.t2i.styles.watercolor') }}</option>
                  <option value="pixel">{{ t('studio.t2i.styles.pixel') }}</option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="text-xs text-slate-400">{{ t('studio.t2i.resolutionLevel') }}</label>
                <select
                  v-model="t2iResolutionLevel"
                  class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition"
                >
                  <option value="720p">720p</option>
                  <option value="1k">1K</option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="text-xs text-slate-400">{{ t('studio.t2i.aspectRatio') }}</label>
                <select
                  v-model="t2iAspectRatio"
                  class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition"
                >
                  <option value="1:1">1:1</option>
                  <option value="3:4">3:4</option>
                  <option value="4:3">4:3</option>
                  <option value="16:9">16:9</option>
                  <option value="9:16">9:16</option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="text-xs text-slate-400">{{ t('studio.t2i.outputSize') }}</label>
                <div class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-300">
                  {{ t2iOutputSize }}
                </div>
              </div>
              <p class="text-[11px] text-slate-500">
                {{ t('studio.t2i.currentCombo', { level: t2iResolutionLevelLabel, ratio: t2iAspectRatio, size: t2iOutputSize, style: t2iStyleLabel }) }}
              </p>
            </div>
          </template>

          <!-- 图转3D：图片上传 -->
          <template v-else-if="mode === 'image23d'">
            <div>
              <label class="text-xs font-bold text-slate-400 uppercase mb-2 flex items-center gap-1.5">
                <span>{{ t('studio.image23d.uploadImage') }}</span>
                <span
                  class="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 text-[10px] text-slate-400 cursor-help normal-case"
                  aria-label="compliance-tip"
                  tabindex="0"
                  @mouseenter="showComplianceTip"
                  @mouseleave="hideComplianceTip"
                  @focus="showComplianceTip"
                  @blur="hideComplianceTip"
                >
                  i
                </span>
              </label>
              <div
                class="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center cursor-pointer hover:border-indigo-500 transition"
                :class="[
                  uploadedImage ? 'border-indigo-500' : '',
                  imageDropActive ? 'border-indigo-400 bg-indigo-500/10' : ''
                ]"
                @click="triggerFileInput"
                @dragenter.prevent="handleImageDragEnter"
                @dragover.prevent="handleImageDragOver"
                @dragleave.prevent="handleImageDragLeave"
                @drop.prevent="handleImageDrop"
              >
                <input
                  ref="fileInput"
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="handleFileUpload"
                />
                <div v-if="!uploadedImage">
                  <i data-lucide="upload-cloud" class="w-12 h-12 text-slate-500 mx-auto mb-2"></i>
                  <p class="text-sm text-slate-400">{{ t('studio.image23d.clickOrDrop') }}</p>
                  <p class="text-xs text-slate-500 mt-1">{{ t('studio.image23d.supportFormats') }}</p>
                </div>
                <div v-else class="space-y-2">
                  <img :src="uploadedImage" class="max-h-48 mx-auto rounded-lg border border-slate-700" :alt="t('studio.image23d.uploadedImageAlt')" />
                  <p class="text-xs text-slate-400">{{ uploadedFileName }}</p>
                </div>
              </div>
            </div>
          </template>

          <!-- 本地预览：3D文件上传 -->
          <template v-else>
            <div>
              <label class="text-xs font-bold text-slate-400 uppercase mb-2 flex items-center gap-1.5">
                <span>{{ t('studio.localPreview.uploadLabel') }}</span>
                <span
                  class="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 text-[10px] text-slate-400 cursor-help normal-case"
                  aria-label="compliance-tip"
                  tabindex="0"
                  @mouseenter="showComplianceTip"
                  @mouseleave="hideComplianceTip"
                  @focus="showComplianceTip"
                  @blur="hideComplianceTip"
                >
                  i
                </span>
              </label>
              <div
                class="border-2 border-dashed border-slate-600 rounded-lg p-6 text-center cursor-pointer hover:border-indigo-500 transition"
                :class="localModelFiles.length > 0 ? 'border-indigo-500' : ''"
                @click="triggerLocalModelInput"
              >
                <input
                  ref="localModelInput"
                  type="file"
                  accept=".glb,model/gltf-binary"
                  class="hidden"
                  @change="handleLocalModelUpload"
                />
                <div v-if="localModelFiles.length === 0">
                  <i data-lucide="folder-open" class="w-12 h-12 text-slate-500 mx-auto mb-2"></i>
                  <p class="text-sm text-slate-400">{{ t('studio.localPreview.clickSelect') }}</p>
                  <p class="text-xs text-slate-500 mt-1">{{ t('studio.localPreview.supportHint') }}</p>
                </div>
                <div v-else class="space-y-2 text-left">
                  <p class="text-xs text-slate-300 font-semibold">已选择 GLB 文件：</p>
                  <div class="max-h-28 overflow-y-auto rounded border border-slate-700 p-2 bg-slate-900/60">
                    <p
                      v-for="name in localModelFileNamesPreview"
                      :key="name"
                      class="text-xs text-slate-400 truncate"
                    >
                      {{ name }}
                    </p>
                  </div>
                  <button
                    class="text-xs text-red-400 hover:text-red-300"
                    type="button"
                    @click.stop="clearLocalModelFiles"
                  >
                    {{ t('studio.common.reselect') }}
                  </button>
                </div>
              </div>
            </div>
          </template>

          <div v-if="mode === 'text23d'" class="space-y-2">
            <div class="space-y-1">
              <label class="text-xs text-slate-400">{{ t('studio.text23d.resultFormatLabel') }}</label>
              <select
                v-model="text3dResultFormat"
                :disabled="text23dConfigLocked"
                class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <option value="GLB">GLB（不可打印）</option>
                <option value="STL">STL（可打印）</option>
              </select>
            </div>
            <label class="text-xs font-bold text-slate-400 uppercase block">{{ t('studio.text23d.modelMode') }}</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                :disabled="text23dConfigLocked || text3dResultFormat === 'STL'"
                :title="text3dResultFormat === 'STL' ? t('studio.text23d.colorUnavailableForStl') : undefined"
                class="py-2 rounded-lg border text-sm font-semibold transition"
                :class="
                  text23dConfigLocked || text3dResultFormat === 'STL'
                    ? 'opacity-40 cursor-not-allowed border-slate-700 text-slate-500 bg-slate-900/50'
                    : modelRenderMode === 'color'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-slate-900 text-slate-300 border-slate-600 hover:border-slate-500'
                "
                @click="modelRenderMode = 'color'"
              >
                {{ t('studio.text23d.colorWithTexture') }}
              </button>
              <button
                type="button"
                :disabled="text23dConfigLocked"
                class="py-2 rounded-lg border text-sm font-semibold transition"
                :class="text23dConfigLocked
                  ? 'opacity-40 cursor-not-allowed border-slate-700 text-slate-500 bg-slate-900/50'
                  : modelRenderMode === 'white'
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-slate-900 text-slate-300 border-slate-600 hover:border-slate-500'"
                @click="modelRenderMode = 'white'"
              >
                {{ t('studio.text23d.whiteGeometry') }}
              </button>
            </div>
          </div>

          <div v-if="mode === 'image23d'" class="space-y-3 border border-slate-700 rounded-lg p-3 bg-slate-900/40">
            <label class="text-xs font-bold text-slate-300 uppercase block">{{ t('studio.image23d.configTitle') }}</label>

            <div class="space-y-1">
              <label class="text-xs text-slate-400">{{ t('studio.image23d.modelVersion') }}</label>
              <select
                v-model="image3dOptions.model"
                class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition"
              >
                <option value="3.0">{{ t('studio.image23d.modelVersion30') }}</option>
                <option
                  value="3.1"
                  :disabled="image3dDerivedGenerateType === 'LowPoly' || image3dDerivedGenerateType === 'Sketch'"
                >
                  {{ t('studio.image23d.modelVersion31') }}
                </option>
              </select>
            </div>

            <div class="space-y-1">
              <label class="text-xs text-slate-400">{{ t('studio.image23d.outputFormat') }}</label>
              <select
                v-model="image3dOptions.result_format"
                class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition"
              >
                <option value="GLB">GLB（不可打印）</option>
                <option value="STL">STL（可打印）</option>
              </select>
            </div>

            <div class="space-y-1">
              <label class="text-xs text-slate-400">{{ t('studio.image23d.generateType') }}</label>
              <select
                v-model="image3dOptions.structure_mode"
                class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition"
                :title="image3dOptions.result_format === 'STL' ? t('studio.image23d.generateTypeStlOnlyWhite') : undefined"
              >
                <option value="AUTO_COLOR" :disabled="image3dOptions.result_format === 'STL'">
                  {{ t('studio.image23d.generateTypes.autoColor') }}
                </option>
                <option value="AUTO_WHITE">{{ t('studio.image23d.generateTypes.autoWhite') }}</option>
                <option value="LOWPOLY_COLOR" :disabled="image3dOptions.result_format === 'STL'">
                  {{ t('studio.image23d.generateTypes.lowpolyColor') }}
                </option>
                <option value="LOWPOLY_WHITE">{{ t('studio.image23d.generateTypes.lowpolyWhite') }}</option>
                <option value="SKETCH_COLOR" :disabled="image3dOptions.result_format === 'STL'">
                  {{ t('studio.image23d.generateTypes.sketchColor') }}
                </option>
                <option value="SKETCH_WHITE">{{ t('studio.image23d.generateTypes.sketchWhite') }}</option>
              </select>
            </div>

            <div class="space-y-1">
              <label class="text-xs text-slate-400">{{ t('studio.image23d.faceCountLabel', { count: image3dOptions.face_count.toLocaleString() }) }}</label>
              <input
                v-model.number="image3dOptions.face_count"
                type="range"
                :min="image3dFaceCountMin"
                max="1500000"
                step="1000"
                class="w-full accent-indigo-500"
              />
              <p class="text-[11px] text-slate-500">
                {{ image3dDerivedGenerateType === 'LowPoly' ? t('studio.image23d.faceCountHintLowpoly') : t('studio.image23d.faceCountHintNormal') }}
              </p>
            </div>

            <div class="space-y-1">
              <label class="text-xs text-slate-400">{{ t('studio.image23d.polygonType') }}</label>
              <select
                v-model="image3dOptions.polygon_type"
                :disabled="image3dDerivedGenerateType !== 'LowPoly'"
                class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-indigo-500 outline-none transition disabled:opacity-50"
              >
                <option value="triangle">{{ t('studio.image23d.polygonTypes.triangle') }}</option>
                <option value="quadrilateral">{{ t('studio.image23d.polygonTypes.quadrilateral') }}</option>
              </select>
            </div>

            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-xs text-slate-400">{{ t('studio.image23d.enablePbr') }}</p>
                <p class="text-[11px] text-slate-500">{{ t('studio.image23d.enablePbrHint') }}</p>
              </div>
              <button
                type="button"
                class="px-3 py-1 rounded border text-xs transition"
                :class="image3dOptions.enable_pbr
                  ? 'bg-emerald-600/20 text-emerald-300 border-emerald-500/50'
                  : 'bg-slate-900 text-slate-300 border-slate-600'"
                @click="image3dOptions.enable_pbr = !image3dOptions.enable_pbr"
              >
                {{ image3dOptions.enable_pbr ? t('studio.common.enabled') : t('studio.common.disabled') }}
              </button>
            </div>

          </div>
        </div>

        <!-- 生成按钮 -->
        <div class="p-4 border-t border-slate-700">
          <button
            class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl shadow-lg flex items-center justify-center gap-2 transition active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
            type="button"
            :disabled="loading || (mode === 'image23d' && !uploadedImage) || (mode === 'local3dpreview' && localModelFiles.length === 0)"
            @click="generate"
          >
            <span class="inline-block"><i data-lucide="zap" class="w-4 h-4"></i></span>
            <span>{{ generateButtonLabel }}</span>
          </button>
        </div>
      </section>

      <!-- 右侧结果视图 -->
      <section class="flex-1 self-start md:self-stretch min-h-[70vh] md:min-h-0 md:h-full md:max-h-full bg-black/40 md:rounded-r-2xl rounded-2xl border border-slate-700 relative overflow-hidden flex flex-col">
        <!-- 空视图 -->
        <div v-if="view === 'empty'" class="flex-1 flex flex-col items-center justify-center opacity-30 text-center px-6">
          <span :key="mode">
            <i :data-lucide="mode === 'text2image' ? 'image' : 'cuboid'" class="w-24 h-24 mb-4"></i>
          </span>
          <p>
            {{
              mode === 'text2image'
                ? t('studio.emptyView.text2image')
                : mode === 'local3dpreview'
                  ? t('studio.emptyView.local3dpreview')
                  : mode === 'image23d'
                    ? t('studio.emptyView.image23d')
                    : t('studio.emptyView.text23d')
            }}
          </p>
        </div>

        <!-- 加载中 -->
        <div v-else-if="view === 'loading'" class="flex-1 flex flex-col items-center justify-center">
          <div class="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p class="text-indigo-400 font-mono">
            {{
              mode === 'text2image'
                ? t('studio.loading.text2image')
                : mode === 'text23d'
                  ? t('studio.loading.text23d')
                : mode === 'image23d'
                    ? t('studio.loading.image23d')
                : t('studio.loading.local3dpreview')
            }}
          </p>
            <p
            v-if="mode === 'text23d' || mode === 'image23d'"
            class="mt-2 text-sm text-slate-300"
          >
            {{ formatMsg(generationStatusMessage) || t('studio.loading.taskProcessing') }}
          </p>
          <div
            v-if="mode === 'text23d' || mode === 'image23d'"
            class="w-full max-w-md px-6 mt-5"
          >
            <div class="flex items-center justify-between text-xs text-slate-300 mb-1.5">
              <span>{{ t('studio.loading.generationProgress') }}</span>
              <span class="font-mono">{{ displayUnifiedAsyncJobProgress }}%</span>
            </div>
            <div class="h-2.5 rounded-full bg-slate-700/80 overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 transition-[width] duration-500"
                :style="{ width: `${unifiedAsyncJobProgress}%` }"
              ></div>
            </div>
            <p class="mt-2 text-[11px] text-slate-400 text-center">
              {{ t('studio.loading.continueTip') }}
            </p>
          </div>
          <p
            v-if="mode === 'text2image'"
            class="mt-2 text-[11px] text-slate-400 text-center"
          >
            {{ t('studio.loading.switchPageTip') }}
          </p>
        </div>

        <!-- 结果视图 -->
        <div v-else class="relative flex-1 min-h-[24rem] md:min-h-0 group overflow-hidden bg-slate-950">
          <!-- 文生图：生成结果 2D 图，或二次创作参考 3D -->
          <template v-if="mode === 'text2image'">
            <img
              v-if="resultImg"
              :src="resultImg"
              class="absolute inset-0 w-full h-full object-contain bg-slate-900"
              alt="生成的图片"
            />
            <div
              v-else-if="text2imageRemixModelUrl && !viewerLoadFailed"
              ref="viewerContainer"
              class="absolute inset-0 w-full h-full bg-slate-950"
            ></div>
            <div
              v-else
              class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm px-4 text-center"
            >
              <p v-if="viewerLoadFailed && text2imageRemixModelUrl">参考模型加载失败</p>
            </div>
            <div
              v-if="resultImg"
              class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition pointer-events-none"
            ></div>
          </template>

          <!-- 文生3D / 图转3D：显示3D模型 -->
          <template v-else>
            <div
              v-if="
                ((mode === 'text23d' || mode === 'image23d') && activeViewerModelUrl && !viewerLoadFailed)
                || (mode === 'local3dpreview' && (resultUrl || localModelFiles.length > 0) && !viewerLoadFailed)
              "
              ref="viewerContainer"
              class="absolute inset-0 w-full h-full bg-slate-950"
            ></div>
            <img
              v-else-if="resultImg"
              :src="resultImg"
              class="absolute inset-0 w-full h-full object-contain bg-slate-900"
              alt="3D模型预览图"
              @error="(e) => { console.error('预览图加载失败:', resultImg); if (e.target) (e.target as HTMLElement).style.display = 'none' }"
            />
            <div
              v-else
              class="absolute inset-0 flex items-center justify-center text-slate-400"
            >
              <p>{{ mode === 'local3dpreview' ? '本地模型加载失败，请重新选择文件' : (resultUrl ? '3D模型加载失败，已回退预览图' : '等待生成3D模型预览...') }}</p>
            </div>
            <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-50 group-hover:opacity-100 transition pointer-events-none"></div>

            <div
              v-if="renderInitPending"
              class="absolute inset-0 z-20 bg-slate-950/95 flex flex-col items-center justify-center"
            >
              <div class="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p class="text-indigo-300 text-sm">{{ formatMsg(generationStatusMessage) || t('studio.loading.renderInit') }}</p>
              <div class="w-full max-w-md px-4 mt-4">
                <div class="flex items-center justify-between text-xs text-slate-300 mb-1">
                  <span>渲染准备进度</span>
                  <span class="font-mono">{{ displayGenerationProgress }}%</span>
                </div>
                <div class="h-2 rounded-full bg-slate-700 overflow-hidden">
                  <div
                    class="h-full bg-indigo-500 transition-all duration-500"
                    :style="{ width: `${Math.max(0, Math.min(100, generationProgress))}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- 结果操作栏：单行、紧凑，不遮挡预览内容 -->
        <div v-if="view === 'result'" class="border-t border-slate-700/80 bg-slate-950/60 px-3 py-2">
          <div class="flex items-center gap-2 overflow-x-auto whitespace-nowrap">
            <button
              v-if="(mode === 'text23d' || mode === 'image23d') && currentResultPrintable"
              class="shrink-0 bg-emerald-600 hover:bg-emerald-500 px-3 py-2 rounded-lg text-xs md:text-sm font-semibold transition"
              type="button"
              @click="openPrintDialog"
            >
              一键下单
            </button>
            <button
              v-if="(mode === 'text23d' || mode === 'image23d') && !published"
              class="shrink-0 bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded-lg text-xs md:text-sm font-semibold transition"
              type="button"
              :disabled="publishingAssetResolve"
              @click="publishToCommunity"
            >
              {{ publishingAssetResolve ? '处理中...' : '发布' }}
            </button>
            <span
              v-if="(mode === 'text23d' || mode === 'image23d') && published"
              class="shrink-0 px-3 py-2 rounded-lg text-xs md:text-sm font-semibold bg-slate-900/70 border border-slate-700 text-emerald-300"
            >
              已发布
            </span>
            <button
              v-if="mode === 'text2image' && resultImg"
              class="shrink-0 bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded-lg text-xs md:text-sm font-semibold transition"
              type="button"
              @click="downloadImage"
            >
              {{ t('studio.resultActions.downloadImage') }}
            </button>
            <button
              class="shrink-0 bg-slate-900/70 hover:bg-slate-900 px-3 py-2 rounded-lg text-xs md:text-sm font-semibold border border-slate-700 transition"
              type="button"
              @click="startNewCreation"
            >
              {{ t('studio.resultActions.createNew') }}
            </button>
            <button
              v-if="mode === 'text23d' || mode === 'image23d'"
              class="shrink-0 px-3 py-2 rounded-lg text-xs md:text-sm font-semibold border border-slate-700 transition"
              :class="viewModelUrl
                ? 'bg-slate-900/70 hover:bg-slate-900'
                : 'bg-slate-900/40 text-slate-500 cursor-not-allowed'"
              type="button"
              :disabled="!viewModelUrl"
              @click="openViewModel"
            >
              {{ t('studio.resultActions.viewModel') }}
            </button>
          </div>
        </div>

        <!-- 底部提示信息 -->
        <div class="p-3 md:p-4 border-t border-slate-700 text-sm text-slate-300 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div class="min-w-0">
            <template v-if="mode === 'image23d'">
              <span class="flex items-center gap-2 min-w-0" v-if="uploadedImage">
                {{ t('studio.footer.imageLabel') }}：
                <img
                  :src="uploadedImage"
                  :alt="t('studio.image23d.uploadedImageAlt')"
                  class="h-8 w-8 rounded border border-slate-700 object-cover"
                />
              </span>
              <span v-else-if="uploadedFileName" class="block truncate">图片：{{ uploadedFileName }}</span>
            </template>
            <template v-else-if="mode === 'local3dpreview'">
              <span v-if="localModelFiles.length > 0" class="block truncate">
                本地文件：<span class="text-slate-400">{{ localModelFiles.length }} 个（{{ localModelPrimaryFileName || '未命名' }}）</span>
              </span>
            </template>
            <template v-else>
              <span v-if="prompt" class="block truncate">提示词：<span class="text-slate-400">{{ prompt }}</span></span>
              <span v-if="mode === 'text2image' && finalOutputSpec" class="block md:inline md:ml-3 text-sky-300">
                输出：{{ finalOutputSpec.size }}（{{ finalOutputSpec.ratio }}）
              </span>
              <span v-if="mode === 'text2image'" class="block md:inline md:ml-3 text-violet-300">
                风格：{{ t2iStyleLabel }} · 清晰度：{{ t2iResolutionLevelLabel }}
              </span>
            </template>
          </div>
          <div v-if="mode !== 'local3dpreview' && creditsUsed != null" class="text-emerald-300">消耗：{{ creditsUsed }} 积分</div>
        </div>

        <!-- Toast 消息 -->
        <div
          v-if="msg"
          class="absolute left-4 bottom-4 text-sm px-4 py-2 rounded-lg shadow-lg z-20"
          :class="msgType === 'error' ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'"
        >
          {{ msg }}
        </div>
      </section>
    </div>
      </div>

      <!-- 历史记录侧边栏（可折叠；桌面端左列从网格顶部起占满高度，无顶部留白） -->
      <aside
        class="order-2 md:order-none glass-panel flex min-h-0 flex-col rounded-2xl md:rounded-l-2xl md:rounded-r-xl border border-slate-700 overflow-hidden transition-all duration-200 shrink-0 sticky top-4 md:static md:col-start-1 md:row-start-1 md:row-span-2 md:h-full md:max-h-full md:min-h-0 md:self-stretch"
        :class="historySidebarOpen ? 'w-full md:w-72 lg:w-80' : 'w-full md:w-12'"
      >
        <div
          class="shrink-0 p-2 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between cursor-pointer"
          @click="historySidebarOpen = !historySidebarOpen"
        >
          <span v-if="historySidebarOpen" class="text-xs font-bold text-slate-400 uppercase">{{ t('studio.history.title') }}</span>
          <i :data-lucide="historySidebarOpen ? 'panel-left-close' : 'panel-left-open'" class="w-5 h-5 text-slate-400"></i>
        </div>
        <div
          v-show="historySidebarOpen"
          class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-y-contain touch-pan-y p-2 space-y-2 max-h-[min(70dvh,calc(100vh-14rem))] md:max-h-none md:overflow-y-scroll [scrollbar-gutter:stable] [scrollbar-width:thin] md:[scrollbar-color:rgb(71_85_105)_rgb(15_23_42/0.9)] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:rounded-full [&::-webkit-scrollbar-track]:bg-slate-950/80 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-600 hover:[&::-webkit-scrollbar-thumb]:bg-slate-500"
        >
          <template v-if="historyLoading && !displayHistoryItems.length"> <p class="text-xs text-slate-500 py-4 text-center">{{ t('studio.history.loading') }}</p> </template>
          <template v-else-if="!displayHistoryItems.length"> <p class="text-xs text-slate-500 py-4 text-center">{{ t('studio.history.empty') }}</p> </template>
          <template v-else>
            <div
              v-for="item in displayHistoryItems"
              :key="item.id"
              class="rounded-lg border border-slate-600/80 p-2 cursor-pointer hover:bg-slate-800/80 transition flex gap-2"
              :class="item.is_transient ? historyTransientCardClass(item.transient_status) : ''"
              @click="openHistoryDetail(item)"
            >
              <div class="w-14 h-14 rounded bg-slate-800 shrink-0 overflow-hidden flex items-center justify-center">
                <img v-if="item.preview_url" :src="item.preview_url" class="w-full h-full object-cover" alt="" />
                <i
                  v-else
                  :data-lucide="item.mode === 'text2img' ? 'image' : item.mode === 'local3dpreview' ? 'folder-open' : 'box'"
                  class="w-6 h-6 text-slate-500"
                ></i>
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-[10px] px-1 rounded bg-slate-600 text-slate-300">{{ historyModeLabel(item.mode) }}</span>
                  <span
                    v-if="item.is_transient"
                    class="text-[10px] px-1 rounded border"
                    :class="historyTransientBadgeClass(item.transient_status)"
                  >
                    {{ historyTransientLabel(item.transient_status) }}
                  </span>
                </div>
                <p class="text-xs text-slate-300 truncate mt-0.5">{{ historyItemSummary(item) }}</p>
                <p class="text-[10px] text-slate-500">{{ historyRelativeTimeLabel(item) }}</p>
                <template v-if="item.is_transient">
                  <p
                    class="text-[10px] mt-1 truncate"
                    :class="historyTransientMessageClass(item.transient_status)"
                  >
                    {{ item.transient_message || t('studio.history.processing') }}
                  </p>
                  <template v-if="historyTransientShowsProgress(item.transient_status)">
                  <div class="mt-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-500"
                      :style="{ width: `${item.transient_progress || 0}%` }"
                    ></div>
                  </div>
                    <p class="text-[10px] text-slate-500 mt-1">{{ Math.round(item.transient_progress || 0) }}%</p>
                  </template>
                  <p v-else-if="item.expires_at" class="text-[10px] text-slate-500 mt-1">
                    {{ t('studio.history.autoCleanupAfter3Hours') }}
                  </p>
                </template>
              </div>
              <button
                v-if="!item.is_transient"
                type="button"
                class="shrink-0 p-1 text-slate-500 hover:text-red-400 rounded"
                title="删除"
                @click.stop="deleteHistoryItem(item)"
              >
                <i data-lucide="trash-2" class="w-4 h-4"></i>
              </button>
            </div>
          </template>
        </div>
      </aside>
    </div>
    </template>

    <div
      v-if="showStudioAlertDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      @click.self="closeStudioAlertDialog"
    >
      <div
        class="glass-panel w-full max-w-sm rounded-2xl overflow-hidden"
        :class="studioAlertDialogTone === 'warning' ? 'border border-amber-500/30' : 'border border-red-500/30'"
      >
        <div class="flex items-center justify-between border-b border-slate-700 bg-slate-800/50 px-5 py-4">
          <h3
            class="text-base font-bold"
            :class="studioAlertDialogTone === 'warning' ? 'text-amber-300' : 'text-red-300'"
          >
            {{ studioAlertDialogTitle }}
          </h3>
          <button
            type="button"
            class="text-slate-400 transition hover:text-white"
            @click="closeStudioAlertDialog"
          >
            <i data-lucide="x" class="h-5 w-5"></i>
          </button>
        </div>
        <div class="space-y-4 px-5 py-5 text-sm text-slate-200">
          <p>{{ studioAlertDialogMessage }}</p>
          <div class="flex justify-end">
            <button
              type="button"
              class="rounded-lg px-4 py-2 text-sm font-semibold text-white transition"
              :class="studioAlertDialogTone === 'warning' ? 'bg-amber-600 hover:bg-amber-500' : 'bg-red-600 hover:bg-red-500'"
              @click="closeStudioAlertDialog"
            >
              {{ t('studio.alertDialog.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 打印规格选择弹窗 -->
    <div
      v-if="showPrintDialog"
      class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="showPrintDialog = false"
    >
      <div class="glass-panel max-w-md w-full rounded-2xl border border-slate-700 overflow-hidden">
            <div class="p-6 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
              <h3 class="font-bold text-lg">{{ t('studio.printDialog.title') }}</h3>
          <button
            class="text-slate-400 hover:text-white"
            type="button"
            @click="showPrintDialog = false"
          >
            <i data-lucide="x" class="w-5 h-5"></i>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <!-- 高度选择 -->
          <div>
            <label class="text-sm font-bold text-slate-300 mb-2 block">{{ t('studio.printDialog.height') }}</label>
            <div class="grid grid-cols-2 gap-3">
              <button
                class="py-3 px-4 rounded-lg border-2 transition font-bold"
                :class="printHeight === '5cm' ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
                type="button"
                @click="printHeight = '5cm'"
              >
                5cm
              </button>
              <button
                class="py-3 px-4 rounded-lg border-2 transition font-bold"
                :class="printHeight === '10cm' ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
                type="button"
                @click="printHeight = '10cm'"
              >
                10cm
              </button>
            </div>
          </div>

          <!-- 材质选择 -->
          <div>
            <label class="text-sm font-bold text-slate-300 mb-2 block">{{ t('studio.printDialog.material') }}</label>
            <select v-model="printMaterial" class="w-full bg-slate-900 border border-slate-600 rounded-lg p-3 text-slate-200 focus:border-emerald-500 outline-none">
              <option value="PLA_WHITE">{{ t('studio.printDialog.materialPlaWhite') }}</option>
              <!-- <option value="PLA">{{ t('studio.printDialog.materialPla') }}</option> -->
              <!-- <option value="ABS">{{ t('studio.printDialog.materialAbs') }}</option> -->
              <!-- <option value="PETG">{{ t('studio.printDialog.materialPetg') }}</option> -->
            </select>
          </div>

          <!-- 预估克重和价格 -->
          <div class="bg-slate-900/50 rounded-lg p-4 space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-slate-400">{{ t('studio.printDialog.weight') }}：</span>
              <span class="text-slate-200 font-bold">{{ t('studio.printDialog.weightCalc') }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-400">{{ t('studio.printDialog.unitPrice') }}：</span>
              <span class="text-slate-200 font-bold">{{ t('studio.printDialog.weightCalc') }}</span>
            </div>
            <div class="flex justify-between border-t border-slate-700 pt-2 mt-2">
              <span class="text-slate-300 font-bold">{{ t('studio.printDialog.orderAmount') }}：</span>
              <span class="text-emerald-300 font-bold text-lg">{{ t('studio.printDialog.updateAfterSlice') }}</span>
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ t('studio.printDialog.sliceNote') }}</p>
            <div class="mt-2 flex items-center justify-between">
              <p class="text-xs text-slate-500">{{ t('studio.printDialog.plaNote') }}</p>
              <!-- 购买PLA耗材按钮 - 暂时隐藏
              <button
                type="button"
                class="px-3 py-1 rounded border text-xs text-slate-200 hover:bg-white/5"
                @click="goToMarketForPLA"
              >
                {{ t('studio.printDialog.buyPla') }}
              </button>
              -->
            </div>
          </div>
        </div>

        <div class="p-6 border-t border-slate-700 space-y-3">
          <button
            class="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition flex items-center justify-center gap-2"
            type="button"
            :disabled="printBusy"
            @click="confirmPrintOrder"
          >
            <i data-lucide="zap" class="w-4 h-4"></i>
            {{ printBusy ? t('studio.printDialog.creating') : t('studio.printDialog.createOrder') }}
          </button>
          <button
            class="w-full py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition flex items-center justify-center gap-2"
            type="button"
            :disabled="printBusy"
            @click="addToCart"
          >
            <span class="inline-block"><i data-lucide="shopping-cart" class="w-4 h-4"></i></span>
            {{ t('studio.printDialog.addToCart') }}
          </button>
          <button
            class="w-full py-3 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold transition"
            type="button"
            @click="showPrintDialog = false"
          >
            {{ t('studio.printDialog.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <div
      v-if="complianceTipVisible"
      class="pointer-events-none fixed z-[9999] w-[22rem] rounded-md border border-white/15 bg-black/20 px-2.5 py-2 text-[11px] leading-4 text-slate-200 backdrop-blur-sm"
      :style="complianceTipStyle"
      role="tooltip"
    >
      {{ t('studio.complianceHover') }}
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { image23dSummaryFromHistoryParams } from '../lib/studioImage23dDisplay'
import { useAuthStore } from '../stores/auth'
import { applyEmbeddedViewerPostLoad } from '../lib/embeddedViewerSetup'
import { STUDIO_T2I_REMIX_STORAGE_KEY, type StudioT2iRemixPayload } from '../lib/studioT2iRemix'
import * as OV from 'online-3d-viewer'

declare const lucide: any

const { t } = useI18n()

const formatMsg = (v: unknown) => {
  if (typeof v !== 'string') return v
  if (v.startsWith('studio.')) return t(v)
  return v
}
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const complianceTipVisible = ref(false)
const complianceTipStyle = ref<Record<string, string>>({ left: '12px', top: '12px' })

function showComplianceTip(event: MouseEvent | FocusEvent) {
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const rect = target.getBoundingClientRect()
  const tooltipWidth = 352 // 22rem
  const viewportPadding = 12
  let left = rect.left
  if (left + tooltipWidth > window.innerWidth - viewportPadding) {
    left = window.innerWidth - tooltipWidth - viewportPadding
  }
  if (left < viewportPadding) left = viewportPadding
  const top = Math.min(rect.bottom + 8, window.innerHeight - 80)
  complianceTipStyle.value = {
    left: `${left}px`,
    top: `${top}px`
  }
  complianceTipVisible.value = true
}

function hideComplianceTip() {
  complianceTipVisible.value = false
}

// 模式：text2image（文生图）、text23d（文生3D）、image23d（图转3D）、local3dpreview（本地预览）
const mode = ref<'text2image' | 'text23d' | 'image23d' | 'local3dpreview'>('text23d')
const modelRenderMode = ref<'color' | 'white'>('color')
const text3dResultFormat = ref<'GLB' | 'STL'>('STL')
/** STL 可打印与彩色纹理互斥：选 STL 时仅允许白色几何体 */
watch(
  [text3dResultFormat, modelRenderMode],
  () => {
    if (text3dResultFormat.value === 'STL' && modelRenderMode.value === 'color') {
      modelRenderMode.value = 'white'
    }
  },
  { immediate: true }
)
const viewerContainer = ref<HTMLElement | null>(null)
const viewerLoadFailed = ref(false)
let embeddedViewer: any = null
let viewerLoadTimer: number | null = null
const view = ref<'empty' | 'loading' | 'result'>('empty')
const loading = ref(false)
/** 文生图：同步请求期间锁定；文生3D：右侧为 loading 视图时锁定（含提交后轮询直至完成） */
const promptInputLocked = computed(
  () =>
    (mode.value === 'text2image' && loading.value) || (mode.value === 'text23d' && view.value === 'loading')
)
/** 文生3D：生成过程中锁定格式 / 模式等参数，避免被任务结果回填覆盖用户选择 */
const text23dConfigLocked = computed(
  () => mode.value === 'text23d' && view.value === 'loading',
)
const creditsUsed = ref<number | null>(null)
const resultUrl = ref<string | null>(null)
const resultDownloadUrl = ref<string | null>(null)
const resultDownloadFormat = ref<string | null>(null)
const resultImg = ref('')
/** 文生图「二次创作」：右侧参考 3D（来自作品详情页，生成新图成功后清除） */
const text2imageRemixModelUrl = ref<string | null>(null)
const text2imageRemixModelFormat = ref<string | null>(null)
const viewerCandidateUrls = computed(() => {
  const candidates: string[] = []
  // try to accept URLs even without extension when we have a known format
  const pushCandidate = (url?: string | null, modelFormat?: string | null) => {
    const normalized = typeof url === 'string' ? url.trim() : ''
    if (!normalized) return
    if (!isViewerRenderableFormat(normalized, modelFormat || undefined)) return
    if (!candidates.includes(normalized)) candidates.push(normalized)
  }

  if (mode.value === 'local3dpreview') {
    pushCandidate(resultUrl.value, resultDownloadFormat.value)
    return candidates
  }

  if (mode.value === 'text23d' || mode.value === 'image23d') {
    pushCandidate(resultDownloadUrl.value, resultDownloadFormat.value)
    pushCandidate(resultUrl.value, resultDownloadFormat.value)
  }

  return candidates
})
const activeViewerModelUrl = computed(() => viewerCandidateUrls.value[0] || null)
const assetId = ref<string | null>(null)
const published = ref(false)
const currentResultFormat = ref<'GLB' | 'STL' | null>(null)
const lastSubmittedStudioJobId = ref<string | null>(null)
const publishingAssetResolve = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'error'>('ok')
const showStudioAlertDialog = ref(false)
const studioAlertDialogTone = ref<'danger' | 'warning'>('danger')
const studioAlertDialogTitle = ref('')
const studioAlertDialogMessage = ref('')
const generationProgress = ref(0)
const generationStatusMessage = ref('')
const generationTargetProgress = ref(0)
const displayGenerationProgress = computed(() => Math.round(generationProgress.value))

/** 文生3D/图生3D 异步任务：右侧加载进度与左侧历史条共用侧栏任务的 transient_progress，避免双进度条不一致 */
const activeSidebarJobForLoading = computed(() => {
  if (view.value !== 'loading') return null
  if (mode.value !== 'text23d' && mode.value !== 'image23d') return null
  const id = selectedTransientJobId.value
  if (!id) return null
  const job = sidebarJobItems.value.find((j) => j.job_id === id)
  if (!job || !job.is_transient || isStudioTerminalStatus(job.transient_status)) return null
  return job
})

const unifiedAsyncJobProgress = computed(() => {
  const job = activeSidebarJobForLoading.value
  if (job) {
    return clampStudioProgress(job.transient_progress ?? 0, 0, 100)
  }
  return clampStudioProgress(generationProgress.value, 0, 100)
})

const displayUnifiedAsyncJobProgress = computed(() => Math.round(unifiedAsyncJobProgress.value))
const text2imageEstimatedCredits = 20
type HunyuanGenerateType = 'Normal' | 'LowPoly' | 'Geometry' | 'Sketch'
const hy3dBaseCreditsMap: Record<HunyuanGenerateType, number> = {
  Normal: 40,
  LowPoly: 50,
  Geometry: 30,
  Sketch: 50
}
const hy3dExtraCredits = {
  multiViewImages: 20,
  enablePBR: 20,
  faceCount: 20,
  resultFormat: 10
}
const renderInitPending = ref(false)
let progressTimer: number | null = null
let renderReadyResolver: ((ready: boolean) => void) | null = null
let renderReadyTimeout: number | null = null
function calcHunyuan3DCredits(
  generateType: HunyuanGenerateType,
  options?: { hasMultiViewImages?: boolean; enablePBR?: boolean; hasFaceCount?: boolean; hasResultFormat?: boolean }
) {
  let total = hy3dBaseCreditsMap[generateType] || 40
  if (options?.hasMultiViewImages) total += hy3dExtraCredits.multiViewImages
  if (options?.enablePBR) total += hy3dExtraCredits.enablePBR
  if (options?.hasFaceCount) total += hy3dExtraCredits.faceCount
  if (options?.hasResultFormat) total += hy3dExtraCredits.resultFormat
  return total
}

// 造梦历史侧边栏
const historySidebarOpen = ref(true)
type PersistedHistoryItem = {
  id: string
  mode: string
  prompt: string
  params: Record<string, unknown>
  preview_url: string | null
  model_url?: string | null
  download_model_url?: string | null
  download_model_format?: string | null
  selected_model_url?: string | null
  selected_model_format?: string | null
  render_model_url?: string | null
  render_model_format?: string | null
  gcode_source_model_url?: string | null
  gcode_source_model_format?: string | null
  asset_id: string | null
  is_published?: boolean
  created_at: string
}
type TransientHistoryStatus =
  | 'SUBMITTED'
  | 'PENDING'
  | 'QUEUED'
  | 'WAITING'
  | 'RUNNING'
  | 'PROCESSING'
  | 'IN_PROGRESS'
  | 'FAILED'
  | 'CANCELLED'

type SidebarJobItem = {
  id: string
  job_id: string
  mode: 'text23d' | 'image23d'
  prompt: string
  params: Record<string, unknown>
  preview_url: string | null
  model_url?: string | null
  asset_id: string | null
  created_at: string
  finished_at?: string | null
  expires_at?: string | null
  is_transient: true
  transient_status: TransientHistoryStatus
  transient_progress: number
  transient_message: string
}
type DisplayHistoryItem = (PersistedHistoryItem & {
  is_transient?: false
  transient_status?: undefined
  transient_progress?: undefined
  transient_message?: undefined
  finished_at?: undefined
  expires_at?: undefined
}) | SidebarJobItem
const historyItems = ref<PersistedHistoryItem[]>([])
const sidebarJobItems = ref<SidebarJobItem[]>([])
const historyLoading = ref(false)
const selectedTransientJobId = ref<string | null>(null)
const selectedHistoryItemId = ref<string | null>(null)
const displayHistoryItems = computed<DisplayHistoryItem[]>(() => {
  const merged = [...sidebarJobItems.value, ...historyItems.value]
  return merged.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

function historyModeLabel(mode: string) {
  if (mode === 'text2img') return '文生图'
  if (mode === 'text23d') return '文生3D'
  if (mode === 'image23d') return '图生3D'
  if (mode === 'local3dpreview') return '本地预览'
  return mode
}

/** 相对「锚点时间」的展示文案（用于已完成记录：从完成时刻起算） */
function formatElapsedSince(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return t('studio.timeAgo.justNow')
  if (diff < 3600000) return t('studio.timeAgo.minutesAgo', { minutes: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('studio.timeAgo.hoursAgo', { hours: Math.floor(diff / 3600000) })
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function historyRelativeTimeLabel(item: DisplayHistoryItem) {
  if ('is_transient' in item && item.is_transient) {
    if (!isStudioTerminalStatus(item.transient_status)) {
      return t('studio.transientStatus.processing')
    }
    const anchor = item.finished_at || item.created_at
    return formatElapsedSince(anchor)
  }
  return formatElapsedSince(item.created_at)
}

function resetStudioResultView() {
  stopProgressTimer()
  resolveRenderReady(false)
  destroyEmbeddedViewer()
  showPrintDialog.value = false
  selectedTransientJobId.value = null
  selectedHistoryItemId.value = null
  lastSubmittedStudioJobId.value = null
  loading.value = false
  view.value = 'empty'
  resultImg.value = ''
  resultUrl.value = null
  resultDownloadUrl.value = null
  resultDownloadFormat.value = null
  assetId.value = null
  currentResultFormat.value = null
  published.value = false
  publishingAssetResolve.value = false
  creditsUsed.value = null
  viewerLoadFailed.value = false
  generationProgress.value = 0
  generationTargetProgress.value = 0
  generationStatusMessage.value = ''
  renderInitPending.value = false
  skipViewerRenderForLastResult.value = false
  finalOutputSpec.value = null
  msg.value = ''
}

function openStudioAlertDialog(options: { title: string; message: string; tone?: 'danger' | 'warning' }) {
  studioAlertDialogTitle.value = options.title
  studioAlertDialogMessage.value = options.message
  studioAlertDialogTone.value = options.tone || 'danger'
  showStudioAlertDialog.value = true
}

function closeStudioAlertDialog() {
  showStudioAlertDialog.value = false
}

function startNewCreation() {
  closeStudioAlertDialog()
  resetStudioResultView()
  if (mode.value === 'text2image' || mode.value === 'text23d') {
    prompt.value = ''
    return
  }
  if (mode.value === 'image23d') {
    clearUploadedImage()
    return
  }
  if (mode.value === 'local3dpreview') {
    clearLocalModelFiles()
  }
}

function openTaskFailureDialog(kind: 'FAILED' | 'CANCELLED') {
  if (kind === 'FAILED') {
    openStudioAlertDialog({
      title: t('studio.alertDialog.failedTitle'),
      message: t('studio.alertDialog.failedRefunded'),
      tone: 'danger'
    })
  } else {
    openStudioAlertDialog({
      title: t('studio.alertDialog.cancelledTitle'),
      message: t('studio.alertDialog.cancelledMessage'),
      tone: 'warning'
    })
  }
}

function historyItemSummary(item: DisplayHistoryItem) {
  const trimmed = typeof item.prompt === 'string' ? item.prompt.trim() : ''
  if (trimmed) return trimmed
  if (item.mode === 'image23d') {
    const fromParams = image23dSummaryFromHistoryParams(
      item.params as Record<string, unknown> | undefined
    )
    if (fromParams) return fromParams
    if (item.preview_url) return t('studio.historyItemSummary.referenceImage')
    return t('studio.historyItemSummary.noPrompt')
  }
  return t('studio.historyItemSummary.noPrompt')
}

/** 造梦历史：带 Token 请求后端，从数据库按当前用户查询并展示 */
async function loadHistory() {
  if (!auth.isAuthed) return
  historyLoading.value = true
  try {
    const res = await api.studio.getHistory({ page: 1, page_size: 50 })
    historyItems.value = (res.items || []).map((item) => ({
      ...item,
      prompt: item.prompt || '',
      params: normalizeHistoryParams(item.params),
    }))
    nextTick(() => renderIcons())
  } catch {
    historyItems.value = []
  } finally {
    historyLoading.value = false
  }
}

function upsertSidebarJobItem(item: SidebarJobItem) {
  const idx = sidebarJobItems.value.findIndex((existing) => existing.job_id === item.job_id)
  if (idx >= 0) {
    sidebarJobItems.value[idx] = {
      ...sidebarJobItems.value[idx],
      ...item,
      transient_progress: item.transient_status === 'FAILED' || item.transient_status === 'CANCELLED'
        ? item.transient_progress || 0
        : Math.max(sidebarJobItems.value[idx].transient_progress || 0, item.transient_progress || 0),
    }
  } else {
    sidebarJobItems.value = [item, ...sidebarJobItems.value]
  }
  if (selectedTransientJobId.value === item.job_id && !isStudioTerminalStatus(item.transient_status)) {
    void setLoadingPreviewForSidebarJob(
      sidebarJobItems.value.find((existing) => existing.job_id === item.job_id) || item,
      { preserveProgress: true }
    )
  }
}

function removeSidebarJobItem(jobId: string) {
  sidebarJobItems.value = sidebarJobItems.value.filter((item) => item.job_id !== jobId)
}

function normalizeHistoryParams(params: unknown): Record<string, unknown> {
  const raw = params && typeof params === 'object' ? { ...(params as Record<string, unknown>) } : {}
  const generationParamsRaw = raw.generation_params
  if (typeof generationParamsRaw === 'string') {
    try {
      raw.generation_params = JSON.parse(generationParamsRaw) as Record<string, unknown>
    } catch {
      raw.generation_params = {}
    }
  } else if (!generationParamsRaw || typeof generationParamsRaw !== 'object') {
    raw.generation_params = {}
  }

  const paramNotesRaw = raw.param_notes
  if (typeof paramNotesRaw === 'string') {
    try {
      raw.param_notes = JSON.parse(paramNotesRaw) as string[]
    } catch {
      raw.param_notes = []
    }
  } else if (!Array.isArray(paramNotesRaw)) {
    raw.param_notes = []
  }

  return raw
}

function buildSidebarHistoryItemFromJob(
  detail: {
    job_id: string
    mode: 'text23d' | 'image23d' | null
    status: TransientHistoryStatus
    progress: number
    message: string
    prompt?: string | null
    created_at?: string | null
    finished_at?: string | null
    expires_at?: string | null
    asset_id?: string | null
    preview_url?: string | null
    generation_params?: Record<string, any> | null
    param_notes?: string[] | null
    credits_used?: number
  },
  seed?: Partial<SidebarJobItem>
): SidebarJobItem | null {
  if (!detail.mode) return null
  const progressBand = getStudioProgressBand(detail.status, detail.message)
  const backendProgress = clampStudioProgress(Math.round(detail.progress || 0))
  const seedProgress = clampStudioProgress(seed?.transient_progress || 0)
  const nextProgress = isStudioTerminalStatus(detail.status)
    ? backendProgress
    : clampStudioProgress(
        Math.max(
          seedProgress,
          backendProgress,
          deriveStudioElapsedProgress(detail.status, detail.message, detail.created_at, seedProgress),
          progressBand.floor
        ),
        progressBand.floor,
        progressBand.ceiling
      )
  const generationParams =
    detail.generation_params && typeof detail.generation_params === 'object'
      ? (detail.generation_params as Record<string, unknown>)
      : {}
  const generateTypeRaw =
    typeof generationParams.GenerateType === 'string'
      ? generationParams.GenerateType
      : (typeof generationParams.generate_type === 'string' ? generationParams.generate_type : '')
  const normalizedGenerateType = String(generateTypeRaw || '').trim().toLowerCase()
  const derivedWithTexture = normalizedGenerateType
    ? !(normalizedGenerateType === 'geometry' || normalizedGenerateType.endsWith('_white'))
    : undefined
  const seedWithTexture = typeof seed?.params?.with_texture === 'boolean'
    ? seed?.params?.with_texture
    : undefined
  const normalizedParams = normalizeHistoryParams({
    with_texture: seedWithTexture ?? derivedWithTexture,
    generation_params: detail.generation_params || {},
    param_notes: detail.param_notes || [],
    credits_used: detail.credits_used || 0,
    ...(seed?.params || {})
  })
  return {
    id: `job:${detail.job_id}`,
    job_id: detail.job_id,
    mode: detail.mode,
    prompt: typeof detail.prompt === 'string' ? detail.prompt : (seed?.prompt || ''),
    params: Object.keys(normalizedParams).length ? normalizedParams : normalizeHistoryParams(seed?.params || {}),
    preview_url: detail.preview_url || seed?.preview_url || null,
    model_url: null,
    asset_id: detail.asset_id || null,
    created_at: seed?.created_at || detail.created_at || new Date().toISOString(),
    finished_at: detail.finished_at || seed?.finished_at || null,
    expires_at: detail.expires_at || seed?.expires_at || null,
    is_transient: true,
    transient_status: detail.status,
    transient_progress: nextProgress,
    transient_message: detail.message || t('studio.history.processing')
  }
}

function historyTransientLabel(status: TransientHistoryStatus) {
  if (status === 'FAILED') return t('studio.transientStatus.failed')
  if (status === 'CANCELLED') return t('studio.transientStatus.cancelled')
  if (status === 'SUBMITTED') return t('studio.transientStatus.submitted')
  if (status === 'PENDING' || status === 'QUEUED' || status === 'WAITING') return t('studio.transientStatus.queued')
  return t('studio.transientStatus.processing')
}

function historyTransientBadgeClass(status: TransientHistoryStatus) {
  if (status === 'FAILED') return 'bg-red-500/15 text-red-300 border-red-400/30'
  if (status === 'CANCELLED') return 'bg-amber-500/15 text-amber-300 border-amber-400/30'
  return 'bg-indigo-500/20 text-indigo-300 border-indigo-400/30'
}

function historyTransientCardClass(status: TransientHistoryStatus) {
  if (status === 'FAILED') return 'border-red-500/40 bg-red-500/5'
  if (status === 'CANCELLED') return 'border-amber-500/40 bg-amber-500/5'
  return 'border-indigo-500/40 bg-indigo-500/5'
}

function historyTransientMessageClass(status: TransientHistoryStatus) {
  if (status === 'FAILED') return 'text-red-300'
  if (status === 'CANCELLED') return 'text-amber-300'
  return 'text-indigo-300'
}

function historyTransientShowsProgress(status: TransientHistoryStatus) {
  return !['FAILED', 'CANCELLED'].includes(status)
}

async function setLoadingPreviewForSidebarJob(item: SidebarJobItem, options?: { preserveProgress?: boolean }) {
  const targetMode = item.mode === 'image23d' ? 'image23d' : 'text23d'
  if (mode.value !== targetMode) {
    mode.value = targetMode
    await nextTick()
  }
  selectedTransientJobId.value = item.job_id
  lastSubmittedStudioJobId.value = item.job_id
  applyHistoryParamsToPanel(targetMode, item.params || {}, { force: true })
  prompt.value = item.prompt || ''
  uploadedImage.value = targetMode === 'image23d' ? (item.preview_url || null) : null
  uploadedImageDataUrl.value = targetMode === 'image23d' && isImageDataUrl(item.preview_url) ? item.preview_url : null
  uploadedFileName.value = targetMode === 'image23d' && item.preview_url ? t('studio.historyItemSummary.referenceImage') : ''
  resultImg.value = item.preview_url || ''
  resultUrl.value = null
  resultDownloadUrl.value = null
  resultDownloadFormat.value = null
  assetId.value = null
  currentResultFormat.value = null
  published.value = false
  viewerLoadFailed.value = false
  renderInitPending.value = false
  skipViewerRenderForLastResult.value = false
  generationStatusMessage.value = item.transient_message || 'studio.loading.taskProcessing'
  const nextProgress = Math.max(1, Math.min(99, item.transient_progress || 0))
  if (options?.preserveProgress) {
    if (generationProgress.value <= 0) {
      generationProgress.value = nextProgress
      generationTargetProgress.value = nextProgress
    } else {
      setProgressTarget(nextProgress)
    }
  } else {
    generationProgress.value = nextProgress
    generationTargetProgress.value = generationProgress.value
  }
  view.value = 'loading'
  startProgressTimer()
}

function applyHistoryParamsToPanel(
  targetMode: 'text2image' | 'text23d' | 'image23d' | 'local3dpreview',
  params: Record<string, unknown>,
  options?: { force?: boolean }
) {
  if (targetMode === 'text2image') {
    const ratio = typeof params.aspect_ratio === 'string' ? params.aspect_ratio : ''
    const level = typeof params.resolution_level === 'string' ? params.resolution_level.toLowerCase() : ''
    const size = typeof params.output_size === 'string'
      ? params.output_size
      : (typeof params.image_size === 'string' ? params.image_size : '')
    const style = typeof params.style === 'string' ? params.style.toLowerCase() : 'auto'
    if (isT2IRatio(ratio)) {
      t2iAspectRatio.value = ratio
    } else if (size) {
      t2iAspectRatio.value = inferT2IRatioFromSize(size)
    }
    if (isT2IResolutionLevel(level)) {
      t2iResolutionLevel.value = level
    } else if (size) {
      t2iResolutionLevel.value = inferT2IResolutionLevelFromSize(size, t2iAspectRatio.value)
    }
    if (isT2IStyle(style)) {
      t2iStyle.value = style
    } else {
      t2iStyle.value = 'auto'
    }
    return
  }

  if (targetMode === 'text23d') {
    // 当前是文生3D 且右侧仍处于 loading 阶段时，不回写参数到左侧面板，
    // 避免覆盖用户在提交前选择的输出格式等配置。
    if (!options?.force && mode.value === 'text23d' && view.value === 'loading') {
      return
    }
    if (typeof params.with_texture === 'boolean') {
      modelRenderMode.value = params.with_texture ? 'color' : 'white'
    }
    let generationParams: Record<string, unknown> = {}
    if (params.generation_params && typeof params.generation_params === 'object') {
      generationParams = params.generation_params as Record<string, unknown>
    } else if (typeof params.generation_params === 'string') {
      try {
        generationParams = JSON.parse(params.generation_params) as Record<string, unknown>
      } catch {
        generationParams = {}
      }
    } else {
      generationParams = params as Record<string, unknown>
    }
    if (typeof generationParams.ResultFormat === 'string') {
      text3dResultFormat.value = generationParams.ResultFormat.toUpperCase() === 'STL' ? 'STL' : 'GLB'
    } else if (typeof (params as any).result_format === 'string') {
      text3dResultFormat.value = String((params as any).result_format).toUpperCase() === 'STL' ? 'STL' : 'GLB'
    } else {
      // 兼容旧数据：此前 GLB 未显式写入 generation_params，缺失时按 GLB 还原。
      text3dResultFormat.value = 'GLB'
    }
    return
  }

  if (targetMode === 'image23d') {
    const withTexture = typeof params.with_texture === 'boolean' ? params.with_texture : image3dDerivedWithTexture.value
    let generationParams: Record<string, unknown> = {}
    if (params.generation_params && typeof params.generation_params === 'object') {
      generationParams = params.generation_params as Record<string, unknown>
    } else if (typeof params.generation_params === 'string') {
      try {
        generationParams = JSON.parse(params.generation_params) as Record<string, unknown>
      } catch {
        generationParams = {}
      }
    } else {
      generationParams = params as Record<string, unknown>
    }

    const model = typeof generationParams.Model === 'string' ? generationParams.Model : ''
    if (model === '3.0' || model === '3.1') {
      image3dOptions.value.model = model
    }

    const generateType = typeof generationParams.GenerateType === 'string' ? generationParams.GenerateType : ''
    const normalizedGenerateType = generateType.toLowerCase()
    if (normalizedGenerateType === 'lowpoly') {
      image3dOptions.value.structure_mode = withTexture ? 'LOWPOLY_COLOR' : 'LOWPOLY_WHITE'
    } else if (normalizedGenerateType === 'sketch') {
      image3dOptions.value.structure_mode = withTexture ? 'SKETCH_COLOR' : 'SKETCH_WHITE'
    } else {
      image3dOptions.value.structure_mode = withTexture ? 'AUTO_COLOR' : 'AUTO_WHITE'
    }

    const faceCount = Number(generationParams.FaceCount)
    if (Number.isFinite(faceCount) && faceCount > 0) {
      image3dOptions.value.face_count = Math.round(faceCount)
    }

    if (typeof generationParams.EnablePBR === 'boolean') {
      image3dOptions.value.enable_pbr = generationParams.EnablePBR
    }

    if (typeof generationParams.PolygonType === 'string') {
      const polygon = generationParams.PolygonType.toLowerCase()
      if (polygon === 'triangle' || polygon === 'quadrilateral') {
        image3dOptions.value.polygon_type = polygon
      }
    }

    if (typeof generationParams.ResultFormat === 'string') {
      const fmt = generationParams.ResultFormat.toUpperCase()
      if (fmt === 'STL' || fmt === 'GLB') {
        image3dOptions.value.result_format = fmt
      } else {
        image3dOptions.value.result_format = 'GLB'
      }
    } else {
      // 兼容旧数据：ResultFormat 缺失时按 GLB 还原，避免切换历史后误跳 STL。
      image3dOptions.value.result_format = 'GLB'
    }
    return
  }

  if (targetMode === 'local3dpreview') {
    const primary = typeof params.primary_file === 'string' ? params.primary_file : ''
    if (primary) {
      localModelPrimaryFileName.value = primary
    }
  }
}

async function openHistoryDetail(item: DisplayHistoryItem) {
  if (item.is_transient) {
    selectedHistoryItemId.value = null
    resetStudioResultView()
    if (item.transient_status === 'FAILED') {
      openTaskFailureDialog('FAILED')
    } else if (item.transient_status === 'CANCELLED') {
      openTaskFailureDialog('CANCELLED')
    } else {
      await setLoadingPreviewForSidebarJob(item)
    }
    return
  }
  closeStudioAlertDialog()
  resetStudioResultView()
  selectedHistoryItemId.value = item.id

  const modeMap: Record<string, 'text2image' | 'text23d' | 'image23d' | 'local3dpreview'> = {
    text2img: 'text2image',
    text23d: 'text23d',
    image23d: 'image23d',
    local3dpreview: 'local3dpreview'
  }
  const targetMode = modeMap[item.mode] || 'text23d'
  if (mode.value !== targetMode) {
    mode.value = targetMode
    await nextTick()
  }

  const historyModelUrl = item.render_model_url || item.model_url || null
  let historyDownloadUrl = item.selected_model_url || item.download_model_url || null
  if (
    (!historyModelUrl || !historyDownloadUrl)
    && item.asset_id
    && (targetMode === 'text23d' || targetMode === 'image23d')
    && !item.selected_model_format
  ) {
    try {
      const assetDetail = await api.assets.detail(item.asset_id)
      historyDownloadUrl = historyDownloadUrl || assetDetail?.model_url || null
    } catch {
      // ignore
    }
  }

  const historyParams = item.params && typeof item.params === 'object' ? item.params : {}
  applyHistoryParamsToPanel(targetMode, historyParams as Record<string, unknown>, { force: true })
  prompt.value = targetMode === 'local3dpreview' ? '' : (item.prompt || '')
  uploadedImage.value = targetMode === 'image23d' ? (item.preview_url || null) : null
  uploadedImageDataUrl.value = targetMode === 'image23d' && isImageDataUrl(item.preview_url) ? item.preview_url : null
  uploadedFileName.value = targetMode === 'image23d' && !item.prompt ? t('studio.historyItemSummary.referenceImage') : ''
  resultImg.value = item.preview_url || (targetMode === 'text2image' ? (historyModelUrl || '') : '')
  resultUrl.value = historyModelUrl
  resultDownloadUrl.value = historyDownloadUrl
  resultDownloadFormat.value = item.selected_model_format || item.download_model_format || getFileExtFromUrl(historyDownloadUrl)
  assetId.value = item.asset_id || null
  published.value = !!item.is_published
  currentResultFormat.value = inferResultFormatFromParams(historyParams as Record<string, unknown>)
  if (!currentResultFormat.value) {
    const ext = getFileExtFromUrl(historyDownloadUrl || historyModelUrl)
    if (ext === 'stl') currentResultFormat.value = 'STL'
    if (ext === 'glb' || ext === 'gltf') currentResultFormat.value = 'GLB'
  }
  if (targetMode === 'text2image') {
    const ratio = typeof (historyParams as Record<string, unknown>).aspect_ratio === 'string'
      ? (historyParams as Record<string, unknown>).aspect_ratio as string
      : t2iAspectRatio.value
    const size = typeof (historyParams as Record<string, unknown>).output_size === 'string'
      ? (historyParams as Record<string, unknown>).output_size as string
      : (typeof (historyParams as Record<string, unknown>).image_size === 'string'
        ? (historyParams as Record<string, unknown>).image_size as string
        : t2iOutputSize.value)
    finalOutputSpec.value = { ratio: isT2IRatio(ratio) ? ratio : inferT2IRatioFromSize(size), size }
  } else {
    finalOutputSpec.value = null
  }
  view.value = 'result'

  const is3D = targetMode === 'text23d' || targetMode === 'image23d' || targetMode === 'local3dpreview'
  const renderable = targetMode === 'local3dpreview'
    ? (!!resultUrl.value && isViewerRenderableFormat(resultUrl.value, undefined))
    : viewerCandidateUrls.value.length > 0
  skipViewerRenderForLastResult.value = is3D && !renderable
  viewerLoadFailed.value = is3D && !renderable

  renderIcons()
  if (targetMode === 'local3dpreview' && is3D && resultUrl.value && renderable) {
    await mountEmbeddedViewer(resultUrl.value)
    } else if (is3D && !resultImg.value) {
    toastErr(t('studio.messages.historyItemMissingModel'))
  }
}

async function deleteHistoryItem(item: DisplayHistoryItem) {
  if (item.is_transient) return
  if (item.is_published) {
    openStudioAlertDialog({
      title: t('studio.alertDialog.deleteBlockedTitle'),
      message: t('studio.alertDialog.deleteBlockedMessage'),
      tone: 'warning'
    })
    return
  }
  try {
    await api.studio.deleteHistory(item.id)
    historyItems.value = historyItems.value.filter((i) => i.id !== item.id)
  } catch (e: any) {
    const errorMessage = e?.message || t('assetDetail.deleteFailed')
    if (typeof errorMessage === 'string' && errorMessage.includes(t('studio.alertDialog.deleteBlockedKeyword'))) {
      openStudioAlertDialog({
        title: t('studio.alertDialog.deleteBlockedTitle'),
        message: t('studio.alertDialog.deleteBlockedMessage'),
        tone: 'warning'
      })
    } else {
      msg.value = errorMessage
      msgType.value = 'error'
    }
  }
  nextTick(() => lucide?.createIcons?.())
}

// 打印相关的状态
type PrintMaterial = 'PLA_WHITE'

const showPrintDialog = ref(false)
const printHeight = ref<'5cm' | '10cm'>('5cm')
const printMaterial = ref<PrintMaterial>('PLA_WHITE')
const printBusy = ref(false)
// 估算结果
const estimatedWeight = ref<number | null>(null)
const estimatedTotalPrice = ref<number | null>(null)
const pricePerGram = ref<number>(2)

async function fetchPrintEstimate() {
  try {
    const payload: any = {
      height: printHeight.value,
      material: printMaterial.value,
    }
    const res = await api.printOrders.estimateWeight(payload)
    estimatedWeight.value = res.estimated_weight ?? null
    pricePerGram.value = typeof res.price_per_gram === 'number' ? res.price_per_gram : pricePerGram.value
    estimatedTotalPrice.value = typeof res.total_price === 'number' ? res.total_price : null
  } catch (e) {
    estimatedWeight.value = null
    estimatedTotalPrice.value = null
    pricePerGram.value = printMaterial.value.startsWith('PLA') ? 2 : pricePerGram.value
  }
}

const defaultPrintMaterial = computed<PrintMaterial>(() => {
  // 当前仅支持 PLA_WHITE，其他材质暂时禁用
  // if (mode.value === 'text23d') {
  //   return modelRenderMode.value === 'white' ? 'PLA_WHITE' : 'PLA'
  // }
  // if (mode.value === 'image23d') {
  //   return image3dDerivedWithTexture.value ? 'PLA' : 'PLA_WHITE'
  // }
  // return 'PLA'
  return 'PLA_WHITE'
})

function openPrintDialog() {
  printMaterial.value = defaultPrintMaterial.value
  showPrintDialog.value = true
}

function goToMarketForPLA() {
  router.push({ path: '/market', query: { material: 'PLA' } })
  showPrintDialog.value = false
}

watch([showPrintDialog, printHeight, printMaterial], ([open]) => {
  if (open) void fetchPrintEstimate()
})

type StudioJobNotification = {
  job_id: string
  mode: 'text23d' | 'image23d'
  status: 'COMPLETED' | 'FAILED' | 'CANCELLED'
  message: string
  prompt: string
  asset_id?: string | null
  created_at?: string | null
  finished_at?: string | null
}

type StudioSidebarJob = {
  job_id: string
  mode: 'text23d' | 'image23d'
  status: TransientHistoryStatus
  progress: number
  message: string
  prompt: string
  preview_url?: string | null
  asset_id?: string | null
  created_at?: string | null
  finished_at?: string | null
  expires_at?: string | null
  texture_mode?: 'color' | 'white'
  generation_params?: Record<string, any> | null
  param_notes?: string[] | null
  credits_used?: number
}

let studioNotificationTimer: number | null = null
let studioSidebarTimer: number | null = null
let studioSidebarProgressTimer: number | null = null
let studioNotificationStartedAt = 0
const handledStudioTerminalJobIds = new Set<string>()
const trackedStudioJobTimers = new Map<string, number>()

function isStudioTerminalStatus(status: string) {
  return status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED'
}

function clampStudioProgress(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value))
}

function parseStudioTime(value?: string | null) {
  if (!value) return null
  const ts = Date.parse(value)
  return Number.isFinite(ts) ? ts : null
}

function getStudioProgressBand(status: string, message?: string | null) {
  const normalizedStatus = String(status || '').toUpperCase()
  const normalizedMessage = String(message || '')
  const isFinalizing = normalizedMessage.includes('结果整理中')

  if (normalizedStatus === 'COMPLETED') return { floor: 100, ceiling: 100, drift: 0 }
  if (normalizedStatus === 'FAILED' || normalizedStatus === 'CANCELLED') return { floor: 0, ceiling: 99, drift: 0 }
  if (isFinalizing) return { floor: 90, ceiling: 96, drift: 0.06 }
  if (normalizedStatus === 'SUBMITTED') return { floor: 8, ceiling: 14, drift: 0.08 }
  if (normalizedStatus === 'PENDING' || normalizedStatus === 'QUEUED' || normalizedStatus === 'WAITING') {
    return { floor: 16, ceiling: 30, drift: 0.12 }
  }
  if (normalizedStatus === 'RUNNING' || normalizedStatus === 'PROCESSING' || normalizedStatus === 'IN_PROGRESS') {
    return { floor: 34, ceiling: 86, drift: 0.18 }
  }
  return { floor: 24, ceiling: 72, drift: 0.12 }
}

function deriveStudioElapsedProgress(
  status: string,
  message?: string | null,
  createdAt?: string | null,
  seedProgress = 0
) {
  const band = getStudioProgressBand(status, message)
  const createdAtMs = parseStudioTime(createdAt)
  const elapsedSeconds = createdAtMs ? Math.max(0, (Date.now() - createdAtMs) / 1000) : 0
  const statusName = String(status || '').toUpperCase()

  let derived = band.floor
  if (statusName === 'SUBMITTED') {
    derived = band.floor + elapsedSeconds * 0.45
  } else if (statusName === 'PENDING' || statusName === 'QUEUED' || statusName === 'WAITING') {
    derived = band.floor + elapsedSeconds * 0.22
  } else if (statusName === 'RUNNING' || statusName === 'PROCESSING' || statusName === 'IN_PROGRESS') {
    derived = band.floor + elapsedSeconds * 0.18
  } else if (String(message || '').includes('结果整理中')) {
    derived = band.floor + elapsedSeconds * 0.12
  } else {
    derived = band.floor + elapsedSeconds * 0.16
  }

  return clampStudioProgress(Math.max(seedProgress, derived), band.floor, band.ceiling)
}

function stopTrackingStudioJob(jobId: string) {
  const timer = trackedStudioJobTimers.get(jobId)
  if (timer !== undefined) {
    window.clearTimeout(timer)
    trackedStudioJobTimers.delete(jobId)
  }
}

function stopAllTrackedStudioJobs() {
  for (const timer of trackedStudioJobTimers.values()) {
    window.clearTimeout(timer)
  }
  trackedStudioJobTimers.clear()
}

async function finalizeTrackedStudioJob(detail: {
  job_id: string
  status: 'COMPLETED' | 'FAILED' | 'CANCELLED'
  message?: string
  mode: 'text23d' | 'image23d' | null
  prompt?: string | null
  created_at?: string | null
  finished_at?: string | null
  preview_url?: string | null
  model_url?: string | null
  download_model_url?: string | null
  download_model_format?: string | null
  model_format?: string | null
  selected_model_url?: string | null
  selected_model_format?: string | null
  render_model_url?: string | null
  render_model_format?: string | null
  gcode_source_model_url?: string | null
  gcode_source_model_format?: string | null
  asset_id?: string | null
  texture_mode?: 'color' | 'white'
  generation_params?: Record<string, any> | null
  param_notes?: string[] | null
  credits_used?: number
}) {
  if (selectedTransientJobId.value === detail.job_id) {
    selectedTransientJobId.value = null
    stopProgressTimer()
    generationStatusMessage.value = detail.message || ''
    if (detail.status === 'COMPLETED') {
      const targetMode = detail.mode === 'image23d' ? 'image23d' : 'text23d'
      if (detail.mode) {
        applyHistoryParamsToPanel(
          targetMode,
          normalizeHistoryParams({
            generation_params: detail.generation_params || {},
            param_notes: detail.param_notes || [],
            credits_used: detail.credits_used || 0,
          }),
          { force: true }
        )
      }
      prompt.value = detail.prompt || ''
      resultImg.value = detail.preview_url || ''
      resultUrl.value = detail.render_model_url || detail.model_url || null
      resultDownloadUrl.value = detail.selected_model_url || detail.download_model_url || null
      resultDownloadFormat.value = detail.selected_model_format || detail.download_model_format || getFileExtFromUrl(detail.selected_model_url || detail.download_model_url || null)
      assetId.value = detail.asset_id || null
      const backendFmt = String(detail.model_format || '').toUpperCase()
      if (backendFmt === 'STL' || backendFmt === 'GLB') {
        currentResultFormat.value = backendFmt as 'STL' | 'GLB'
      } else {
        currentResultFormat.value = inferResultFormatFromParams({ generation_params: detail.generation_params || {} })
      }
      viewerLoadFailed.value = false
      view.value = 'result'
    } else {
      view.value = 'empty'
    }
  }
  removeSidebarJobItem(detail.job_id)
  await loadHistory()
  await syncSidebarJobs()
}

function scheduleTrackStudioJob(jobId: string) {
  if (!jobId || trackedStudioJobTimers.has(jobId) || !auth.isAuthed) return

  const poll = async () => {
    if (!auth.isAuthed) {
      stopTrackingStudioJob(jobId)
      return
    }
    try {
      const detail = await api.studio.queryJob(jobId)
      if (isStudioTerminalStatus(detail.status)) {
        stopTrackingStudioJob(jobId)
        await finalizeTrackedStudioJob({
          job_id: detail.job_id,
          status: detail.status,
          message: detail.message,
          mode: detail.mode,
          prompt: detail.prompt,
          created_at: detail.created_at,
          finished_at: detail.finished_at,
          preview_url: detail.preview_url,
          model_url: detail.model_url,
          download_model_url: detail.download_model_url,
          model_format: detail.model_format,
          selected_model_url: detail.selected_model_url,
          selected_model_format: detail.selected_model_format,
          render_model_url: detail.render_model_url,
          render_model_format: detail.render_model_format,
          gcode_source_model_url: detail.gcode_source_model_url,
          gcode_source_model_format: detail.gcode_source_model_format,
          asset_id: detail.asset_id,
          texture_mode: detail.texture_mode,
          generation_params: detail.generation_params,
          param_notes: detail.param_notes,
          credits_used: detail.credits_used
        })
        return
      }

      const existing = sidebarJobItems.value.find((item) => item.job_id === detail.job_id)
      const sidebarItem = buildSidebarHistoryItemFromJob(
        {
          job_id: detail.job_id,
          mode: detail.mode,
          status: detail.status,
          progress: detail.progress,
          message: detail.message,
          prompt: detail.prompt,
          created_at: detail.created_at,
          finished_at: detail.finished_at,
          preview_url: detail.preview_url,
          asset_id: detail.asset_id,
          generation_params: detail.generation_params,
          param_notes: detail.param_notes,
          credits_used: detail.credits_used
        },
        existing
      )
      if (sidebarItem) {
        upsertSidebarJobItem(sidebarItem)
      }
      const nextTimer = window.setTimeout(poll, 5000)
      trackedStudioJobTimers.set(jobId, nextTimer)
    } catch {
      const nextTimer = window.setTimeout(poll, 8000)
      trackedStudioJobTimers.set(jobId, nextTimer)
    }
  }

  const initialTimer = window.setTimeout(poll, 2500)
  trackedStudioJobTimers.set(jobId, initialTimer)
}

async function pollStudioNotifications() {
  if (!auth.isAuthed) return
  try {
    const res = await api.studio.getJobNotifications(10)
    const items = (res?.items || []) as StudioJobNotification[]
    if (items.length === 0) return
    let shouldReloadHistory = false
    for (const item of items) {
      const eventTimeText = item.finished_at || item.created_at || ''
      const eventTime = eventTimeText ? new Date(eventTimeText).getTime() : Number.NaN
      const shouldToast = !studioNotificationStartedAt
        || Number.isNaN(eventTime)
        || eventTime >= (studioNotificationStartedAt - 2000)
      const alreadyHandled = handledStudioTerminalJobIds.has(item.job_id)
      if (item.status === 'COMPLETED') {
        removeSidebarJobItem(item.job_id)
        shouldReloadHistory = true
        if (shouldToast && !alreadyHandled) {
          toastOk(item.message || t('studio.messages.task3dCompleted'))
        }
      } else if (item.status === 'CANCELLED') {
        if (selectedTransientJobId.value === item.job_id) {
          resetStudioResultView()
          openTaskFailureDialog('CANCELLED')
        }
        if (shouldToast && !alreadyHandled) {
          toastErr(item.message || t('studio.messages.task3dCancelled'))
        }
      } else if (shouldToast && !alreadyHandled) {
        if (selectedTransientJobId.value === item.job_id) {
          resetStudioResultView()
          openTaskFailureDialog('FAILED')
        }
        toastErr(item.message || t('studio.messages.task3dFailed'))
      }
      handledStudioTerminalJobIds.add(item.job_id)
      stopTrackingStudioJob(item.job_id)
      await api.studio.ackJobNotification(item.job_id)
    }
    if (shouldReloadHistory) {
      await loadHistory()
    }
    await syncSidebarJobs()
  } catch {
    // ignore
  }
}

async function syncSidebarJobs() {
  if (!auth.isAuthed) {
    sidebarJobItems.value = []
    return
  }
  try {
    const res = await api.studio.getSidebarJobs(20)
    const nextItems = (res?.items || [])
      .map((item) => buildSidebarHistoryItemFromJob(item as StudioSidebarJob, sidebarJobItems.value.find((existing) => existing.job_id === item.job_id)))
      .filter((item): item is SidebarJobItem => !!item)
    const nextJobIds = new Set(nextItems.map((item) => item.job_id))
    const preservedItems = sidebarJobItems.value.filter(
      (item) => !nextJobIds.has(item.job_id) && !isStudioTerminalStatus(item.transient_status)
    )
    const mergedItems = [...nextItems, ...preservedItems]
    sidebarJobItems.value = mergedItems.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    for (const item of mergedItems) {
      if (!isStudioTerminalStatus(item.transient_status)) {
        scheduleTrackStudioJob(item.job_id)
      }
    }
  } catch {
    // ignore
  }
}

function startStudioNotificationPolling() {
  if (studioNotificationTimer !== null) return
  studioNotificationTimer = window.setInterval(() => {
    void pollStudioNotifications()
  }, 15000)
}

function stopStudioNotificationPolling() {
  if (studioNotificationTimer !== null) {
    window.clearInterval(studioNotificationTimer)
    studioNotificationTimer = null
  }
  studioNotificationStartedAt = 0
}

function startStudioSidebarPolling() {
  if (studioSidebarTimer !== null) return
  studioSidebarTimer = window.setInterval(() => {
    void syncSidebarJobs()
  }, 5000)
}

function stopStudioSidebarPolling() {
  if (studioSidebarTimer !== null) {
    window.clearInterval(studioSidebarTimer)
    studioSidebarTimer = null
  }
}

function startStudioSidebarProgressTimer() {
  if (studioSidebarProgressTimer !== null) return
  studioSidebarProgressTimer = window.setInterval(() => {
    sidebarJobItems.value = sidebarJobItems.value.map((item) => {
      if (!item.is_transient || isStudioTerminalStatus(item.transient_status)) return item
      const band = getStudioProgressBand(item.transient_status, item.transient_message)
      const derived = deriveStudioElapsedProgress(
        item.transient_status,
        item.transient_message,
        item.created_at,
        item.transient_progress || 0
      )
      const current = clampStudioProgress(Math.max(item.transient_progress || 0, derived), 0, band.ceiling)
      if (current >= band.ceiling || band.drift <= 0) {
        return {
          ...item,
          transient_progress: current,
        }
      }
      return {
        ...item,
        transient_progress: clampStudioProgress(current + band.drift, band.floor, band.ceiling),
      }
    })
  }, 1000)
}

function stopStudioSidebarProgressTimer() {
  if (studioSidebarProgressTimer !== null) {
    window.clearInterval(studioSidebarProgressTimer)
    studioSidebarProgressTimer = null
  }
}

function renderIcons() {
  nextTick(() => {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons()
    }
  })
}

// 从 URL 参数读取模式，并消费「二次创作」sessionStorage（须在 mode 变更的 nextTick 之后写入 prompt）
onMounted(async () => {
  syncModeFromRoute()
  await nextTick()
  hydrateT2iRemixFromSessionStorage()
  auth.hydrate()
  if (auth.isAuthed) {
    await loadHistory()
    await syncSidebarJobs()
    startStudioSidebarPolling()
    startStudioSidebarProgressTimer()
  }
  renderIcons()
  window.addEventListener('resize', resizeEmbeddedViewer)
})

/** 切换账号 / 登出时清空造梦侧栏与历史缓存并重新拉取，避免看到上一用户的记录 */
watch(
  () => [auth.token ?? '', String(auth.user?.id ?? '')] as const,
  async ([token, userId], prev) => {
    const prevToken = prev?.[0] ?? ''
    const prevUserId = prev?.[1] ?? ''
    if (token === prevToken && userId === prevUserId) return

    if (!token) {
      stopAllTrackedStudioJobs()
      handledStudioTerminalJobIds.clear()
      studioNotificationStartedAt = 0
      sidebarJobItems.value = []
      historyItems.value = []
      selectedTransientJobId.value = null
      stopStudioSidebarPolling()
      stopStudioNotificationPolling()
      stopStudioSidebarProgressTimer()
      return
    }

    // 仅 JWT 轮换、用户 id 未变：不重复打历史接口
    if (userId && userId === prevUserId && token !== prevToken) {
      return
    }

    stopAllTrackedStudioJobs()
    handledStudioTerminalJobIds.clear()
    studioNotificationStartedAt = 0
    sidebarJobItems.value = []
    historyItems.value = []
    selectedTransientJobId.value = null

    startStudioSidebarPolling()
    startStudioNotificationPolling()
    startStudioSidebarProgressTimer()

    historyLoading.value = true
    try {
      await loadHistory()
      await syncSidebarJobs()
    } finally {
      historyLoading.value = false
    }
  }
)

onBeforeUnmount(() => {
  stopProgressTimer()
  resolveRenderReady(false)
  stopStudioSidebarPolling()
  stopStudioSidebarProgressTimer()
  stopAllTrackedStudioJobs()
  window.removeEventListener('resize', resizeEmbeddedViewer)
  destroyEmbeddedViewer()
})

watch(mode, async (nextMode, prevMode) => {
  stopProgressTimer()
  resolveRenderReady(false)
  renderIcons()
  destroyEmbeddedViewer()
  selectedTransientJobId.value = null
  lastSubmittedStudioJobId.value = null
  text2imageRemixModelUrl.value = null
  text2imageRemixModelFormat.value = null
  // 切换模式时重置状态
  view.value = 'empty'
  resultImg.value = ''
  resultUrl.value = null
  resultDownloadUrl.value = null
  resultDownloadFormat.value = null
  assetId.value = null
  currentResultFormat.value = null
  published.value = false
  creditsUsed.value = null
  viewerLoadFailed.value = false
  generationProgress.value = 0
  generationTargetProgress.value = 0
  generationStatusMessage.value = ''
  renderInitPending.value = false
  skipViewerRenderForLastResult.value = false
  finalOutputSpec.value = null

  // 四种模式的输入面板彼此独立，切换模式时不继承上一个模式的输入内容。
  if (nextMode !== prevMode) {
    prompt.value = ''
  }

  if (prevMode === 'image23d' && nextMode !== 'image23d') {
    clearUploadedImage()
  }

  if (prevMode === 'local3dpreview' && nextMode !== 'local3dpreview') {
    clearLocalModelFiles()
  }
})

watch(
  [mode, view, activeViewerModelUrl, resultDownloadUrl, text2imageRemixModelUrl, text2imageRemixModelFormat, resultImg],
  async () => {
    const t2iRemix3d =
      mode.value === 'text2image' &&
      view.value === 'result' &&
      !resultImg.value &&
      !!text2imageRemixModelUrl.value &&
      isViewerRenderableFormat(text2imageRemixModelUrl.value, text2imageRemixModelFormat.value ?? undefined)

    if (t2iRemix3d) {
      await mountEmbeddedViewer([text2imageRemixModelUrl.value!])
      return
    }

    const is3DMode = mode.value === 'text23d' || mode.value === 'image23d' || mode.value === 'local3dpreview'
    if (!is3DMode || view.value !== 'result') {
      destroyEmbeddedViewer()
      return
    }
    if (mode.value === 'local3dpreview') {
      return
    }
    if (!activeViewerModelUrl.value) {
      destroyEmbeddedViewer()
      return
    }
    await mountEmbeddedViewer(viewerCandidateUrls.value)
  }
)

watch(
  () => route.fullPath,
  async () => {
    if (route.path !== '/studio') return
    syncModeFromRoute()
    await nextTick()
    hydrateT2iRemixFromSessionStorage()
  }
)

function startProgressTimer() {
  if (progressTimer !== null) return
  progressTimer = window.setInterval(() => {
    if (generationProgress.value < generationTargetProgress.value) {
      const gap = generationTargetProgress.value - generationProgress.value
      const step = gap > 25 ? 2.6 : gap > 12 ? 1.6 : gap > 5 ? 0.8 : 0.35
      generationProgress.value = Math.min(generationTargetProgress.value, generationProgress.value + step)
    } else if (
      view.value === 'loading'
      && (mode.value === 'text23d' || mode.value === 'image23d')
      && selectedTransientJobId.value
    ) {
      const activeJob = sidebarJobItems.value.find((item) => item.job_id === selectedTransientJobId.value)
      const band = getStudioProgressBand(activeJob?.transient_status || 'RUNNING', generationStatusMessage.value)
      const derived = activeJob
        ? deriveStudioElapsedProgress(
            activeJob.transient_status,
            activeJob.transient_message,
            activeJob.created_at,
            generationTargetProgress.value
          )
        : generationTargetProgress.value
      generationTargetProgress.value = Math.max(generationTargetProgress.value, derived)
      if (band.drift > 0 && generationTargetProgress.value < band.ceiling) {
        generationTargetProgress.value = clampStudioProgress(generationTargetProgress.value + band.drift, band.floor, band.ceiling)
      }
      if (generationProgress.value < generationTargetProgress.value) {
        generationProgress.value = Math.min(generationTargetProgress.value, generationProgress.value + Math.max(band.drift, 0.08))
      }
    }
  }, 250)
}

function stopProgressTimer() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer)
    progressTimer = null
  }
}

function setProgressTarget(target: number, hard = false) {
  const clamped = Math.max(0, Math.min(100, target))
  generationTargetProgress.value = hard ? clamped : Math.max(generationTargetProgress.value, clamped)
  startProgressTimer()
}

function resolveRenderReady(ready: boolean) {
  if (renderReadyTimeout !== null) {
    window.clearTimeout(renderReadyTimeout)
    renderReadyTimeout = null
  }
  if (renderReadyResolver) {
    const resolver = renderReadyResolver
    renderReadyResolver = null
    resolver(ready)
  }
}

function destroyEmbeddedViewer() {
  clearViewerLoadTimer()
  if (embeddedViewer && typeof embeddedViewer.Destroy === 'function') {
    embeddedViewer.Destroy()
  }
  embeddedViewer = null
  if (viewerContainer.value) {
    viewerContainer.value.innerHTML = ''
  }
}

function resizeEmbeddedViewer() {
  if (embeddedViewer && typeof embeddedViewer.Resize === 'function') {
    embeddedViewer.Resize()
  }
}

function clearViewerLoadTimer() {
  if (viewerLoadTimer !== null) {
    window.clearTimeout(viewerLoadTimer)
    viewerLoadTimer = null
  }
}

async function mountEmbeddedViewer(modelUrl: string | string[]) {
  await nextTick()
  if (!viewerContainer.value) {
    return
  }

  const queue = (Array.isArray(modelUrl) ? modelUrl : [modelUrl])
    .map((url) => typeof url === 'string' ? url.trim() : '')
    .filter(Boolean)

  if (queue.length === 0) {
    destroyEmbeddedViewer()
    viewerLoadFailed.value = true
    resolveRenderReady(false)
    return
  }

  if (renderInitPending.value) {
    generationStatusMessage.value = 'studio.loading.renderInit'
    setProgressTarget(Math.max(96, generationProgress.value))
  }

  const buildViewerRequestUrl = (sourceUrl: string) => {
    let modelFileName = 'model.glb'
    try {
      const fileName = (sourceUrl.startsWith('/') ? sourceUrl.split('?')[0] : new URL(sourceUrl).pathname)
        .split('/')
        .filter(Boolean)
        .pop()
      if (fileName) {
        modelFileName = fileName.includes('.') ? fileName : `${fileName}.glb`
      }
    } catch (e) {
      console.warn('模型URL解析失败，使用默认文件名:', e)
    }

    if (sourceUrl.startsWith('/api/studio/local-preview-file/')) {
      return sourceUrl
    }
    if (sourceUrl.startsWith('/uploads/')) {
      const base = import.meta.env.DEV
        ? 'http://localhost:3000'
        : (typeof window !== 'undefined'
            ? `${window.location.protocol}//${window.location.hostname}:3000`
            : 'http://117.50.91.35:3000')
      return `${base}${sourceUrl}`
    }
    const proxyToken = `v${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
    return `/api/studio/model-proxy/${proxyToken}/${encodeURIComponent(modelFileName)}?url=${encodeURIComponent(sourceUrl)}`
  }

    const attemptLoad = (index: number) => {
    const currentUrl = queue[index]
    destroyEmbeddedViewer()
    viewerLoadFailed.value = false

      const viewerOptions: any = {
      backgroundColor: new OV.RGBAColor(20, 30, 52, 255),
        onModelLoaded: () => {
        clearViewerLoadTimer()
        viewerLoadFailed.value = false
        applyEmbeddedViewerPostLoad(embeddedViewer, { logLabel: 'Studio' })
        resizeEmbeddedViewer()
        if (renderInitPending.value) {
          generationStatusMessage.value = 'studio.loading.renderReady'
        }
        resolveRenderReady(true)
      },
      onModelLoadFailed: () => {
        clearViewerLoadTimer()
        console.warn('[Studio] EmbeddedViewer failed to load model URL:', currentUrl)
        const hasNext = index < queue.length - 1
        destroyEmbeddedViewer()
        if (hasNext) {
          void attemptLoad(index + 1)
          return
        }
        viewerLoadFailed.value = true
        resolveRenderReady(false)
        if (resultImg.value) {
          toastErr(t('studio.messages.modelLoadFailed'))
        }
      }
    }

    embeddedViewer = new OV.EmbeddedViewer(viewerContainer.value, viewerOptions)
    embeddedViewer.LoadModelFromUrlList([buildViewerRequestUrl(currentUrl)])
    viewerLoadTimer = window.setTimeout(() => {
      console.warn('[Studio] EmbeddedViewer load timeout for URL:', currentUrl)
      const hasNext = index < queue.length - 1
      destroyEmbeddedViewer()
      if (hasNext) {
        void attemptLoad(index + 1)
        return
      }
      viewerLoadFailed.value = true
      resolveRenderReady(false)
      if (resultImg.value) {
        toastErr(t('studio.messages.modelLoadTimeout'))
      }
    }, 60000)
    resizeEmbeddedViewer()
  }

  attemptLoad(0)
}

async function mountLocalEmbeddedViewer(files: File[]) {
  await nextTick()
  if (!viewerContainer.value) return
  if (!files || files.length === 0) {
    throw new Error(t('studio.messages.noLocalModelFile'))
  }

  destroyEmbeddedViewer()
  viewerLoadFailed.value = false

  const viewerOptions: any = {
    backgroundColor: new OV.RGBAColor(20, 30, 52, 255),
    onModelLoaded: () => {
      clearViewerLoadTimer()
      viewerLoadFailed.value = false
      applyEmbeddedViewerPostLoad(embeddedViewer, { logLabel: 'Studio' })
      resizeEmbeddedViewer()
    },
    onModelLoadFailed: () => {
      clearViewerLoadTimer()
      destroyEmbeddedViewer()
      viewerLoadFailed.value = true
      toastErr(t('studio.messages.localModelLoadFailed'))
    }
  }
  embeddedViewer = new OV.EmbeddedViewer(viewerContainer.value, viewerOptions)
  embeddedViewer.LoadModelFromFileList(files as any)
  viewerLoadTimer = window.setTimeout(() => {
    destroyEmbeddedViewer()
    viewerLoadFailed.value = true
    toastErr(t('studio.messages.localModelLoadTimeout'))
  }, 60000)
  resizeEmbeddedViewer()
}
const lang = ref<'cn' | 'en'>('cn')
const translatingPrompt = ref(false)
const optimizingPrompt = ref(false)
const promptAssistantEnabled = false//恢复AI翻译！！！！恢复，只要把这个改成 true 就行
const prompt = ref('一只穿着宇航服的柴犬，4k画质')
type T2IRatio = '1:1' | '3:4' | '4:3' | '16:9' | '9:16'
type T2IResolutionLevel = '720p' | '1k'
type T2IStyle = 'auto' | 'cinematic' | 'photoreal' | 'anime' | 'illustration' | 'watercolor' | 'pixel'
const t2iAspectRatio = ref<T2IRatio>('1:1')
const t2iResolutionLevel = ref<T2IResolutionLevel>('1k')
const t2iStyle = ref<T2IStyle>('auto')
const finalOutputSpec = ref<{ size: string; ratio: string } | null>(null)
const t2iRatioValues: T2IRatio[] = ['1:1', '3:4', '4:3', '16:9', '9:16']
const t2iResolutionLevelValues: T2IResolutionLevel[] = ['720p', '1k']
const t2iStyleValues: T2IStyle[] = ['auto', 'cinematic', 'photoreal', 'anime', 'illustration', 'watercolor', 'pixel']
const t2iShortEdgeByLevel: Record<T2IResolutionLevel, number> = {
  '720p': 720,
  '1k': 1024
}
const t2iResolutionLevelLabelMap: Record<T2IResolutionLevel, string> = {
  '720p': '720p',
  '1k': '1K'
}
const t2iRatioFloatMap: Record<T2IRatio, number> = {
  '1:1': 1,
  '3:4': 3 / 4,
  '4:3': 4 / 3,
  '16:9': 16 / 9,
  '9:16': 9 / 16
}

function parseT2ISize(size?: string | null) {
  if (!size) return null
  const m = size.trim().toLowerCase().match(/^(\d{2,5})x(\d{2,5})$/)
  if (!m) return null
  const width = Number(m[1])
  const height = Number(m[2])
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null
  return { width, height }
}

function inferT2IRatioFromSize(size?: string | null): T2IRatio {
  const parsed = parseT2ISize(size)
  if (!parsed) return '1:1'
  const target = parsed.width / parsed.height
  const entries = Object.entries(t2iRatioFloatMap) as Array<[T2IRatio, number]>
  return entries.reduce((best, current) => {
    const [bestRatio, bestFloat] = best
    const [currRatio, currFloat] = current
    return Math.abs(currFloat - target) < Math.abs(bestFloat - target) ? [currRatio, currFloat] : [bestRatio, bestFloat]
  })[0]
}

function isT2IRatio(value: string): value is T2IRatio {
  return t2iRatioValues.includes(value as T2IRatio)
}

function isT2IResolutionLevel(value: string): value is T2IResolutionLevel {
  return t2iResolutionLevelValues.includes(value as T2IResolutionLevel)
}

function isT2IStyle(value: string): value is T2IStyle {
  return t2iStyleValues.includes(value as T2IStyle)
}

function inferT2IResolutionLevelFromSize(size?: string | null, ratioHint?: T2IRatio): T2IResolutionLevel {
  const parsed = parseT2ISize(size)
  if (!parsed) return '1k'
  const ratio = ratioHint || inferT2IRatioFromSize(size)
  return t2iResolutionLevelValues.reduce((best, level) => {
    const expected = parseT2ISize(calcT2IOutputSize(level, ratio))
    if (!expected) return best
    const expectedDiff = Math.abs(expected.width - parsed.width) + Math.abs(expected.height - parsed.height)
    const bestExpected = parseT2ISize(calcT2IOutputSize(best, ratio))
    if (!bestExpected) return level
    const bestDiff = Math.abs(bestExpected.width - parsed.width) + Math.abs(bestExpected.height - parsed.height)
    return expectedDiff < bestDiff ? level : best
  }, '1k' as T2IResolutionLevel)
}

function calcT2IOutputSize(level: T2IResolutionLevel, ratio: T2IRatio) {
  const [aStr, bStr] = ratio.split(':')
  const a = Number(aStr)
  const b = Number(bStr)
  const shortEdge = t2iShortEdgeByLevel[level]

  let width = shortEdge
  let height = shortEdge
  if (a > b) {
    height = shortEdge
    width = Math.round((height * a) / b)
  } else if (a < b) {
    width = shortEdge
    height = Math.round((width * b) / a)
  }

  const maxEdge = Math.max(width, height)
  if (maxEdge > 2048) {
    const scale = 2048 / maxEdge
    width = Math.round(width * scale)
    height = Math.round(height * scale)
  }
  width = Math.max(256, Math.floor(width / 2) * 2)
  height = Math.max(256, Math.floor(height / 2) * 2)
  return `${width}x${height}`
}

const t2iOutputSize = computed(() => calcT2IOutputSize(t2iResolutionLevel.value, t2iAspectRatio.value))
const t2iResolutionLevelLabel = computed(() => t2iResolutionLevelLabelMap[t2iResolutionLevel.value] || '1K')
const t2iStyleLabel = computed(() => {
  try {
    return t(`studio.t2i.styles.${t2iStyle.value}`)
  } catch {
    return t('studio.t2i.styles.auto')
  }
})

// 图转3D相关
const fileInput = ref<HTMLInputElement | null>(null)
const uploadedImage = ref<string | null>(null)
const uploadedImageDataUrl = ref<string | null>(null)
const uploadedFileName = ref<string>('')
const imageDropActive = ref(false)
const localModelInput = ref<HTMLInputElement | null>(null)
const localModelFiles = ref<File[]>([])
const localModelPrimaryFileName = ref('')
const localModelFileNamesPreview = computed(() => localModelFiles.value.slice(0, 6).map((f) => f.name))
const skipViewerRenderForLastResult = ref(false)
const viewModelUrl = computed(() => resultDownloadUrl.value || resultUrl.value || null)
const image3dOptions = ref<{
  model: '3.0' | '3.1'
  structure_mode: 'AUTO_COLOR' | 'AUTO_WHITE' | 'LOWPOLY_COLOR' | 'LOWPOLY_WHITE' | 'SKETCH_COLOR' | 'SKETCH_WHITE'
  face_count: number
  enable_pbr: boolean
  polygon_type: 'triangle' | 'quadrilateral'
  result_format: 'GLB' | 'STL'
}>({
  model: '3.0',
  structure_mode: 'AUTO_WHITE',
  face_count: 500000,
  enable_pbr: false,
  polygon_type: 'triangle',
  result_format: 'STL'
})
/** STL 可打印与彩色生成类型互斥：仅 AUTO/LOWPOLY/SKETCH 的 *_WHITE */
watch(
  [() => image3dOptions.value.result_format, () => image3dOptions.value.structure_mode],
  () => {
    if (image3dOptions.value.result_format !== 'STL') return
    const sm = image3dOptions.value.structure_mode
    if (sm === 'AUTO_COLOR') image3dOptions.value.structure_mode = 'AUTO_WHITE'
    else if (sm === 'LOWPOLY_COLOR') image3dOptions.value.structure_mode = 'LOWPOLY_WHITE'
    else if (sm === 'SKETCH_COLOR') image3dOptions.value.structure_mode = 'SKETCH_WHITE'
  },
  { immediate: true }
)
const image3dDerivedGenerateType = computed<'AUTO' | 'LowPoly' | 'Sketch'>(() => {
  const mode = image3dOptions.value.structure_mode
  if (mode.startsWith('LOWPOLY')) return 'LowPoly'
  if (mode.startsWith('SKETCH')) return 'Sketch'
  return 'AUTO'
})
const image3dDerivedWithTexture = computed(() => image3dOptions.value.structure_mode.endsWith('COLOR'))
const image3dFaceCountMin = computed(() => (image3dDerivedGenerateType.value === 'LowPoly' ? 3000 : 10000))
const image3dFaceCountChanged = computed(() => Math.round(image3dOptions.value.face_count) !== 500000)
const image3dResultFormatChanged = computed(() => image3dOptions.value.result_format === 'STL')
const text3dResultFormatChanged = computed(() => text3dResultFormat.value === 'STL')
const text3dGenerateTypeForCredits = computed<HunyuanGenerateType>(() => (modelRenderMode.value === 'color' ? 'Normal' : 'Geometry'))
const image3dGenerateTypeForCredits = computed<HunyuanGenerateType>(() => {
  const generateType = image3dDerivedGenerateType.value
  if (generateType === 'LowPoly' || generateType === 'Sketch') return generateType
  return image3dDerivedWithTexture.value ? 'Normal' : 'Geometry'
})
const text3dEstimatedCredits = computed(() =>
  calcHunyuan3DCredits(text3dGenerateTypeForCredits.value, {
    hasResultFormat: text3dResultFormatChanged.value
  })
)
const image3dEstimatedCredits = computed(() =>
  calcHunyuan3DCredits(image3dGenerateTypeForCredits.value, {
    hasMultiViewImages: false,
    enablePBR: image3dOptions.value.enable_pbr,
    hasFaceCount: image3dFaceCountChanged.value,
    hasResultFormat: image3dResultFormatChanged.value
  })
)
const estimatedGenerateCredits = computed(() => {
  if (mode.value === 'text2image') return text2imageEstimatedCredits
  if (mode.value === 'text23d') return text3dEstimatedCredits.value
  if (mode.value === 'image23d') return image3dEstimatedCredits.value
  return 0
})
const generateButtonLabel = computed(() => {
  if (loading.value) return t('studio.generateButton.generating')
  if (mode.value === 'text2image') return t('studio.generateButton.text2image', { credits: estimatedGenerateCredits.value })
  if (mode.value === 'text23d') return t('studio.generateButton.text23d', { credits: estimatedGenerateCredits.value })
  if (mode.value === 'image23d') return t('studio.generateButton.image23d', { credits: estimatedGenerateCredits.value })
  return t('studio.generateButton.local3dpreview')
})



function toastOk(t: string) {
  msgType.value = 'ok'
  msg.value = t
  setTimeout(() => (msg.value = ''), 2500)
}
function toastErr(t: string) {
  msgType.value = 'error'
  msg.value = t
  setTimeout(() => (msg.value = ''), 3500)
}

function detectPromptLang(text: string): 'cn' | 'en' | null {
  const hasChinese = /[\u4e00-\u9fff]/.test(text)
  const hasEnglish = /[a-zA-Z]/.test(text)
  if (hasChinese && !hasEnglish) return 'cn'
  if (hasEnglish && !hasChinese) return 'en'
  return null
}

async function toggleLang() {
  const rawText = prompt.value.trim()
  if (!rawText) {
    toastErr(t('studio.messages.pleaseInputPrompt'))
    return
  }
  if (translatingPrompt.value) return

  const detectedLang = detectPromptLang(rawText)
  const sourceLang = detectedLang || lang.value
  const targetLang = sourceLang === 'cn' ? 'en' : 'zh'

  translatingPrompt.value = true
  try {
    const res = await api.studio.translatePrompt({
      text: rawText,
      source_lang: sourceLang === 'cn' ? 'zh' : 'en',
      target_lang: targetLang
    })
    const translated = (res?.translated_text || '').trim()
    if (!translated) {
      throw new Error(t('studio.messages.translateResultEmpty'))
    }
    prompt.value = translated
    lang.value = targetLang === 'en' ? 'en' : 'cn'
    toastOk(lang.value === 'en' ? t('studio.messages.translatedToEn') : t('studio.messages.translatedToCn'))
  } catch (e: any) {
    toastErr(e?.message || t('studio.messages.translateFailed'))
  } finally {
    translatingPrompt.value = false
  }
}

async function optimizePromptWithAssistant() {
  const rawText = prompt.value.trim()
  if (!rawText) {
    toastErr(t('studio.messages.pleaseInputPromptOptimize'))
    return
  }
  if (optimizingPrompt.value) return
  if (mode.value !== 'text2image' && mode.value !== 'text23d') {
    toastErr(t('studio.messages.optimizeNotSupported'))
    return
  }

  const detectedLang = detectPromptLang(rawText)
  const sourceLang = detectedLang || lang.value

  optimizingPrompt.value = true
  try {
    const res = await api.studio.optimizePrompt({
      text: rawText,
      mode: mode.value,
      source_lang: sourceLang === 'cn' ? 'zh' : sourceLang === 'en' ? 'en' : 'auto'
    })
    const optimized = (res?.optimized_text || '').trim()
    if (!optimized) {
      throw new Error(t('studio.messages.optimizeResultEmpty'))
    }
    prompt.value = optimized
    const optimizedLang = detectPromptLang(optimized)
    if (optimizedLang) {
      lang.value = optimizedLang
    }
    toastOk(t('studio.messages.promptOptimized'))
  } catch (e: any) {
    toastErr(e?.message || t('studio.messages.optimizeFailed'))
  } finally {
    optimizingPrompt.value = false
  }
}

function triggerFileInput() {
  fileInput.value?.click()
}
function applyUploadedImageFile(file: File) {
  if (!file.type.startsWith('image/')) {
    toastErr('请上传图片文件')
    return
  }

  uploadedFileName.value = file.name
  const reader = new FileReader()
  reader.onload = (e) => {
    const dataUrl = e.target?.result as string
    uploadedImage.value = dataUrl
    uploadedImageDataUrl.value = dataUrl
  }
  reader.readAsDataURL(file)
}

function handleFileUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  applyUploadedImageFile(file)
}

function handleImageDragEnter() {
  imageDropActive.value = true
}

function handleImageDragOver() {
  imageDropActive.value = true
}

function handleImageDragLeave(e: DragEvent) {
  const currentTarget = e.currentTarget as HTMLElement | null
  const relatedTarget = e.relatedTarget as Node | null
  if (currentTarget && relatedTarget && currentTarget.contains(relatedTarget)) {
    return
  }
  imageDropActive.value = false
}

function handleImageDrop(e: DragEvent) {
  imageDropActive.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  applyUploadedImageFile(file)
}

function clearUploadedImage() {
  uploadedImage.value = null
  uploadedImageDataUrl.value = null
  uploadedFileName.value = ''
  imageDropActive.value = false
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function triggerLocalModelInput() {
  localModelInput.value?.click()
}

function clearLocalModelFiles() {
  localModelFiles.value = []
  localModelPrimaryFileName.value = ''
  if (localModelInput.value) {
    localModelInput.value.value = ''
  }
}

function handleLocalModelUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (files.length === 0) return

  if (files.length > 1) {
    toastErr('本地预览目前仅支持上传 1 个 GLB 文件')
    return
  }
  const file = files[0]
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  if (ext !== 'glb') {
    toastErr('本地预览当前仅支持 GLB 格式，请先转换后再上传')
    return
  }

  localModelFiles.value = [file]
  localModelPrimaryFileName.value = file.name
  viewerLoadFailed.value = false
  toastOk('已选择 GLB 文件')
}

watch(
  () => image3dOptions.value.structure_mode,
  () => {
    const generateType = image3dDerivedGenerateType.value
    const minFaceCount = generateType === 'LowPoly' ? 3000 : 10000
    if (image3dOptions.value.face_count < minFaceCount) {
      image3dOptions.value.face_count = minFaceCount
    }
    if (image3dOptions.value.model === '3.1' && (generateType === 'LowPoly' || generateType === 'Sketch')) {
      image3dOptions.value.model = '3.0'
      toastErr('当前风格与 3.1 不兼容，已自动切换到 3.0')
    }
  }
)

function buildImage3DParamsPayload() {
  const generateType = image3dDerivedGenerateType.value
  const payload: Record<string, any> = {
    model: image3dOptions.value.model,
    enable_pbr: image3dOptions.value.enable_pbr
  }

  const normalizedFaceCount = Math.round(image3dOptions.value.face_count)
  if (normalizedFaceCount !== 500000) {
    payload.face_count = normalizedFaceCount
  }

  if (generateType !== 'AUTO') {
    payload.generate_type = generateType
  }
  if (generateType === 'LowPoly') {
    payload.polygon_type = image3dOptions.value.polygon_type
  }
  payload.result_format = image3dOptions.value.result_format
  return payload
}

function openViewModel() {
  if (!viewModelUrl.value) return
  window.open(viewModelUrl.value, '_blank', 'noopener,noreferrer')
}

function getFileExtFromUrl(url?: string | null) {
  if (!url) return ''
  if (url.startsWith('/')) {
    const pathname = url.split('?')[0]
    if (!pathname.includes('.')) return ''
    return pathname.split('.').pop()?.toLowerCase() || ''
  }
  try {
    const pathname = new URL(url).pathname
    if (!pathname.includes('.')) return ''
    return pathname.split('.').pop()?.toLowerCase() || ''
  } catch {
    return ''
  }
}

function inferResultFormatFromParams(params: Record<string, unknown> | null | undefined): 'GLB' | 'STL' | null {
  if (!params || typeof params !== 'object') return null
  const generationParams = (params.generation_params && typeof params.generation_params === 'object')
    ? (params.generation_params as Record<string, unknown>)
    : params
  const fmt = typeof generationParams.ResultFormat === 'string'
    ? generationParams.ResultFormat
    : (typeof generationParams.result_format === 'string' ? generationParams.result_format : '')
  const normalized = String(fmt || '').trim().toUpperCase()
  if (normalized === 'STL' || normalized === 'GLB') return normalized
  return null
}

function getFileNameFromUrl(url?: string | null) {
  if (!url) return ''
  try {
    const u = url.startsWith('http') ? new URL(url) : null
    const path = (u ? u.pathname : url).split('?')[0]
    const seg = path.split('/').filter(Boolean)
    return seg.length ? seg[seg.length - 1].toLowerCase() : ''
  } catch {
    return ''
  }
}

async function ensureCurrentAssetId() {
  if (assetId.value) return assetId.value

  // 历史详情场景：优先锁定当前选中历史条目，避免按提示词/文件名误匹配到其他资产。
  if (selectedHistoryItemId.value) {
    await loadHistory()
    const selected = historyItems.value.find((item) => item.id === selectedHistoryItemId.value)
    if (selected?.asset_id) {
      assetId.value = selected.asset_id
      published.value = !!selected.is_published
      return assetId.value
    }
    return null
  }

  if (lastSubmittedStudioJobId.value) {
    try {
      const detail = await api.studio.queryJob(lastSubmittedStudioJobId.value)
      if (detail?.asset_id) {
        assetId.value = detail.asset_id
        return assetId.value
      }
    } catch {
      // ignore and fallback
    }
  }

  await loadHistory()
  const targetMode = mode.value
  const targetFile = getFileNameFromUrl(resultDownloadUrl.value || resultUrl.value)
  const matched = historyItems.value.find((item) => {
    if (!item.asset_id) return false
    if (targetMode === 'text23d' && item.mode !== 'text23d') return false
    if (targetMode === 'image23d' && item.mode !== 'image23d') return false
    const itemFile = getFileNameFromUrl(item.download_model_url || item.model_url || '')
    if (targetFile && itemFile && targetFile === itemFile) return true
    return false
  })
  if (matched?.asset_id) {
    assetId.value = matched.asset_id
  }
  return assetId.value
}

function isViewerRenderableFormat(modelUrl?: string | null, modelFormat?: string | null) {
  const supported = new Set(['glb', 'gltf', 'obj', 'stl', 'fbx'])
  const normalizedFormat = (modelFormat || '').toLowerCase()
  if (supported.has(normalizedFormat)) return true
  const ext = getFileExtFromUrl(modelUrl)
  return supported.has(ext)
}

function syncModeFromRoute() {
  const modeParam = route.query.mode as string
  if (
    modeParam === 'text2image' ||
    modeParam === 'text23d' ||
    modeParam === 'image23d' ||
    modeParam === 'local3dpreview'
  ) {
    mode.value = modeParam
  }
}

function hydrateT2iRemixFromSessionStorage() {
  let raw: string | null = null
  try {
    raw = sessionStorage.getItem(STUDIO_T2I_REMIX_STORAGE_KEY)
  } catch {
    return
  }
  if (!raw) return
  try {
    sessionStorage.removeItem(STUDIO_T2I_REMIX_STORAGE_KEY)
  } catch {
    // ignore
  }
  let data: StudioT2iRemixPayload
  try {
    data = JSON.parse(raw) as StudioT2iRemixPayload
  } catch {
    return
  }
  if (typeof data.prompt === 'string') {
    prompt.value = data.prompt
  } else if (data.prompt !== undefined && data.prompt !== null) {
    prompt.value = String(data.prompt)
  }

  // 清理并准备填充
  text2imageRemixModelUrl.value = null
  text2imageRemixModelFormat.value = null
  viewerLoadFailed.value = false
  const url = typeof data.modelUrl === 'string' ? data.modelUrl.trim() : ''
  const fmt = typeof data.modelFormat === 'string' ? data.modelFormat : null

  // 文生图（保留原逻辑）
  if (mode.value === 'text2image') {
    if (url && isViewerRenderableFormat(url, fmt)) {
      text2imageRemixModelUrl.value = url
      text2imageRemixModelFormat.value = fmt
      view.value = 'result'
    }
    return
  }

  // 文生3D / 图生3D：把模型/参考图信息塞入 Studio 的 3D 面板状态，触发 result + viewer
  if (mode.value === 'text23d' || mode.value === 'image23d') {
    resultUrl.value = url || null
    resultDownloadUrl.value = url || null
    resultDownloadFormat.value = fmt || (url ? getFileExtFromUrl(url) : null)
    assetId.value = null
    published.value = false
    viewerLoadFailed.value = false
    renderInitPending.value = false
    skipViewerRenderForLastResult.value = false

    if (mode.value === 'image23d') {
      const ref = typeof data.referenceImageUrl === 'string' ? data.referenceImageUrl : ''
      uploadedImage.value = ref || null
      uploadedImageDataUrl.value = isImageDataUrl(ref) ? ref : null
      uploadedFileName.value = ref && !prompt.value ? t('studio.historyItemSummary.referenceImage') : uploadedFileName.value
      resultImg.value = ref || (url || '')
    } else {
      resultImg.value = url || ''
    }

    view.value = 'result'
  }
}

function isImageDataUrl(value?: string | null) {
  return typeof value === 'string' && value.startsWith('data:image')
}

const currentResultPrintable = computed(() => {
  if (mode.value !== 'text23d' && mode.value !== 'image23d') return false
  if (currentResultFormat.value === 'STL') return true
  const ext = getFileExtFromUrl(resultDownloadUrl.value || resultUrl.value)
  return ext === 'stl'
})

type Submitted3DJob = {
  job_id: string
  status: string
  mode: 'text23d' | 'image23d'
  generation_params?: Record<string, any>
  param_notes?: string[]
  credits_used?: number
  /** 图生3D：后端下发的参数摘要文案 */
  display_prompt?: string
}

async function run3DGeneration(): Promise<Submitted3DJob | null> {
  if (mode.value === 'text23d') {
    const payload = {
      prompt: prompt.value,
      with_texture: modelRenderMode.value === 'color',
      result_format: text3dResultFormat.value
    }
    const submitRes = await api.studio.submitText3D(payload)
    creditsUsed.value = submitRes.credits_used ?? text3dEstimatedCredits.value
    return {
      job_id: submitRes.job_id,
      status: submitRes.status,
      mode: submitRes.mode,
      generation_params: submitRes.generation_params,
      param_notes: submitRes.param_notes,
      credits_used: submitRes.credits_used,
    }
  } else {
    const image3dParamPayload = buildImage3DParamsPayload()
    if (!isImageDataUrl(uploadedImageDataUrl.value)) {
      throw new Error('请重新上传图片后再提交')
    }
    const payload = {
      image_base64: uploadedImageDataUrl.value!,
      with_texture: image3dDerivedWithTexture.value,
      ...image3dParamPayload
    }
    const submitRes = await api.studio.submitImage3D(payload)
    creditsUsed.value = submitRes.credits_used ?? image3dEstimatedCredits.value
    return {
      job_id: submitRes.job_id,
      status: submitRes.status,
      mode: submitRes.mode,
      generation_params: submitRes.generation_params,
      param_notes: submitRes.param_notes,
      credits_used: submitRes.credits_used,
      display_prompt: submitRes.display_prompt,
    }
  }
}

async function generate() {
  stopProgressTimer()
  resolveRenderReady(false)

  if (mode.value === 'local3dpreview') {
    if (localModelFiles.value.length === 0) {
      return toastErr('请先选择本地3D文件')
    }
    loading.value = true
    view.value = 'loading'
    creditsUsed.value = null
    resultUrl.value = null
    resultDownloadUrl.value = null
    resultDownloadFormat.value = null
    resultImg.value = ''
    assetId.value = null
    currentResultFormat.value = null
    lastSubmittedStudioJobId.value = null
    published.value = false
    viewerLoadFailed.value = false
    generationProgress.value = 0
    generationTargetProgress.value = 0
    generationStatusMessage.value = ''
    renderInitPending.value = false
    skipViewerRenderForLastResult.value = false
    finalOutputSpec.value = null
    try {
      await new Promise((resolve) => setTimeout(resolve, 200))
      view.value = 'result'
      renderIcons()
      await mountLocalEmbeddedViewer(localModelFiles.value)
      toastOk(`本地模型加载成功（${localModelFiles.value.length} 个文件）`)
      try {
        const uploadRes = await api.studio.uploadLocalPreview(localModelFiles.value, localModelPrimaryFileName.value || undefined)
        resultUrl.value = uploadRes.model_url
        resultDownloadUrl.value = uploadRes.model_url
        resultDownloadFormat.value = getFileExtFromUrl(uploadRes.model_url)
        if (uploadRes.preview_url) {
          resultImg.value = uploadRes.preview_url
        }
        await loadHistory()
      } catch (saveErr: any) {
        console.warn('本地预览历史保存失败:', saveErr)
        toastErr(saveErr?.message || '本地模型已加载，但历史保存失败')
      }
    } catch (e: any) {
      console.error(e)
      view.value = 'empty'
      toastErr(e?.message || '本地模型加载失败')
    } finally {
      loading.value = false
    }
    return
  }

  // 检查登录状态
  auth.hydrate()
  if (!auth.isAuthed) {
    return toastErr('请先登录后再生成')
  }

  // 图转3D需要先上传图片
  if (mode.value === 'image23d' && !uploadedImage.value) {
    return toastErr('请先上传图片')
  }

  // 文生图/文生3D需要提示词
  if ((mode.value === 'text2image' || mode.value === 'text23d') && !prompt.value.trim()) {
    return toastErr('请输入提示词')
  }

  loading.value = true
  creditsUsed.value = null
  generationStatusMessage.value = ''
  selectedTransientJobId.value = null
  selectedHistoryItemId.value = null

  if (mode.value === 'text2image') {
    view.value = 'loading'
    resultUrl.value = null
    resultDownloadUrl.value = null
    resultDownloadFormat.value = null
    resultImg.value = ''
    assetId.value = null
    published.value = false
    viewerLoadFailed.value = false
    generationProgress.value = 0
    generationTargetProgress.value = 0
    renderInitPending.value = false
    skipViewerRenderForLastResult.value = false
    finalOutputSpec.value = null
  } else {
    view.value = 'loading'
    resultUrl.value = null
    resultDownloadUrl.value = null
    resultDownloadFormat.value = null
    resultImg.value = mode.value === 'image23d' ? (uploadedImage.value || '') : ''
    assetId.value = null
    currentResultFormat.value = null
    published.value = false
    viewerLoadFailed.value = false
    generationProgress.value = 6
    generationTargetProgress.value = 14
    generationStatusMessage.value = 'studio.messages.taskSubmittedWaiting'
    renderInitPending.value = false
    skipViewerRenderForLastResult.value = false
    finalOutputSpec.value = null
    startProgressTimer()
  }

  try {
    if (mode.value === 'text2image') {
      // 文生图：调用阿里云百炼 wan2.6-t2i API
      const res = await api.studio.generate({
        prompt: prompt.value,
        model_config_id: 'wan2.6-t2i', // 指定使用阿里云百炼文生图模型
        aspect_ratio: t2iAspectRatio.value,
        resolution_level: t2iResolutionLevel.value,
        image_size: t2iOutputSize.value,
        style: t2iStyle.value,
      })
      
      console.log('✅ 文生图响应:', res)
      resultImg.value = res.preview_url || res.image_url || ''
      resultUrl.value = res.image_url || null
      resultDownloadUrl.value = res.image_url || null
      resultDownloadFormat.value = getFileExtFromUrl(res.image_url || null)
      assetId.value = res.asset_id || null
      currentResultFormat.value = null
      lastSubmittedStudioJobId.value = null
      creditsUsed.value = res.credits_used || 10
      const outputSize = res.output_size || t2iOutputSize.value
      const responseRatio = typeof res.aspect_ratio === 'string' ? res.aspect_ratio : ''
      const responseLevel = typeof res.resolution_level === 'string' ? res.resolution_level.toLowerCase() : ''
      if (isT2IRatio(responseRatio)) {
        t2iAspectRatio.value = responseRatio
      } else {
        t2iAspectRatio.value = inferT2IRatioFromSize(outputSize)
      }
      if (isT2IResolutionLevel(responseLevel)) {
        t2iResolutionLevel.value = responseLevel
      } else {
        t2iResolutionLevel.value = inferT2IResolutionLevelFromSize(outputSize, t2iAspectRatio.value)
      }
      finalOutputSpec.value = {
        size: outputSize,
        ratio: t2iAspectRatio.value
      }
      if (res.style && isT2IStyle(res.style)) {
        t2iStyle.value = res.style
      }
      if (res.spec_note) {
        toastOk(res.spec_note)
      }
      
      console.log('📊 设置显示数据:', { resultImg: resultImg.value, resultUrl: resultUrl.value })
      
      if (!resultImg.value) {
        toastErr('生成成功但未返回图片URL')
      } else {
        toastOk(`图片生成成功（-${creditsUsed.value} 积分）`)
        loadHistory()
        text2imageRemixModelUrl.value = null
        text2imageRemixModelFormat.value = null
      }
      view.value = 'result'
    } else {
      const submitRes = await run3DGeneration()
      const credits = submitRes?.credits_used ?? estimatedGenerateCredits.value
      const jobId = submitRes?.job_id
      lastSubmittedStudioJobId.value = jobId || null
      const modeLabel = mode.value === 'image23d' ? '图转3D' : '文生3D'
      if (submitRes && jobId) {
        const sidebarPrompt =
          mode.value === 'image23d'
            ? String(submitRes.display_prompt || '').trim()
            : prompt.value.trim()
        const sidebarItem: SidebarJobItem = {
          id: `job:${jobId}`,
          job_id: jobId,
          mode: submitRes.mode,
          prompt: sidebarPrompt,
          params: normalizeHistoryParams({
            with_texture: submitRes.texture_mode !== 'white',
            generation_params: submitRes.generation_params || {},
            param_notes: submitRes.param_notes || [],
            credits_used: credits,
          }),
          preview_url: mode.value === 'image23d' ? uploadedImage.value : null,
          model_url: null,
          asset_id: null,
          created_at: new Date().toISOString(),
          finished_at: null,
          expires_at: null,
          is_transient: true,
          transient_status: 'SUBMITTED',
          transient_progress: 10,
          transient_message: '任务已提交，等待排队...'
        }
        upsertSidebarJobItem(sidebarItem)
        await setLoadingPreviewForSidebarJob(sidebarItem)
        scheduleTrackStudioJob(jobId)
        void syncSidebarJobs()
      }
      toastOk(`${modeLabel}任务已提交（预计 ${credits} 积分）${jobId ? `，任务ID：${jobId}` : ''}`)
    }
  } catch (e: any) {
    console.error(e)
    stopProgressTimer()
    resolveRenderReady(false)
    renderInitPending.value = false
    if (mode.value === 'text2image' || mode.value === 'text23d' || mode.value === 'image23d') {
      if (mode.value === 'text2image' && text2imageRemixModelUrl.value) {
        view.value = 'result'
      } else {
        view.value = 'empty'
      }
    }
    toastErr(e?.message || '生成失败')
  } finally {
    loading.value = false
  }
}

async function confirmPrintOrder() {
  const currentAssetId = await ensureCurrentAssetId()
  if (!currentAssetId) {
    toastErr('请先生成3D模型')
    return
  }

  // 检查登录状态
  auth.hydrate()
  if (!auth.isAuthed) {
    toastErr('请先登录')
    return
  }

  printBusy.value = true
  try {
    const res = await api.printOrders.create({
      asset_id: currentAssetId,
      height: printHeight.value,
      material: printMaterial.value,
      estimated_weight: estimatedWeight.value ?? undefined
    })

    toastOk(res.message || '打印订单创建成功！')
    showPrintDialog.value = false

    // 跳转到订单详情页
    setTimeout(() => {
      router.push(`/orders/${res.order_id}`)
    }, 1500)
  } catch (e: any) {
    toastErr(e?.message || '创建打印订单失败')
  } finally {
    printBusy.value = false
  }
}

function addToCart() {
  // 检查是否有asset_id
  if (!assetId.value) {
    toastErr('请先生成3D模型')
    return
  }

  try {
    toastErr('打印定制将按真实切片克重计价，暂不支持加入购物车，请直接下单')
  } catch (e: any) {
    toastErr(e?.message || '加入购物车失败')
  }
}

async function publishToCommunity() {
  publishingAssetResolve.value = true
  try {
    const currentAssetId = await ensureCurrentAssetId()
    if (!currentAssetId) {
      toastErr('当前结果尚未生成可发布资产，请等待几秒后重试')
      return
    }
    const res = await api.assets.publish(currentAssetId)
    published.value = !!res.is_published
    toastOk(res.message || '发布成功')
    renderIcons()
    setTimeout(() => {
      router.push('/community')
    }, 600)
  } catch (e: any) {
    toastErr(e?.message || '发布失败')
  } finally {
    publishingAssetResolve.value = false
  }
}

function downloadImage() {
  if (!resultImg.value) return
  const link = document.createElement('a')
  link.href = resultImg.value
  const ext = getFileExtFromUrl(resultImg.value) || 'jpg'
  link.download = `generated-image-${Date.now()}.${ext}`
  link.click()
  toastOk(t('studio.messages.imageDownloading'))
}

</script>

<style scoped>
.page-transition {
  @apply animate-[slideUp_0.3s_cubic-bezier(0.16,1,0.3,1)];
}

/* 左侧参数面板：轨道透明、滑块低对比，避免系统默认白底滚动条 */
.studio-left-panel-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgb(71 85 105 / 0.45) transparent;
}
.studio-left-panel-scroll::-webkit-scrollbar {
  width: 6px;
}
.studio-left-panel-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.studio-left-panel-scroll::-webkit-scrollbar-thumb {
  background-color: rgb(51 65 85 / 0.5);
  border-radius: 9999px;
  border: 2px solid transparent;
  background-clip: padding-box;
}
.studio-left-panel-scroll::-webkit-scrollbar-thumb:hover {
  background-color: rgb(71 85 105 / 0.65);
}
</style>
