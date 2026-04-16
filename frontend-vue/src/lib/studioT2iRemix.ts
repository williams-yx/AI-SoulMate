/** 作品详情「二次创作」→ 造梦文生图 的一次性 sessionStorage 键 */
export const STUDIO_T2I_REMIX_STORAGE_KEY = 'studio_t2i_remix'

export type StudioT2iRemixPayload = {
  prompt: string
  /** 目标模式：文生图 / 文生3D / 图生3D */
  mode?: 'text2image' | 'text23d' | 'image23d'
  modelUrl?: string | null
  modelFormat?: string | null
  /** 图生3D 的参考图 URL（可选） */
  referenceImageUrl?: string | null
}
