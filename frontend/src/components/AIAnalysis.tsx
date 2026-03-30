interface AIAnalysisProps {
  analysis: string | null;
  loading: boolean;
}

export default function AIAnalysis({ analysis, loading }: AIAnalysisProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-32 mb-3" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-100 rounded w-full" />
          <div className="h-4 bg-gray-100 rounded w-5/6" />
          <div className="h-4 bg-gray-100 rounded w-4/6" />
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-3">
        <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <h3 className="font-bold text-base sm:text-lg text-gray-900">AI 趨勢分析</h3>
      </div>
      <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{analysis}</p>
      <p className="text-xs text-gray-400 mt-3 border-t border-gray-100 pt-2">
        * 此分析僅描述趨勢，不構成投資建議
      </p>
    </div>
  );
}
