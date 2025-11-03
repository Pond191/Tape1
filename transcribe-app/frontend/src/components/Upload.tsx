import { useRef, useState } from "react";
import { JobSummary, TranscribeOptions, uploadAudio } from "../api/client";

interface Props {
  onJobCreated: (job: JobSummary) => void;
}

const defaultOptions: TranscribeOptions = {
  model_size: "small",
  enable_dialect_map: false
};

export default function Upload({ onJobCreated }: Props) {
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [options, setOptions] = useState<TranscribeOptions>(defaultOptions);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!fileInput.current?.files?.length) {
      setError("กรุณาเลือกไฟล์เสียงก่อนเริ่มถอดเทป");
      return;
    }

    const file = fileInput.current.files[0];
    setLoading(true);
    try {
      const job = await uploadAudio(file, options);
      onJobCreated(job);
      if (fileInput.current) {
        fileInput.current.value = "";
      }
      setError(null);
    } catch (err) {
      console.error(err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("อัปโหลดไม่สำเร็จ กรุณาลองใหม่อีกครั้ง");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <h2>อัปโหลดไฟล์เสียง</h2>
      <input ref={fileInput} type="file" accept="audio/*" required disabled={loading} />
      <label>
        เลือกโมเดล
        <select
          value={options.model_size}
          onChange={(event) => setOptions({ ...options, model_size: event.target.value })}
          disabled={loading}
        >
          <option value="small">small</option>
          <option value="medium">medium</option>
          <option value="large-v3">large-v3</option>
        </select>
      </label>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={Boolean(options.enable_dialect_map)}
          onChange={(event) => setOptions({ ...options, enable_dialect_map: event.target.checked })}
          disabled={loading}
        />
        เปิด Dialect mapping
      </label>
      <button type="submit" disabled={loading}>
        {loading ? "กำลังอัปโหลด..." : "ถอดเทป"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
