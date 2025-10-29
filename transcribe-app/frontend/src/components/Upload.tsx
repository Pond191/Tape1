import { useRef, useState } from "react";
import { TranscribeOptions, uploadAudio } from "../api/client";

interface Props {
  onJobCreated: (jobId: string) => void;
}

const defaultOptions: TranscribeOptions = {
  model_size: "small",
  enable_diarization: true,
  enable_punct: true,
  enable_itn: true,
  enable_dialect_map: true
};

export default function Upload({ onJobCreated }: Props) {
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [options, setOptions] = useState<TranscribeOptions>(defaultOptions);
  const [lexicon, setLexicon] = useState<string>("Node-RED, MQTT, VLAN");
  const [contextPrompt, setContextPrompt] = useState<string>("สงขลานครินทร์ หาดใหญ่ ศรีตรัง");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!fileInput.current?.files?.length) {
      return;
    }
    const file = fileInput.current.files[0];
    setLoading(true);
    try {
      const payload: TranscribeOptions = {
        ...options,
        custom_lexicon: lexicon
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        context_prompt: contextPrompt
      };
      const jobId = await uploadAudio(file, payload);
      onJobCreated(jobId);
      if (fileInput.current) {
        fileInput.current.value = "";
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <h2>อัปโหลดไฟล์เสียง</h2>
      <input ref={fileInput} type="file" accept="audio/*" required />
      <label>
        เลือกโมเดล
        <select
          value={options.model_size}
          onChange={(event) => setOptions({ ...options, model_size: event.target.value })}
        >
          <option value="tiny">tiny</option>
          <option value="base">base</option>
          <option value="small">small</option>
          <option value="medium">medium</option>
          <option value="large-v3">large-v3</option>
        </select>
      </label>
      <label>
        Context prompt
        <textarea value={contextPrompt} onChange={(event) => setContextPrompt(event.target.value)} />
      </label>
      <label>
        Custom lexicon (comma separated)
        <input value={lexicon} onChange={(event) => setLexicon(event.target.value)} />
      </label>
      <label>
        เปิด Dialect mapping
        <input
          type="checkbox"
          checked={options.enable_dialect_map}
          onChange={(event) => setOptions({ ...options, enable_dialect_map: event.target.checked })}
        />
      </label>
      <button type="submit" disabled={loading}>
        {loading ? "กำลังอัปโหลด..." : "ถอดเทป"}
      </button>
    </form>
  );
}
