import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HomeView from '../../views/HomeView.vue'
import { createRouter, createWebHistory } from 'vue-router'

vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({
      data: [
        { id: 1, name: 'Google', url: 'https://google.com', keywords_count: 50, clusters_count: 5 },
        { id: 2, name: 'Yandex', url: 'https://yandex.ru', keywords_count: 200, clusters_count: 20 }
      ]
    })),
    post: vi.fn(() => Promise.resolve({ data: { id: 3, name: 'New' } }))
  }
}))

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: HomeView }, { path: '/project/:id', component: { template: '<div>Project</div>' } }]
})

describe('HomeView', () => {
  it('loads and lists projects on mount', async () => {
    router.push('/')
    await router.isReady()
    
    const wrapper = mount(HomeView, {
      global: {
        plugins: [router]
      }
    })

    expect(wrapper.text()).toContain('Список проектов')
    
    // waiting for axios
    await flushPromises()
    
    expect(wrapper.text()).toContain('Google')
    expect(wrapper.text()).toContain('Yandex')
    // the project urls
    expect(wrapper.text()).toContain('https://google.com')
  })
})
