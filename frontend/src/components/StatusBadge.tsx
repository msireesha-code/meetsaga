export default function StatusBadge({ status }: { status: string }) {
  let cls = "badge-queued";
  if (status === "COMPLETED") cls = "badge-completed";
  else if (status === "FAILED" || status === "CANCELLED") cls = "badge-failed";
  else if (status !== "QUEUED") cls = "badge-processing";
  return <span className={`badge ${cls}`}>{status}</span>;
}
