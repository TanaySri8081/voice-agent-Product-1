export default function ChartCard({ title, description, children, action }) {
  return (
    <section className="panel rounded-3xl p-5">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-gray-950">{title}</h2>
          {description ? <p className="mt-1 text-sm text-gray-500">{description}</p> : null}
        </div>
        {action}
      </div>
      <div className="h-72">{children}</div>
    </section>
  );
}
