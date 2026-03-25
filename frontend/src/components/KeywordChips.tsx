export interface KeywordChipProps {
  keyword: string;
  matched: boolean;
  onClick?: () => void;
}

export function KeywordChip({ keyword, matched, onClick }: KeywordChipProps) {
  return (
    <span
      onClick={onClick}
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors ${
        matched 
          ? 'bg-green-50 text-green-700 border-green-200' 
          : 'bg-gray-100 text-gray-700 border-gray-200'
      } ${onClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
    >
      {keyword}
    </span>
  );
}

export function KeywordChips({ keywords }: { keywords: KeywordChipProps[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {keywords.map((k, i) => (
        <KeywordChip key={i} {...k} />
      ))}
    </div>
  );
}
