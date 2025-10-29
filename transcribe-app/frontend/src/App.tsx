import { useCallback, useState } from "react";
import Upload from "./components/Upload";
import JobList from "./components/JobList";
import TranscriptViewer from "./components/TranscriptViewer";
import { JobResult, JobStatus } from "./api/client";

export default function App() {
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [selectedResult, setSelectedResult] = useState<JobResult | undefined>();

  const handleJobCreated = (jobId: string) => {
    setJobs((current) => [...current, { job_id: jobId, status: "pending", progress: 0 } as JobStatus]);
  };

  const handleResult = useCallback((result: JobResult) => {
    setSelectedResult(result);
  }, []);

  return (
    <div className="app">
      <header>
        <h1>Dialect Transcribe</h1>
        <p>ถอดเทปไทย/อีสาน/เหนือ/ใต้ พร้อมโค้ดสวิตช์</p>
      </header>
      <main>
        <Upload onJobCreated={handleJobCreated} />
        <JobList jobs={jobs} setJobs={setJobs} onResult={handleResult} />
        <TranscriptViewer result={selectedResult} />
      </main>
    </div>
  );
}
