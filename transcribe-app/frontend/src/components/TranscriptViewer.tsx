import { useMemo, useState } from "react";
import { JobResult } from "../api/client";

interface Props {
  result?: JobResult;
}

export default function TranscriptViewer({ result }: Props) {
  const [query, setQuery] = useState("");

  const filteredSegments = useMemo(() => {
    if (!result) {
      return [];
    }
    if (!query) {
      return result.segments;
    }
    return result.segments.filter((segment) => segment.text.toLowerCase().includes(query.toLowerCase()));
  }, [result, query]);

  if (!result) {
    return <p>เลือกงานที่เสร็จแล้วเพื่อดูผลลัพธ์</p>;
  }

  return (
    <div className="transcript-viewer">
      <h2>ถอดเทป</h2>
      <input
        placeholder="ค้นหา..."
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="segments">
        {filteredSegments.map((segment) => (
          <div key={`${segment.start}-${segment.end}`} className="segment">
            <div className="meta">
              <span>{segment.speaker ?? "ผู้พูด"}</span>
              <span>
                {segment.start.toFixed(1)}s - {segment.end.toFixed(1)}s
              </span>
            </div>
            <p>{segment.text}</p>
          </div>
        ))}
      </div>
      {result.dialect_mapped_text && (
        <div className="dialect-mapping">
          <h3>เวอร์ชันไทยกลาง</h3>
          <p>{result.dialect_mapped_text}</p>
        </div>
      )}
    </div>
  );
}
