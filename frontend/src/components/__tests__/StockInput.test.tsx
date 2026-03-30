import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import StockInput from '../StockInput'

describe('StockInput', () => {
  const defaultProps = {
    onSearch: vi.fn(),
    loading: false,
    error: null,
  }

  it('空白輸入按搜尋不呼叫 onSearch', () => {
    const onSearch = vi.fn()
    render(<StockInput {...defaultProps} onSearch={onSearch} />)
    fireEvent.submit(screen.getByRole('button', { name: '查詢' }))
    expect(onSearch).not.toHaveBeenCalled()
  })

  it('輸入有效代號按搜尋呼叫 onSearch("2330")', () => {
    const onSearch = vi.fn()
    render(<StockInput {...defaultProps} onSearch={onSearch} />)
    fireEvent.change(screen.getByPlaceholderText('輸入台股代號 (例: 2330)'), {
      target: { value: '2330' },
    })
    fireEvent.submit(screen.getByRole('button', { name: '查詢' }))
    expect(onSearch).toHaveBeenCalledWith('2330')
  })

  it('前後空白自動 trim', () => {
    const onSearch = vi.fn()
    render(<StockInput {...defaultProps} onSearch={onSearch} />)
    fireEvent.change(screen.getByPlaceholderText('輸入台股代號 (例: 2330)'), {
      target: { value: ' 2330 ' },
    })
    fireEvent.submit(screen.getByRole('button', { name: '查詢' }))
    expect(onSearch).toHaveBeenCalledWith('2330')
  })

  it('Enter 鍵觸發搜尋', () => {
    const onSearch = vi.fn()
    render(<StockInput {...defaultProps} onSearch={onSearch} />)
    const input = screen.getByPlaceholderText('輸入台股代號 (例: 2330)')
    fireEvent.change(input, { target: { value: '2330' } })
    fireEvent.submit(input.closest('form')!)
    expect(onSearch).toHaveBeenCalledWith('2330')
  })

  it('Loading 狀態按鈕 disabled 且顯示「查詢中...」', () => {
    render(<StockInput {...defaultProps} loading={true} />)
    const button = screen.getByRole('button', { name: '查詢中...' })
    expect(button).toBeDisabled()
  })

  it('錯誤訊息顯示', () => {
    render(<StockInput {...defaultProps} error="查無此代號" />)
    expect(screen.getByText('查無此代號')).toBeInTheDocument()
  })

  it('輸入為空時按鈕 disabled', () => {
    render(<StockInput {...defaultProps} />)
    expect(screen.getByRole('button', { name: '查詢' })).toBeDisabled()
  })
})
