interface AIAnalysisProps {
  analysis: string | null;
  loading: boolean;
}

export default function AIAnalysis({ analysis, loading }: AIAnalysisProps) {
  if (loading) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded border animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded border">
      <h3 className="font-bold text-lg mb-2">AI 趨勢分析</h3>
      <p className="text-gray-700 leading-relaxed">{analysis}</p>
      <p className="text-xs text-gray-400 mt-2">* 此分析僅描述趨勢，不構成投資建議</p>
    </div>
  );
}
