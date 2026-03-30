import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchStock } from '../stockApi'

describe('fetchStock', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('成功回應正確解析 JSON', async () => {
    const mockData = {
      symbol: '2330',
      name: '台積電',
      data: [],
      ma5: [],
      ma20: [],
      ai_analysis: null,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })
    )

    const result = await fetchStock('2330')
    expect(result).toEqual(mockData)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/stock/2330')
  })

  it('非 200 回應拋出 Error 含 detail 訊息', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: '查無此股票代號' }),
      })
    )

    await expect(fetchStock('9999')).rejects.toThrow('查無此股票代號')
  })

  it('非 JSON 回應拋出 Error 含 fallback 訊息', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('not json')),
      })
    )

    await expect(fetchStock('2330')).rejects.toThrow('Unknown error')
  })
})
