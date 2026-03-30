interface AIAnalysisProps {
  text: string;
  streaming: boolean;
  error: string | null;
}

export default function AIAnalysis({ text, streaming, error }: AIAnalysisProps) {
  if (error) {
    return (
      <div className="bg-white rounded-lg border border-red-200 p-4 sm:p-6">
        <p className="text-sm text-red-500">{error}</p>
      </div>
    );
  }

  if (!text && !streaming) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-3">
        <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <h3 className="font-bold text-base sm:text-lg text-gray-900">AI 趨勢分析</h3>
        {streaming && (
          <span className="inline-block h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
        )}
      </div>
      <p className="text-sm sm:text-base text-gray-700 leading-relaxed whitespace-pre-wrap">
        {text || (streaming ? "" : "")}
        {streaming && <span className="inline-block w-1 h-4 bg-blue-500 animate-pulse ml-0.5 align-text-bottom" />}
      </p>
      {!streaming && text && (
        <p className="text-xs text-gray-400 mt-3 border-t border-gray-100 pt-2">
          * 此分析僅描述趨勢，不構成投資建議
        </p>
      )}
    </div>
  );
}
