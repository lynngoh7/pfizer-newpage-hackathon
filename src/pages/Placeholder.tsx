/**
 * Stub view for screens not built yet. Shows the title and which build step
 * delivers it. Delete this file once every view has a real page.
 */
interface Props {
  title: string;
  note: string;
}

export default function Placeholder({ title, note }: Props) {
  return (
    <div className="page">
      <h2>{title}</h2>
      <p className="muted">{note}</p>
    </div>
  );
}
