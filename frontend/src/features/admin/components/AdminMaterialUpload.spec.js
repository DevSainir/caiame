// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminMaterialUpload from '@/features/admin/components/AdminMaterialUpload.vue'

const MATERIAL = {
  id: 'a1',
  original_name: 'priem-terapevta.mp4',
  size_bytes: 248 * 1024 * 1024,
  duration_seconds: 1380,
  content_type: 'video/mp4',
  uploaded_at: '2026-08-30T10:00:00Z',
}

describe('загрузка материала', () => {
  it('честно говорит, что файла нет', () => {
    const block = mount(AdminMaterialUpload, { props: { kind: 'video' } })

    expect(block.text()).toContain('Файл пока не загружен')
  })

  it('показывает имя файла и его размер', () => {
    // Размер здесь — не украшение: по нему видно, что загрузился тот файл, а не пустышка.
    const block = mount(AdminMaterialUpload, { props: { kind: 'video', material: MATERIAL } })

    expect(block.text()).toContain('priem-terapevta.mp4')
    expect(block.text()).toContain('248.0 МБ')
  })

  it('называет ограничение того вида, который выбран', () => {
    const video = mount(AdminMaterialUpload, { props: { kind: 'video' } })
    const pdf = mount(AdminMaterialUpload, { props: { kind: 'pdf' } })

    expect(video.text()).toContain('MP4')
    expect(pdf.text()).toContain('PDF')
  })

  it('во время загрузки показывает ход, а не старый файл', () => {
    const block = mount(AdminMaterialUpload, {
      props: { kind: 'video', material: MATERIAL, isBusy: true, progress: 40 },
    })

    expect(block.text()).toContain('Загружаем файл…')
    expect(block.html()).toContain('width: 40%')
  })
})
