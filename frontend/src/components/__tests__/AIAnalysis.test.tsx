import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import AIAnalysis from '../AIAnalysis'

describe('AIAnalysis', () => {
  it('analysis 為 null 不渲染任何內容', () => {
    const { container } = render(<AIAnalysis analysis={null} loading={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('analysis 為有效文字時顯示分析內容', () => {
    render(<AIAnalysis analysis="趨勢向上" loading={false} />)
    expect(screen.getByText('趨勢向上')).toBeInTheDocument()
    expect(screen.getByText('AI 趨勢分析')).toBeInTheDocument()
  })

  it('loading 為 true 時顯示 skeleton', () => {
    const { container } = render(<AIAnalysis analysis={null} loading={true} />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('analysis 含 HTML 標籤以純文字渲染', () => {
    render(<AIAnalysis analysis="<script>alert(1)</script>" loading={false} />)
    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
  })

  it('超長文字正常渲染不 crash', () => {
    const longText = 'A'.repeat(10000)
    render(<AIAnalysis analysis={longText} loading={false} />)
    expect(screen.getByText(longText)).toBeInTheDocument()
  })
})
