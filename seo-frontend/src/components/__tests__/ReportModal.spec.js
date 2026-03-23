import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ReportModal from '../ReportModal.vue'

// Mock axios and marked
vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: { content: 'Mocked Content' } }))
  }
}))
vi.mock('marked', () => ({
  marked: vi.fn((text) => `<p>${text}</p>`)
}))

describe('ReportModal', () => {
  const cluster = {
    id: 1,
    name: 'Test Cluster',
    keywords: [{ query: 'test kw', volume: 100 }]
  }

  it('renders Correctly and defaults to TZ tab', async () => {
    const wrapper = mount(ReportModal, {
      props: {
        cluster: cluster,
        modelValue: true
      },
      global: {
        stubs: {
          VueFinalModal: { template: '<div><slot /></div>' }
        }
      }
    })

    expect(wrapper.text()).toContain('Test Cluster')
    // Tabs
    const buttons = wrapper.findAll('.main-tabs button')
    expect(buttons[0].text()).toBe('ТЗ для копирайтера')
    expect(buttons[1].text()).toBe('Готовая статья')
    
    // Initial active tab should show default TZ text
    expect(wrapper.text()).toContain('ТЗ ДЛЯ КОПИРАЙТЕРА НА SEO-ТЕКСТ')
  })

  it('switches to Article tab correctly', async () => {
    const wrapper = mount(ReportModal, {
      props: {
        cluster: cluster,
        modelValue: true
      },
      global: {
        stubs: {
          VueFinalModal: { template: '<div><slot /></div>' }
        }
      }
    })

    // Click on the second tab
    const articleTabBtn = wrapper.findAll('.main-tabs button')[1]
    await articleTabBtn.trigger('click')

    // It should state that article is not generated
    expect(wrapper.text()).toContain('Статья еще не сгенерирована.')
  })
})
