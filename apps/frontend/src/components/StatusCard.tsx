type StatusCardProps = {
  title: string;
  value: string;
  description: string;
};

export function StatusCard({ title, value, description }: StatusCardProps) {
  return (
    <article className="card status-card">
      <div className="card-header">
        <h2>{title}</h2>
        <span className="badge">{value}</span>
      </div>
      <p>{description}</p>
    </article>
  );
}
