import React from 'react';

interface QueryResultProps {
  columns: string[];
  rows: (string | number | null)[][];
}

export default function QueryResult({ columns, rows }: QueryResultProps) {
  if (!columns.length || !rows.length) {
    return (
      <div className="text-gray-500 text-sm italic">
        Sonuc bulunamadi.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border rounded-lg">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rows.slice(0, 100).map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-gray-50">
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap"
                >
                  {cell === null ? (
                    <span className="text-gray-400 italic">null</span>
                  ) : (
                    String(cell)
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 100 && (
        <div className="px-4 py-2 bg-gray-50 text-sm text-gray-500 border-t">
          Ilk 100 sonuc gosteriliyor ({rows.length} toplam)
        </div>
      )}
    </div>
  );
}
