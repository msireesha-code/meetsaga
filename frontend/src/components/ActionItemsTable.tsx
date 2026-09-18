import type { ActionItem, TranscriptSegment } from "../types";

function priorityClass(priority: string): string {
  const p = priority.toLowerCase();
  if (p === "high") return "priority-high";
  if (p === "medium") return "priority-medium";
  if (p === "low") return "priority-low";
  return "";
}

function Value({ value }: { value: string }) {
  if (!value || value === "Not specified") return <span className="not-specified">Not specified</span>;
  return <>{value}</>;
}

export default function ActionItemsTable({
  items,
  onNavigate,
  segments,
}: {
  items: ActionItem[];
  onNavigate: (seconds: number) => void;
  segments?: TranscriptSegment[];
}) {
  if (items.length === 0) return <p className="empty-state">No action items identified.</p>;

  const jumpTo = (item: ActionItem) => {
    if (segments && item.source_segment_ids.length > 0) {
      const idx = item.source_segment_ids[0];
      const seg = segments[idx];
      if (seg) {
        onNavigate(seg.start);
        return;
      }
    }
    if (item.timestamp) {
      const parts = item.timestamp.split(":").map(Number);
      const seconds = parts.length === 3 ? parts[0] * 3600 + parts[1] * 60 + parts[2] : 0;
      onNavigate(seconds);
    }
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Action</th>
          <th>Owner</th>
          <th>Due Date</th>
          <th>Priority</th>
          <th>Timestamp</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} title={item.context || undefined}>
            <td>{item.action}</td>
            <td>
              <Value value={item.owner} />
            </td>
            <td>
              <Value value={item.due_date} />
            </td>
            <td className={priorityClass(item.priority)}>
              <Value value={item.priority} />
            </td>
            <td>
              {item.timestamp ? (
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    jumpTo(item);
                  }}
                >
                  {item.timestamp}
                </a>
              ) : (
                "-"
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
