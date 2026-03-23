import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SiteAudit from '../SiteAudit.vue'

describe('SiteAudit', () => {
  it('renders correctly with 100 score', () => {
    const auditData = {
      score: 100,
      checks: [
        { status: true, msg: '200 OK', name: 'Availability' }
      ]
    }
    const wrapper = mount(SiteAudit, { props: { auditData } })
    
    expect(wrapper.text()).toContain('Health Score')
    expect(wrapper.text()).toContain('100Health Score')
    expect(wrapper.text()).toContain('200 OK')
  })

  it('renders correctly with low score', () => {
    const auditData = {
      score: 45,
      checks: [
        { status: false, msg: 'Error 500', name: 'Availability' }
      ]
    }
    const wrapper = mount(SiteAudit, { props: { auditData } })
    
    expect(wrapper.text()).toContain('45Health Score')
    expect(wrapper.text()).toContain('Error 500')
  })
})
