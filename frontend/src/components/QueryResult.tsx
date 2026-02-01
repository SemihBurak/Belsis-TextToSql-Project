interface QueryResultProps {
  columns: string[];
  rows: (string | number | null)[][];
}

export default function QueryResult({ columns, rows }: QueryResultProps) {
  if (!columns.length || !rows.length) {
    return (
      <div className="text-center py-8 bg-gradient-to-br from-gray-50 to-slate-100 rounded-xl border-2 border-gray-200">
        <div className="text-5xl mb-2">📭</div>
        <p className="text-gray-500 font-medium">Sonuç bulunamadı</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden border-2 border-gray-200 rounded-xl shadow-lg">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gradient-to-r from-indigo-500 to-purple-500">
            <tr>
              {columns.map((column, index) => (
                <th
                  key={index}
                  className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {rows.slice(0, 100).map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 transition-colors duration-150"
              >
                {row.map((cell, cellIndex) => (
                  <td
                    key={cellIndex}
                    className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap"
                  >
                    {cell === null ? (
                      <span className="text-gray-400 italic font-mono bg-gray-100 px-2 py-1 rounded">null</span>
                    ) : (
                      <span className="font-medium">{String(cell)}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 100 && (
        <div className="px-6 py-3 bg-gradient-to-r from-yellow-50 to-amber-50 text-sm font-medium border-t-2 border-yellow-200 flex items-center space-x-2">
          <span className="text-xl">⚠️</span>
          <span className="text-yellow-800">
            İlk 100 sonuç gösteriliyor ({rows.length} toplam kayıt)
          </span>
        </div>
      )}
    </div>
  );
}
